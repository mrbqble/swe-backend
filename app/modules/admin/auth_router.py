"""Admin authentication routes."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.core.security import create_access_token
from app.db.session import get_db
from app.modules.admin.model import AdminUser
from app.utils.hashing import verify_password

AdminAuthRouter = APIRouter(prefix="/auth", tags=["admin"])

_ADMIN_TOKEN_HOURS = 8


@AdminAuthRouter.post("/login")
async def admin_login(
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin login with email + password. Returns 8-hour access token."""
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    result = await db.execute(
        select(AdminUser).where(AdminUser.email == email)
    )
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(password, admin.password_hash):
        raise ApplicationError("Invalid credentials.")
    if not admin.is_active:
        raise ApplicationError("Admin account is inactive.")

    token = create_access_token(
        data={"sub": str(admin.id), "email": admin.email, "role": "admin"},
        expires_delta=timedelta(hours=_ADMIN_TOKEN_HOURS),
    )
    return {"access_token": token, "token_type": "bearer"}


@AdminAuthRouter.get("/me")
async def admin_me(
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """Return current admin's identity."""
    return {"id": admin.id, "email": admin.email, "name": admin.name}
