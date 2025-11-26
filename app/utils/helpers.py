"""API helper functions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.modules.consumer.model import Consumer
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    """Get user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    print(result)
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: int, db: AsyncSession) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_consumer_by_user_id(user_id: int, db: AsyncSession) -> Consumer | None:
    """Get consumer by user ID."""
    result = await db.execute(select(Consumer).where(Consumer.user_id == user_id))
    return result.scalar_one_or_none()


async def get_supplier_by_user_id(user_id: int, db: AsyncSession) -> Supplier | None:
    """Get supplier by user ID (for supplier owner)."""
    result = await db.execute(select(Supplier).where(Supplier.user_id == user_id))
    return result.scalar_one_or_none()


async def is_supplier_owner_or_manager(
    user: User, supplier_id: int, db: AsyncSession
) -> bool:
    """Check if user is owner or manager of the supplier."""
    # Check if user is supplier owner
    supplier = await get_supplier_by_user_id(user.id, db)
    if supplier and supplier.id == supplier_id:
        return True

    # Check if user is supplier manager
    if user.role == Role.SUPPLIER_MANAGER.value:
        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == user.id,
                SupplierStaff.supplier_id == supplier_id,
                SupplierStaff.staff_role.in_(["manager", "owner"]),
            )
        )
        staff = result.scalar_one_or_none()
        if staff:
            return True

    return False


async def assign_sales_representative(
    supplier_id: int, db: AsyncSession
) -> int:
    """
    Assign a sales representative to a supplier.

    Priority:
    1. Active sales representative (staff_role contains "sales")
    2. Any active staff member
    3. Supplier owner as fallback

    Returns:
        User ID of the assigned sales representative

    Raises:
        ApplicationError: If no sales representative can be found
    """
    from app.core.exceptions import ApplicationError

    # Try to find a sales rep for this supplier
    result = await db.execute(
        select(SupplierStaff)
        .join(User, SupplierStaff.user_id == User.id)
        .where(SupplierStaff.supplier_id == supplier_id)
        .where(SupplierStaff.staff_role.ilike("%sales%"))
        .where(User.is_active)
        .limit(1)
    )
    sales_rep_staff = result.scalar_one_or_none()
    if sales_rep_staff:
        return sales_rep_staff.user_id

    # If no sales rep found, try to get any active staff member
    result = await db.execute(
        select(SupplierStaff)
        .join(User, SupplierStaff.user_id == User.id)
        .where(SupplierStaff.supplier_id == supplier_id)
        .where(User.is_active)
        .limit(1)
    )
    sales_rep_staff = result.scalar_one_or_none()
    if sales_rep_staff:
        return sales_rep_staff.user_id

    # Last resort: try to get the supplier owner
    result = await db.execute(
        select(Supplier)
        .join(User, Supplier.user_id == User.id)
        .where(Supplier.id == supplier_id)
        .where(User.is_active)
    )
    supplier = result.scalar_one_or_none()
    if supplier and supplier.user_id:
        return supplier.user_id

    raise ApplicationError(
        "No sales representative found for this supplier. Please contact support."
    )
