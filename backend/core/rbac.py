"""Role-Based Access Control definitions.

Roles:
    partner      — Full access, can manage cases and export evidence
    associate    — Can view and analyze providers, create cases
    investigator — Can view providers and analytics, read-only cases
    auditor      — Read-only access to dashboards and reports
"""

from enum import Enum
from typing import Dict, Set


class Role(str, Enum):
    PARTNER = "partner"
    ASSOCIATE = "associate"
    INVESTIGATOR = "investigator"
    AUDITOR = "auditor"


# Permissions per role
PERMISSIONS: Dict[Role, Set[str]] = {
    Role.PARTNER: {
        "read:providers", "write:providers",
        "read:cases", "write:cases", "delete:cases",
        "read:analytics", "run:analytics",
        "read:evidence", "export:evidence",
        "read:network", "read:alerts",
        "manage:users", "read:audit_logs",
    },
    Role.ASSOCIATE: {
        "read:providers",
        "read:cases", "write:cases",
        "read:analytics", "run:analytics",
        "read:evidence", "export:evidence",
        "read:network", "read:alerts",
    },
    Role.INVESTIGATOR: {
        "read:providers",
        "read:cases",
        "read:analytics", "run:analytics",
        "read:evidence",
        "read:network", "read:alerts",
    },
    Role.AUDITOR: {
        "read:providers",
        "read:cases",
        "read:analytics",
        "read:alerts",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    return permission in PERMISSIONS.get(role_enum, set())
