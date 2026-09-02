"""
Prescription Management for Healthcare Blockchain System

A prescription is created once by a doctor for a patient they are
actively consulting (an active consent must already exist - this
module does not re-check consent itself, same convention as ChatManager;
the app layer is the enforcement point).

Lifecycle (only 2 states are ever written to the database):
    not_started -> started

Two more states are DERIVED, never stored, computed at read time from
today's date vs. end_date:
    not_started + past end_date  => "expired"   (patient never redeemed it)
    started     + past end_date  => "completed"  (course finished)

This keeps the feature free of any background job/scheduler - a
prescription's displayed status is always correct the moment it's
looked at, without needing a cron task to "expire" things in the DB.

Org handling: the doctor explicitly picks which of their organizations
a prescription is issued under (a doctor can belong to more than one
org - see ConsentManager.get_user_organizations). That choice is
snapshotted onto the prescription permanently at creation time, so a
pharmacist's org-scoped search is always a single, unambiguous
equality check, regardless of what the doctor's org memberships look
like later.
"""

import sqlite3
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Dict, Optional


# Preset course durations offered in the "write prescription" form.
# Keys are what gets stored (durable, language-independent); labels are display-only.
DURATION_PRESETS = {
    '7d': {'label': '7 Days', 'days': 7},
    '14d': {'label': '14 Days', 'days': 14},
    '1m': {'label': '1 Month', 'days': 30},
    '3m': {'label': '3 Months', 'days': 90},
    '6m': {'label': '6 Months', 'days': 180},
    '1y': {'label': '1 Year', 'days': 365},
}

STATUS_NOT_STARTED = 'not_started'
STATUS_STARTED = 'started'
# The two derived, never-stored statuses:
STATUS_EXPIRED = 'expired'
STATUS_COMPLETED = 'completed'

_RX_UID_ALPHABET = string.ascii_uppercase + string.digits


def _generate_rx_uid() -> str:
    """
    Short, human-readable ID a patient can read aloud to a pharmacist.
    Format: RX-XXXXXX (6 chars from an alphabet with no ambiguous
    characters like 0/O or 1/I, since this gets communicated verbally).
    """
    alphabet = _RX_UID_ALPHABET.translate(str.maketrans('', '', 'O0I1'))
    suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"RX-{suffix}"


