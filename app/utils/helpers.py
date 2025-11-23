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
