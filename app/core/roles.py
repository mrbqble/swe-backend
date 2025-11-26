"""Role definitions for RBAC."""

import enum


class Role(str, enum.Enum):
    """User roles for role-based access control."""

    CONSUMER = "consumer"
    SUPPLIER_OWNER = "supplier_owner"
    SUPPLIER_MANAGER = "supplier_manager"
    SUPPLIER_SALES = "supplier_sales"