class PrescriptionManager:
    """Manages prescriptions: creation by doctors, viewing by patients, dispensing by pharmacists."""

    def __init__(self, db_path: str = "healthcare.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescriptions (
                id TEXT PRIMARY KEY,
                rx_uid TEXT UNIQUE NOT NULL,
                doctor_id TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                org_id TEXT NOT NULL,
                org_name TEXT NOT NULL,
                content TEXT NOT NULL,
                duration_key TEXT NOT NULL,
                duration_label TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'not_started',
                created_at TEXT NOT NULL,
                dispensed_at TEXT,
                dispensed_by TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rx_patient ON prescriptions (patient_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rx_doctor ON prescriptions (doctor_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rx_org ON prescriptions (org_id)
        ''')

        conn.commit()
        conn.close()

    # ============== Status computation (derived, never persisted) ==============

    @staticmethod
    def compute_display_status(stored_status: str, end_date: str) -> str:
        """
        Turn the 2 stored statuses into the 4 user-facing ones by comparing
        against today's date. Pure function, no DB access - safe to call on
        any row dict without a round trip.
        """
        try:
            is_past_end = datetime.now() >= datetime.fromisoformat(end_date)
        except (ValueError, TypeError):
            is_past_end = False

        if stored_status == STATUS_STARTED:
            return STATUS_COMPLETED if is_past_end else STATUS_STARTED
        # stored_status == STATUS_NOT_STARTED
        return STATUS_EXPIRED if is_past_end else STATUS_NOT_STARTED

    # ============== Creation (doctor) ==============

    def create_prescription(self, doctor_id: str, doctor_name: str,
                             patient_id: str, patient_name: str,
                             org_id: str, org_name: str,
                             content: str, duration_key: str) -> Optional[Dict]:
        """
        Create a new prescription. Caller (app layer) must already have
        verified: (a) an active consent exists between doctor and patient,
        and (b) the doctor actually belongs to org_id.

        Returns the stored prescription dict, or None if inputs were invalid.
        """
        content = (content or "").strip()
        if not content:
            return None
        if duration_key not in DURATION_PRESETS:
            return None

        preset = DURATION_PRESETS[duration_key]
        start = datetime.now()
        end = start + timedelta(days=preset['days'])

        rx_id = secrets.token_hex(16)
        # rx_uid is meant to be unique and short; collisions are astronomically
        # unlikely with a 6-char alphanumeric space, but guard anyway.
        rx_uid = _generate_rx_uid()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for _ in range(5):
            cursor.execute('SELECT 1 FROM prescriptions WHERE rx_uid = ?', (rx_uid,))
            if cursor.fetchone() is None:
                break
            rx_uid = _generate_rx_uid()

        created_at = start.isoformat()
        cursor.execute('''
            INSERT INTO prescriptions
            (id, rx_uid, doctor_id, doctor_name, patient_id, patient_name,
             org_id, org_name, content, duration_key, duration_label,
             start_date, end_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (rx_id, rx_uid, doctor_id, doctor_name, patient_id, patient_name,
              org_id, org_name, content, duration_key, preset['label'],
              created_at, end.isoformat(), STATUS_NOT_STARTED, created_at))

        conn.commit()
        conn.close()

        return self.get_by_uid(rx_uid)

    # ============== Reading ==============

    @staticmethod
    def _row_to_dict(row) -> Dict:
        d = {
            'id': row[0], 'rx_uid': row[1], 'doctor_id': row[2], 'doctor_name': row[3],
            'patient_id': row[4], 'patient_name': row[5], 'org_id': row[6], 'org_name': row[7],
            'content': row[8], 'duration_key': row[9], 'duration_label': row[10],
            'start_date': row[11], 'end_date': row[12], 'status': row[13],
            'created_at': row[14], 'dispensed_at': row[15], 'dispensed_by': row[16],
        }
        d['display_status'] = PrescriptionManager.compute_display_status(d['status'], d['end_date'])
        return d

    def get_by_uid(self, rx_uid: str) -> Optional[Dict]:
        """Look up a single prescription by its human-readable ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM prescriptions WHERE rx_uid = ?', (rx_uid.strip().upper(),))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def get_for_patient(self, patient_id: str, page: int = 1, per_page: int = 10) -> Dict:
        """Paginated prescription history for a patient, newest first."""
        page = max(1, page)
        offset = (page - 1) * per_page

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM prescriptions WHERE patient_id = ?', (patient_id,))
        total = cursor.fetchone()[0]

        cursor.execute('''
            SELECT * FROM prescriptions
            WHERE patient_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (patient_id, per_page, offset))
        rows = cursor.fetchall()
        conn.close()

        return {
            'items': [self._row_to_dict(r) for r in rows],
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': max(1, (total + per_page - 1) // per_page),
        }

    def get_for_doctor(self, doctor_id: str, limit: int = 50) -> List[Dict]:
        """Recent prescriptions written by a doctor (across all their patients/orgs)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM prescriptions
            WHERE doctor_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (doctor_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def find_for_pharmacist(self, rx_uid: str, org_id: str) -> Optional[Dict]:
        """
        Look up a prescription by ID, but ONLY if it was issued under the
        pharmacist's own org. A prescription issued elsewhere simply does
        not appear - the caller cannot distinguish "wrong org" from
        "doesn't exist", which is intentional (no org-enumeration signal).
        """
        rx = self.get_by_uid(rx_uid)
        if not rx or rx['org_id'] != org_id:
            return None
        return rx

    # ============== Dispensing (pharmacist) ==============

    def mark_started(self, rx_uid: str, org_id: str, pharmacist_id: str) -> Optional[Dict]:
        """
        Mark a prescription as dispensed. Scoped to org_id the same way
        find_for_pharmacist is, so a pharmacist cannot dispense a
        prescription from another organization even by guessing a valid ID.

        Returns the updated prescription dict, or None if not found/wrong
        org/already started/already past its window.
        """
        rx = self.find_for_pharmacist(rx_uid, org_id)
        if not rx:
            return None
        if rx['display_status'] != STATUS_NOT_STARTED:
            # Already started, completed, or expired - nothing to do.
            return None

        dispensed_at = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE prescriptions
            SET status = ?, dispensed_at = ?, dispensed_by = ?
            WHERE rx_uid = ? AND org_id = ? AND status = ?
        ''', (STATUS_STARTED, dispensed_at, pharmacist_id, rx['rx_uid'], org_id, STATUS_NOT_STARTED))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return self.get_by_uid(rx_uid) if updated else None