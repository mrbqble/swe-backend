"""Supplier routes."""

from typing import Any
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.supplier.schema import (
    StaffCreateRequest,
    StaffResponse,
    StaffUpdate,
    SupplierResponse,
    SupplierUpdate,
)
from app.modules.user.model import User
from app.utils.helpers import get_user_by_email
from app.utils.hashing import hash_password
from app.utils.password_policy import validate_password_policy

SupplierRouter = APIRouter(prefix="/suppliers", tags=["suppliers"])


@SupplierRouter.get("/me", response_model=SupplierResponse)
async def get_my_supplier(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated supplier's profile."""
    if current_user.role != Role.SUPPLIER_OWNER.value:
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
    if current_user.role != Role.SUPPLIER_OWNER.value:
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
    if current_user.role != Role.SUPPLIER_OWNER.value:
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
    if current_user.role not in [Role.SUPPLIER_OWNER.value, Role.SUPPLIER_MANAGER.value]:
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


@SupplierRouter.post("/staff", response_model=StaffResponse)
async def create_supplier_staff(
    staff_data: StaffCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new staff member (manager or sales rep) for current supplier.

    Only supplier owners can create staff members through the web app.
    """
    if current_user.role != Role.SUPPLIER_OWNER.value:
        raise ApplicationError("Only supplier owners can create staff members")

    # Get supplier for current user
    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    # Check if user already exists
    existing_user = await get_user_by_email(staff_data.email, db)
    if existing_user:
        raise ApplicationError("User with this email already exists")

    # Validate password policy
    try:
        validate_password_policy(staff_data.password)
    except ValueError as e:
        raise ApplicationError(str(e))

    # Determine user role based on staff_role
    if staff_data.staff_role == "manager":
        user_role = Role.SUPPLIER_MANAGER.value
    elif staff_data.staff_role == "sales":
        user_role = Role.SUPPLIER_SALES.value
    else:
        raise ApplicationError(f"Invalid staff role: {staff_data.staff_role}")

    # Create user
    password_hash = hash_password(staff_data.password)
    user = User(
        email=staff_data.email,
        password_hash=password_hash,
        first_name=staff_data.first_name,
        last_name=staff_data.last_name,
        role=user_role,
    )
    db.add(user)
    await db.flush()

    # Create SupplierStaff relationship
    staff = SupplierStaff(
        user_id=user.id,
        supplier_id=supplier.id,
        staff_role=staff_data.staff_role,
        created_at=datetime.now(UTC),
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    await db.refresh(user)

    return StaffResponse(
        id=staff.id,
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=staff.staff_role,
        is_active=user.is_active,
        created_at=staff.created_at,
    )


@SupplierRouter.delete("/staff/{staff_id}")
async def delete_supplier_staff(
    staff_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a staff member from current supplier."""
    if current_user.role != Role.SUPPLIER_OWNER.value:
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
    if current_user.role != Role.SUPPLIER_OWNER.value:
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


@SupplierRouter.patch("/staff/{staff_id}/activate")
async def activate_supplier_staff(
    staff_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate a previously deactivated staff member."""
    if current_user.role != Role.SUPPLIER_OWNER.value:
        raise ApplicationError("Only supplier owners can activate staff members")

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

    staff.user.is_active = True
    await db.commit()

    return {"message": "Staff member activated successfully"}


@SupplierRouter.patch("/staff/{staff_id}", response_model=StaffResponse)
async def update_supplier_staff(
    staff_id: int,
    staff_data: StaffUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing staff member's details (name, email, role)."""
    if current_user.role != Role.SUPPLIER_OWNER.value:
        raise ApplicationError("Only supplier owners can update staff members")

    # Get supplier for current user
    stmt = select(Supplier).where(Supplier.user_id == current_user.id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise ApplicationError("Supplier profile not found")

    # Get staff member belonging to this supplier
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

    user = staff.user

    # If email is being changed, ensure it's not taken by another user
    if staff_data.email and staff_data.email != user.email:
        existing_user = await get_user_by_email(staff_data.email, db)
        if existing_user and existing_user.id != user.id:
            raise ApplicationError("User with this email already exists")
        user.email = staff_data.email

    # Update first/last name if provided
    if staff_data.first_name is not None:
        user.first_name = staff_data.first_name
    if staff_data.last_name is not None:
        user.last_name = staff_data.last_name

    # Update staff role if provided
    if staff_data.staff_role is not None:
        if staff_data.staff_role == "manager":
            user.role = Role.SUPPLIER_MANAGER.value
        elif staff_data.staff_role == "sales":
            user.role = Role.SUPPLIER_SALES.value
        else:
            raise ApplicationError(f"Invalid staff role: {staff_data.staff_role}")
        staff.staff_role = staff_data.staff_role

    await db.commit()
    await db.refresh(staff)
    await db.refresh(user)

    return StaffResponse(
        id=staff.id,
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=staff.staff_role,
        is_active=user.is_active,
        created_at=staff.created_at,
    )
