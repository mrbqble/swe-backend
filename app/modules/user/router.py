"""User routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.user.model import User
from app.modules.user.schema import PasswordChange, UserResponse, UserUpdate
from app.utils.hashing import hash_password, verify_password
from app.utils.password_policy import validate_password_policy

UserRouter = APIRouter(prefix="/users", tags=["users"])


@UserRouter.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current authenticated user."""
    return current_user


@UserRouter.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update current authenticated user's profile."""
    # Check if email is being changed and if it's already taken
    if user_data.email and user_data.email != current_user.email:
        from app.utils.helpers import get_user_by_email

        existing_user = await get_user_by_email(user_data.email, db)
        if existing_user and existing_user.id != current_user.id:
            raise ApplicationError("Email already registered")

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return current_user


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
