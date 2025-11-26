"""Supplier routes."""

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.supplier.schema import SupplierResponse, SupplierUpdate
from app.modules.user.model import User

SupplierRouter = APIRouter(prefix="/suppliers", tags=["suppliers"])


@SupplierRouter.get("/me", response_model=SupplierResponse)
async def get_my_supplier(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated supplier's profile."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError("Only supplier owners can access this endpoint")

    stmt = (
        select(Supplier)
        .where(Supplier.user_id == current_user.id)
        .options(selectinload(Supplier.user))
    )
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    return supplier


@SupplierRouter.put("/me", response_model=SupplierResponse)
async def update_my_supplier(
    supplier_data: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current authenticated supplier's profile."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError(
            "Only supplier owners can update supplier profile")

    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    # Update fields
    update_data = supplier_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    await db.commit()
    await db.refresh(supplier)

    return supplier


@SupplierRouter.patch("/me/deactivate")
async def deactivate_my_supplier(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate current authenticated supplier's account."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError(
            "Only supplier owners can deactivate supplier account")

    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    supplier.is_active = False
    await db.commit()

    return {"message": "Supplier account deactivated successfully"}


@SupplierRouter.delete("/me")
async def delete_my_supplier(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete current authenticated supplier's account."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError(
            "Only supplier owners can delete supplier account")

    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    await db.delete(supplier)
    await db.commit()

    return {"message": "Supplier account deleted successfully"}


@SupplierRouter.get("/staff", response_model=list[dict[str, Any]])
async def get_supplier_staff(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all staff members for current supplier."""
    if current_user.role not in [Role.SUPPLIER_OWNER, Role.SUPPLIER_MANAGER]:
        raise ApplicationError(
            "Only supplier owners and managers can view staff")

    # Get supplier for current user
    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        # If user is staff, get their supplier
        stmt = (
            select(SupplierStaff)
            .where(SupplierStaff.user_id == current_user.id)
            .options(selectinload(SupplierStaff.supplier))
        )
        result = await db.execute(stmt)
        staff_record = result.scalar_one_or_none()
        if staff_record:
            supplier = staff_record.supplier
        else:
            raise ApplicationError("Supplier not found")

    # Get all staff for this supplier
    stmt = (
        select(SupplierStaff)
        .where(SupplierStaff.supplier_id == supplier.id)
        .options(selectinload(SupplierStaff.user))
    )
    result = await db.execute(stmt)
    staff_list = result.scalars().all()

    return [
        {
            "id": staff.id,
            "user_id": staff.user.id,
            "first_name": staff.user.first_name,
            "last_name": staff.user.last_name,
            "email": staff.user.email,
            "role": staff.staff_role,
            "is_active": staff.user.is_active,
            "created_at": staff.created_at.isoformat(),
        }
        for staff in staff_list
    ]


@SupplierRouter.post("/staff")
async def create_supplier_staff(
    _staff_data: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new staff member for current supplier."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError("Only supplier owners can create staff members")

    # Get supplier for current user
    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    # Create user first (this would typically be done via auth endpoint)
    # For now, we'll assume the user already exists and we're just linking them
    # In a real implementation, you'd create the user via the auth endpoint
    # and then create the SupplierStaff record

    return {"message": "Staff member creation should be done via user registration"}


@SupplierRouter.delete("/staff/{staff_id}")
async def delete_supplier_staff(
    staff_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a staff member from current supplier."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError("Only supplier owners can delete staff members")

    # Get supplier for current user
    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    # Get staff member
    stmt = select(SupplierStaff).where(
        SupplierStaff.id == staff_id,
        SupplierStaff.supplier_id == supplier.id,
    )
    result = await db.execute(stmt)
    staff = result.scalar_one_or_none()

    if not staff:
        raise ApplicationError("Staff member not found")

    await db.delete(staff)
    await db.commit()

    return {"message": "Staff member deleted successfully"}


@SupplierRouter.patch("/staff/{staff_id}/deactivate")
async def deactivate_supplier_staff(
    staff_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a staff member."""
    if current_user.role != Role.SUPPLIER_OWNER:
        raise ApplicationError(
            "Only supplier owners can deactivate staff members")

    # Get supplier for current user
    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    # Get staff member
    stmt = (
        select(SupplierStaff)
        .where(
            SupplierStaff.id == staff_id,
            SupplierStaff.supplier_id == supplier.id,
        )
        .options(selectinload(SupplierStaff.user))
    )
    result = await db.execute(stmt)
    staff = result.scalar_one_or_none()

    if not staff:
        raise ApplicationError("Staff member not found")

    staff.user.is_active = False
    await db.commit()

    return {"message": "Staff member deactivated successfully"}
