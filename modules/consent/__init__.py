"""
Consent Management System for Healthcare Data Sharing

Features:
- Organization management (hospitals, clinics, labs)
- Access request workflow
- Patient consent with time limits
- Audit trail for all access
- Emergency access override
"""

import sqlite3
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class OrganizationType(Enum):
    """Types of healthcare organizations."""
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    LAB = "laboratory"
    PHARMACY = "pharmacy"
    INSURANCE = "insurance"
    RESEARCH = "research"


class AccessStatus(Enum):
    """Status of access requests."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AccessType(Enum):
    """Types of access."""
    VIEW = "view"
    DOWNLOAD = "download"
    DIAGNOSE = "diagnose"
    FULL = "full"


@dataclass
class Organization:
    """Healthcare organization."""
    id: str
    name: str
    org_type: OrganizationType
    address: str
    license_number: str
    verified: bool = False
    created_at: str = ""

    def to_dict(self):
        return {
            **asdict(self),
            'org_type': self.org_type.value
        }


@dataclass
class AccessRequest:
    """Request from doctor to access patient data."""
    id: str
    doctor_id: str
    doctor_name: str
    patient_id: str
    patient_name: str
    record_hash: str  # Specific record or "all" for all records
    organization_id: str
    organization_name: str
    access_type: AccessType
    reason: str
    status: AccessStatus
    requested_at: str
    responded_at: str = ""
    expires_at: str = ""
    notes: str = ""

    def to_dict(self):
        return {
            **asdict(self),
            'access_type': self.access_type.value,
            'status': self.status.value
        }


@dataclass
class AuditLog:
    """Audit log entry for data access."""
    id: str
    user_id: str
    user_name: str
    user_role: str
    action: str  # view, download, diagnose, share, revoke
    record_hash: str
    patient_id: str
    organization_id: str
    ip_address: str
    timestamp: str
    details: str = ""

    def to_dict(self):
        return asdict(self)


class ConsentManager:
    """
    Manages patient consent for data sharing.

    Workflow:
    1. Doctor searches for patient (by ID or name)
    2. Doctor requests access to patient's records
    3. Patient receives notification
    4. Patient approves/denies with optional time limit
    5. Doctor can access data if approved
    6. All access is logged in audit trail
    """

    def __init__(self, db_path: str = "healthcare.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables for consent management."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Organizations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                org_type TEXT NOT NULL,
                address TEXT,
                license_number TEXT UNIQUE,
                verified INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')

        # User-Organization relationship
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_organizations (
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TEXT NOT NULL,
                PRIMARY KEY (user_id, organization_id)
            )
        ''')

        # Access requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_requests (
                id TEXT PRIMARY KEY,
                doctor_id TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                record_hash TEXT DEFAULT 'all',
                organization_id TEXT,
                organization_name TEXT,
                access_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                responded_at TEXT,
                expires_at TEXT,
                notes TEXT
            )
        ''')

        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_role TEXT NOT NULL,
                action TEXT NOT NULL,
                record_hash TEXT,
                patient_id TEXT,
                organization_id TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL,
                details TEXT
            )
        ''')

        # Active consents (approved access)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_consents (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                record_hash TEXT DEFAULT 'all',
                access_type TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')

        # Patient-level sharing policy for organizations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_hospital_policies (
                patient_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL DEFAULT 'allow_all',
                updated_at TEXT NOT NULL
            )
        ''')

        # Explicit list of organizations allowed by patient
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_allowed_hospitals (
                patient_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (patient_id, organization_id)
            )
        ''')

        conn.commit()
        conn.close()

    # ============== Organization Management ==============

    def create_organization(self, name: str, org_type: str, address: str,
                           license_number: str) -> Organization:
        """Create a new organization."""
        org_id = secrets.token_hex(16)
        created_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO organizations (id, name, org_type, address, license_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (org_id, name, org_type, address, license_number, created_at))

        conn.commit()
        conn.close()

        return Organization(
            id=org_id,
            name=name,
            org_type=OrganizationType(org_type),
            address=address,
            license_number=license_number,
            created_at=created_at
        )

    def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM organizations WHERE id = ?', (org_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Organization(
                id=row[0], name=row[1], org_type=OrganizationType(row[2]),
                address=row[3], license_number=row[4], verified=bool(row[5]),
                created_at=row[6]
            )
        return None

    def get_all_organizations(self) -> List[Organization]:
        """Get all organizations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM organizations')
        rows = cursor.fetchall()
        conn.close()

        return [
            Organization(
                id=row[0], name=row[1], org_type=OrganizationType(row[2]),
                address=row[3], license_number=row[4], verified=bool(row[5]),
                created_at=row[6]
            )
            for row in rows
        ]

    def add_user_to_organization(self, user_id: str, org_id: str, role: str = "member"):
        """Add user to organization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO user_organizations (user_id, organization_id, role, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, org_id, role, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_user_organization(self, user_id: str) -> Optional[Organization]:
        """Get user's organization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT o.* FROM organizations o
            JOIN user_organizations uo ON o.id = uo.organization_id
            WHERE uo.user_id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return Organization(
                id=row[0], name=row[1], org_type=OrganizationType(row[2]),
                address=row[3], license_number=row[4], verified=bool(row[5]),
                created_at=row[6]
            )
        return None

    def get_user_organizations(self, user_id: str) -> List[Organization]:
        """
        Get ALL organizations a user belongs to (a user can belong to more
        than one - get_user_organization() above only surfaces one for the
        existing single-org UI flows). Used where a user needs to pick which
        of their orgs applies to a specific action (e.g. a doctor issuing a
        prescription under one of several hospitals they're affiliated with).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT o.* FROM organizations o
            JOIN user_organizations uo ON o.id = uo.organization_id
            WHERE uo.user_id = ?
            ORDER BY o.name
        ''', (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            Organization(
                id=row[0], name=row[1], org_type=OrganizationType(row[2]),
                address=row[3], license_number=row[4], verified=bool(row[5]),
                created_at=row[6]
            )
            for row in rows
        ]

    def get_owned_organizations(self, user_id: str) -> List[Organization]:
        """Get organizations where this user holds the 'owner' membership role."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT o.* FROM organizations o
            JOIN user_organizations uo ON o.id = uo.organization_id
            WHERE uo.user_id = ? AND uo.role = 'owner'
            ORDER BY o.name
        ''', (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            Organization(
                id=row[0], name=row[1], org_type=OrganizationType(row[2]),
                address=row[3], license_number=row[4], verified=bool(row[5]),
                created_at=row[6]
            )
            for row in rows
        ]

    def is_org_owner(self, user_id: str, org_id: str) -> bool:
        """Check whether a user holds the 'owner' membership role for a specific organization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 1 FROM user_organizations
            WHERE user_id = ? AND organization_id = ? AND role = 'owner'
        ''', (user_id, org_id))

        found = cursor.fetchone() is not None
        conn.close()
        return found

    # ============== Access Request Management ==============

    def create_access_request(self, doctor_id: str, doctor_name: str,
                              patient_id: str, patient_name: str,
                              reason: str, access_type: str = "view",
                              record_hash: str = "all",
                              organization_id: str = None,
                              organization_name: str = None) -> AccessRequest:
        """Create a new access request from doctor to patient."""
        request_id = secrets.token_hex(16)
        requested_at = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO access_requests
            (id, doctor_id, doctor_name, patient_id, patient_name, record_hash,
             organization_id, organization_name, access_type, reason, status, requested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (request_id, doctor_id, doctor_name, patient_id, patient_name,
              record_hash, organization_id, organization_name, access_type,
              reason, AccessStatus.PENDING.value, requested_at))

        conn.commit()
        conn.close()

        return AccessRequest(
            id=request_id, doctor_id=doctor_id, doctor_name=doctor_name,
            patient_id=patient_id, patient_name=patient_name,
            record_hash=record_hash, organization_id=organization_id or "",
            organization_name=organization_name or "",
            access_type=AccessType(access_type), reason=reason,
            status=AccessStatus.PENDING, requested_at=requested_at
        )

    def get_pending_requests_for_patient(self, patient_id: str) -> List[AccessRequest]:
        """Get all pending access requests for a patient."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM access_requests
            WHERE patient_id = ? AND status = ?
            ORDER BY requested_at DESC
        ''', (patient_id, AccessStatus.PENDING.value))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_access_request(row) for row in rows]

    def get_requests_by_doctor(self, doctor_id: str) -> List[AccessRequest]:
        """Get all access requests made by a doctor."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM access_requests
            WHERE doctor_id = ?
            ORDER BY requested_at DESC
        ''', (doctor_id,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_access_request(row) for row in rows]

    def get_request_by_id(self, request_id: str) -> Optional[AccessRequest]:
        """Get a single access request by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM access_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None
        return self._row_to_access_request(row)

    def approve_request(self, request_id: str, patient_id: str,
                        duration_days: int = 30, notes: str = "") -> bool:
        """Patient approves an access request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        responded_at = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()

        # Update request status
        cursor.execute('''
            UPDATE access_requests
            SET status = ?, responded_at = ?, expires_at = ?, notes = ?
            WHERE id = ? AND patient_id = ? AND status = ?
        ''', (AccessStatus.APPROVED.value, responded_at, expires_at, notes,
              request_id, patient_id, AccessStatus.PENDING.value))

        if cursor.rowcount == 0:
            conn.close()
            return False

        # Get request details
        cursor.execute('SELECT * FROM access_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()

        # Create active consent
        consent_id = secrets.token_hex(16)
        cursor.execute('''
            INSERT INTO active_consents
            (id, request_id, doctor_id, patient_id, record_hash, access_type, granted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (consent_id, request_id, row[1], row[3], row[5], row[8], responded_at, expires_at))

        conn.commit()
        conn.close()
        return True

    def deny_request(self, request_id: str, patient_id: str, notes: str = "") -> bool:
        """Patient denies an access request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE access_requests
            SET status = ?, responded_at = ?, notes = ?
            WHERE id = ? AND patient_id = ? AND status = ?
        ''', (AccessStatus.DENIED.value, datetime.now().isoformat(), notes,
              request_id, patient_id, AccessStatus.PENDING.value))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def revoke_access(self, consent_id: str, patient_id: str) -> bool:
        """Patient revokes previously granted access."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE active_consents
            SET is_active = 0
            WHERE id = ? AND patient_id = ?
        ''', (consent_id, patient_id))

        # Also update the original request
        cursor.execute('''
            UPDATE access_requests
            SET status = ?
            WHERE id = (SELECT request_id FROM active_consents WHERE id = ?)
        ''', (AccessStatus.REVOKED.value, consent_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def check_access(self, doctor_id: str, patient_id: str, record_hash: str = None) -> bool:
        """Check if doctor has valid access to patient's records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Check for valid active consent
        if record_hash:
            cursor.execute('''
                SELECT COUNT(*) FROM active_consents
                WHERE doctor_id = ? AND patient_id = ?
                AND (record_hash = ? OR record_hash = 'all')
                AND is_active = 1
                AND (expires_at IS NULL OR expires_at > ?)
            ''', (doctor_id, patient_id, record_hash, now))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM active_consents
                WHERE doctor_id = ? AND patient_id = ?
                AND is_active = 1
                AND (expires_at IS NULL OR expires_at > ?)
            ''', (doctor_id, patient_id, now))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def get_active_consents_for_patient(self, patient_id: str) -> List[Dict]:
        """Get all active consents (who has access to patient's data)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ac.*, ar.doctor_name, ar.organization_name, ar.reason
            FROM active_consents ac
            JOIN access_requests ar ON ac.request_id = ar.id
            WHERE ac.patient_id = ? AND ac.is_active = 1
            ORDER BY ac.granted_at DESC
        ''', (patient_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'consent_id': row[0],
                'request_id': row[1],
                'doctor_id': row[2],
                'doctor_name': row[9],
                'patient_id': row[3],
                'record_hash': row[4],
                'access_type': row[5],
                'granted_at': row[6],
                'expires_at': row[7],
                'organization_name': row[10],
                'reason': row[11]
            }
            for row in rows
        ]

    def get_active_consent_by_id(self, consent_id: str, patient_id: str = None) -> Optional[Dict]:
        """Get a single active consent by ID (optionally scoped to patient)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if patient_id:
            cursor.execute('''
                SELECT ac.*, ar.doctor_name, ar.organization_name, ar.reason
                FROM active_consents ac
                JOIN access_requests ar ON ac.request_id = ar.id
                WHERE ac.id = ? AND ac.patient_id = ?
            ''', (consent_id, patient_id))
        else:
            cursor.execute('''
                SELECT ac.*, ar.doctor_name, ar.organization_name, ar.reason
                FROM active_consents ac
                JOIN access_requests ar ON ac.request_id = ar.id
                WHERE ac.id = ?
            ''', (consent_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'consent_id': row[0],
            'request_id': row[1],
            'doctor_id': row[2],
            'patient_id': row[3],
            'record_hash': row[4],
            'access_type': row[5],
            'granted_at': row[6],
            'expires_at': row[7],
            'is_active': bool(row[8]),
            'doctor_name': row[9],
            'organization_name': row[10],
            'reason': row[11]
        }

    def get_accessible_patients(self, doctor_id: str) -> List[Dict]:
        """Get list of patients the doctor has access to."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute('''
            SELECT DISTINCT ac.patient_id, ar.patient_name, ac.access_type,
                   ac.granted_at, ac.expires_at, ac.record_hash
            FROM active_consents ac
            JOIN access_requests ar ON ac.request_id = ar.id
            WHERE ac.doctor_id = ? AND ac.is_active = 1
            AND (ac.expires_at IS NULL OR ac.expires_at > ?)
        ''', (doctor_id, now))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'patient_id': row[0],
                'patient_name': row[1],
                'access_type': row[2],
                'granted_at': row[3],
                'expires_at': row[4],
                'record_hash': row[5]
            }
            for row in rows
        ]

    # ============== Patient Sharing Preferences ==============

    def set_patient_hospital_policy(self, patient_id: str, mode: str,
                                    organization_ids: List[str] = None) -> bool:
        """
        Set patient sharing policy for organizations.

        Args:
            patient_id: Patient user id
            mode: allow_all, allow_selected, deny_all
            organization_ids: Optional list used when mode is allow_selected
        """
        if mode not in {'allow_all', 'allow_selected', 'deny_all'}:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO patient_hospital_policies (patient_id, mode, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                mode = excluded.mode,
                updated_at = excluded.updated_at
        ''', (patient_id, mode, now))

        # Reset explicit allowlist and repopulate if needed
        cursor.execute('DELETE FROM patient_allowed_hospitals WHERE patient_id = ?', (patient_id,))

        if mode == 'allow_selected' and organization_ids:
            cursor.executemany('''
                INSERT OR IGNORE INTO patient_allowed_hospitals (patient_id, organization_id, added_at)
                VALUES (?, ?, ?)
            ''', [(patient_id, org_id, now) for org_id in organization_ids])

        conn.commit()
        conn.close()
        return True

    def get_patient_hospital_policy(self, patient_id: str) -> Dict[str, Any]:
        """Get patient organization sharing policy."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT mode FROM patient_hospital_policies
            WHERE patient_id = ?
        ''', (patient_id,))
        mode_row = cursor.fetchone()
        mode = mode_row[0] if mode_row else 'allow_all'

        cursor.execute('''
            SELECT organization_id FROM patient_allowed_hospitals
            WHERE patient_id = ?
            ORDER BY organization_id
        ''', (patient_id,))
        organizations = [row[0] for row in cursor.fetchall()]

        conn.close()
        return {
            'patient_id': patient_id,
            'mode': mode,
            'organization_ids': organizations
        }

    def is_hospital_allowed_for_patient(self, patient_id: str, organization_id: str) -> bool:
        """Check if patient's sharing policy allows a specific organization."""
        # Missing organization_id means we cannot verify external trust scope.
        if not organization_id:
            return False

        policy = self.get_patient_hospital_policy(patient_id)
        mode = policy['mode']

        if mode == 'deny_all':
            return False
        if mode == 'allow_all':
            return True
        return organization_id in set(policy['organization_ids'])

    # ============== Audit Logging ==============

    def log_access(self, user_id: str, user_name: str, user_role: str,
                   action: str, record_hash: str, patient_id: str,
                   organization_id: str = None, ip_address: str = "",
                   details: str = ""):
        """Log an access event."""
        log_id = secrets.token_hex(16)
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO audit_log
            (id, user_id, user_name, user_role, action, record_hash,
             patient_id, organization_id, ip_address, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (log_id, user_id, user_name, user_role, action, record_hash,
              patient_id, organization_id, ip_address, timestamp, details))

        conn.commit()
        conn.close()

    def get_audit_log_for_patient(self, patient_id: str, limit: int = 50) -> List[AuditLog]:
        """Get audit log for a patient's records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM audit_log
            WHERE patient_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (patient_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            AuditLog(
                id=row[0], user_id=row[1], user_name=row[2], user_role=row[3],
                action=row[4], record_hash=row[5], patient_id=row[6],
                organization_id=row[7], ip_address=row[8], timestamp=row[9],
                details=row[10] or ""
            )
            for row in rows
        ]

    def get_audit_log_for_record(self, record_hash: str) -> List[AuditLog]:
        """Get audit log for a specific record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM audit_log
            WHERE record_hash = ?
            ORDER BY timestamp DESC
        ''', (record_hash,))

        rows = cursor.fetchall()
        conn.close()

        return [
            AuditLog(
                id=row[0], user_id=row[1], user_name=row[2], user_role=row[3],
                action=row[4], record_hash=row[5], patient_id=row[6],
                organization_id=row[7], ip_address=row[8], timestamp=row[9],
                details=row[10] or ""
            )
            for row in rows
        ]

    # ============== Helper Methods ==============

    def _row_to_access_request(self, row) -> AccessRequest:
        """Convert database row to AccessRequest object."""
        return AccessRequest(
            id=row[0], doctor_id=row[1], doctor_name=row[2],
            patient_id=row[3], patient_name=row[4], record_hash=row[5],
            organization_id=row[6] or "", organization_name=row[7] or "",
            access_type=AccessType(row[8]), reason=row[9],
            status=AccessStatus(row[10]), requested_at=row[11],
            responded_at=row[12] or "", expires_at=row[13] or "",
            notes=row[14] or ""
        )

    def search_patients(self, search_term: str, auth_manager) -> List[Dict]:
        """Search for patients (for doctors to request access)."""
        # This uses the auth_manager to search users
        users = auth_manager.get_all_users()
        results = []

        for user in users:
            if user.role.value == 'patient':
                if (search_term.lower() in user.username.lower() or
                    search_term.lower() in user.full_name.lower() or
                    search_term.lower() in user.email.lower()):
                    results.append({
                        'id': user.id,
                        'username': user.username,
                        'full_name': user.full_name,
                        'email': user.email[:3] + '***' + user.email[-10:]  # Partially hide email
                    })

        return results