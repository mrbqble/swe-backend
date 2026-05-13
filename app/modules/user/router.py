"""User routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.user.model import User
from app.modules.user.schema import UpdateProfileRequest, UserProfile
from app.utils.helpers import get_user_by_email

UserRouter = APIRouter(prefix="/users", tags=["users"])


@UserRouter.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current authenticated user's profile."""
    return current_user


@UserRouter.patch("/me", response_model=UserProfile)
async def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update current authenticated user's profile."""
    update_dict = data.model_dump(exclude_unset=True)

    if "email" in update_dict and update_dict["email"] is not None:
        new_email = str(update_dict["email"])
        if new_email != current_user.email:
            existing = await get_user_by_email(new_email, db)
            if existing and existing.id != current_user.id:
                raise ApplicationError("Email already registered.")
        update_dict["email"] = new_email

    for field, value in update_dict.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user
