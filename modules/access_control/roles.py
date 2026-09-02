"""Role-based access control definitions."""

from enum import Enum, auto
from typing import Set, List
from dataclasses import dataclass


class Permission(Enum):
    """Permissions available in the system."""

    # Record permissions
    VIEW_OWN_RECORDS = auto()
    VIEW_ALL_RECORDS = auto()
    UPLOAD_RECORDS = auto()
    DELETE_RECORDS = auto()

    # Access control
    GRANT_ACCESS = auto()
    REVOKE_ACCESS = auto()

    # AI features
    RUN_DIAGNOSIS = auto()
    VIEW_DIAGNOSIS = auto()

    # Prescriptions
    WRITE_PRESCRIPTIONS = auto()
    VIEW_PRESCRIPTIONS = auto()
    DISPENSE_PRESCRIPTIONS = auto()

    # Admin
    MANAGE_USERS = auto()
    VIEW_BLOCKCHAIN = auto()
    VIEW_AUDIT_LOG = auto()

    # Network
    ADD_NODE = auto()
    REMOVE_NODE = auto()


class Role(Enum):
    """User roles in the healthcare system."""

    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    RESEARCHER = "researcher"
    PHARMACIST = "pharmacist"  # Never self-registered; created only by an org owner


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.PATIENT: {
        Permission.VIEW_OWN_RECORDS,
        Permission.UPLOAD_RECORDS,
        Permission.GRANT_ACCESS,
        Permission.REVOKE_ACCESS,
        Permission.VIEW_DIAGNOSIS,
        Permission.VIEW_PRESCRIPTIONS,
    },
    Role.DOCTOR: {
        Permission.VIEW_OWN_RECORDS,
        Permission.VIEW_ALL_RECORDS,  # Can view records they have access to
        Permission.UPLOAD_RECORDS,
        Permission.RUN_DIAGNOSIS,
        Permission.VIEW_DIAGNOSIS,
        Permission.VIEW_BLOCKCHAIN,
        Permission.WRITE_PRESCRIPTIONS,
        Permission.VIEW_PRESCRIPTIONS,
    },
    Role.ADMIN: {
        Permission.VIEW_OWN_RECORDS,
        Permission.VIEW_ALL_RECORDS,
        Permission.UPLOAD_RECORDS,
        Permission.DELETE_RECORDS,
        Permission.GRANT_ACCESS,
        Permission.REVOKE_ACCESS,
        Permission.RUN_DIAGNOSIS,
        Permission.VIEW_DIAGNOSIS,
        Permission.MANAGE_USERS,
        Permission.VIEW_BLOCKCHAIN,
        Permission.VIEW_AUDIT_LOG,
        Permission.ADD_NODE,
        Permission.REMOVE_NODE,
        Permission.VIEW_PRESCRIPTIONS,
    },
    Role.RESEARCHER: {
        Permission.VIEW_ALL_RECORDS,  # Anonymized data
        Permission.RUN_DIAGNOSIS,
        Permission.VIEW_DIAGNOSIS,
        Permission.VIEW_BLOCKCHAIN,
    },
    Role.PHARMACIST: {
        # Deliberately minimal: no record access, no chat, no consent visibility.
        # This role only ever does one thing - look up an rx_uid and dispense it.
        Permission.DISPENSE_PRESCRIPTIONS,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(role)


def get_all_roles() -> List[str]:
    """Get list of all role names."""
    return [role.value for role in Role]


@dataclass
class AccessPolicy:
    """Policy for record access."""

    record_id: str
    owner_id: str
    allowed_users: Set[str]
    allowed_roles: Set[Role]
    is_public: bool = False

    def can_access(self, user_id: str, user_role: Role) -> bool:
        """Check if user can access based on policy."""
        if self.is_public:
            return True
        if user_id == self.owner_id:
            return True
        if user_id in self.allowed_users:
            return True
        if user_role in self.allowed_roles:
            return True
        return False