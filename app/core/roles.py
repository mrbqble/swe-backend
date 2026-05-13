"""Role definitions for RBAC."""

import enum


class Role(str, enum.Enum):
    """User roles for iCare platform."""

    PARTNER = "partner"
    ADMIN = "admin"
