"""User routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.consumer.model import Consumer
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.modules.user.schema import PasswordChange, UserResponse, UserUpdate
from app.utils.hashing import hash_password, verify_password
from app.utils.password_policy import validate_password_policy

UserRouter = APIRouter(prefix="/users", tags=["users"])


@UserRouter.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current authenticated user."""
    # Build response with user data
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "organization_name": None,
        "company_name": None,
    }

    # If user is a consumer, fetch and include organization_name and profile_image
    if current_user.role == Role.CONSUMER.value:
        result = await db.execute(
            select(Consumer).where(Consumer.user_id == current_user.id)
        )
        consumer = result.scalar_one_or_none()
        if consumer:
            user_data["organization_name"] = consumer.organization_name
            user_data["profile_image"] = consumer.profile_image

    # If user is supplier staff (owner, manager, or sales), fetch and include company_name
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        # Check if user is supplier owner
        result = await db.execute(
            select(Supplier).where(Supplier.user_id == current_user.id)
        )
        supplier = result.scalar_one_or_none()
        if supplier:
            user_data["company_name"] = supplier.company_name
        else:
            # Check if user is staff (manager or sales) via SupplierStaff
            # Get the supplier_id from SupplierStaff, then fetch the Supplier
            result = await db.execute(
                select(SupplierStaff).where(SupplierStaff.user_id == current_user.id)
            )
            staff = result.scalar_one_or_none()
            if staff:
                # Fetch the supplier to get company_name
                result = await db.execute(
                    select(Supplier).where(Supplier.id == staff.supplier_id)
                )
                supplier = result.scalar_one_or_none()
                if supplier:
                    user_data["company_name"] = supplier.company_name

    return user_data


@UserRouter.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update current authenticated user's profile."""
    # Check if email is being changed and if it's already taken
    if user_data.email and user_data.email != current_user.email:
        from app.utils.helpers import get_user_by_email

        existing_user = await get_user_by_email(user_data.email, db)
        if existing_user and existing_user.id != current_user.id:
            raise ApplicationError("Email already registered")

    # Update user fields
    update_data = user_data.model_dump(exclude_unset=True)
    organization_name = update_data.pop("organization_name", None)
    # Check if profile_image was explicitly provided (even if None)
    # If it's in update_data, it was explicitly set (could be None to remove image)
    profile_image_provided = "profile_image" in update_data
    profile_image = update_data.pop("profile_image", None) if profile_image_provided else None

    for field, value in update_data.items():
        setattr(current_user, field, value)

    # Update consumer fields if provided and user is a consumer
    if current_user.role == Role.CONSUMER.value:
        result = await db.execute(
            select(Consumer).where(Consumer.user_id == current_user.id)
        )
        consumer = result.scalar_one_or_none()
        if consumer:
            if organization_name is not None:
                consumer.organization_name = organization_name
            # Allow setting profile_image to None to remove it (only if explicitly provided)
            if profile_image_provided:
                consumer.profile_image = profile_image
        else:
            raise ApplicationError("Consumer profile not found")

    await db.commit()
    await db.refresh(current_user)

    # Build response with updated data (including organization_name if consumer)
    user_response = {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "organization_name": None,
        "profile_image": None,
        "company_name": None,
    }

    # If user is a consumer, fetch and include organization_name and profile_image
    if current_user.role == Role.CONSUMER.value:
        result = await db.execute(
            select(Consumer).where(Consumer.user_id == current_user.id)
        )
        consumer = result.scalar_one_or_none()
        if consumer:
            user_response["organization_name"] = consumer.organization_name
            user_response["profile_image"] = consumer.profile_image

    # If user is supplier staff, fetch and include company_name
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        result = await db.execute(
            select(Supplier).where(Supplier.user_id == current_user.id)
        )
        supplier = result.scalar_one_or_none()
        if supplier:
            user_response["company_name"] = supplier.company_name
        else:
            result = await db.execute(
                select(SupplierStaff).where(SupplierStaff.user_id == current_user.id)
            )
            staff = result.scalar_one_or_none()
            if staff:
                result = await db.execute(
                    select(Supplier).where(Supplier.id == staff.supplier_id)
                )
                supplier = result.scalar_one_or_none()
                if supplier:
                    user_response["company_name"] = supplier.company_name

    return user_response


@UserRouter.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Change current authenticated user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise ApplicationError("Current password is incorrect")

    # Validate new password
    try:
        validate_password_policy(password_data.new_password)
    except ValueError as e:
        raise ApplicationError(str(e))

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@UserRouter.post("/me/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deactivate current authenticated user's account. Only consumers can deactivate their accounts."""
    # Only consumers can deactivate their accounts
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Only consumers can deactivate their accounts")

    # Deactivate the account
    current_user.is_active = False
    await db.commit()

    return {"message": "Account deactivated successfully"}
