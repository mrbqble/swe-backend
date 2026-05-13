"""API dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.user.model import User
from app.utils.helpers import get_user_by_id


class HTTPBearer401(HTTPBearer):
    """HTTPBearer that returns 401 instead of 403 for missing credentials."""

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            credentials = await super().__call__(request)
            if credentials is None:
                raise ApplicationError("Could not validate credentials", status_code=401)
            return credentials
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise ApplicationError("Could not validate credentials", status_code=401)
            raise


http_bearer = HTTPBearer401()
_http_bearer = http_bearer  # backward-compat alias


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated partner from JWT token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise ApplicationError("Could not validate credentials", status_code=401)

    # Reject admin tokens on partner endpoints
    if payload.get("role") == "admin":
        raise ApplicationError("Could not validate credentials", status_code=401)

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise ApplicationError("Invalid token payload", status_code=401)

    try:
        user_id = int(user_id_raw)
    except (ValueError, TypeError):
        raise ApplicationError("Invalid token payload", status_code=401)

    user = await get_user_by_id(user_id, db)
    if user is None:
        raise ApplicationError("User not found", status_code=401)
    if not user.is_active:
        raise ApplicationError("User account is inactive", status_code=403)
    if user.is_frozen:
        raise ApplicationError("Account is frozen", status_code=403)

    return user


async def get_session_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
) -> int | None:
    """Extract session_id (sid) claim from the access token."""
    payload = decode_access_token(credentials.credentials)
    if payload:
        sid = payload.get("sid")
        try:
            return int(sid) if sid is not None else None
        except (ValueError, TypeError):
            return None
    return None


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated admin from JWT token."""
    from app.modules.admin.model import AdminUser

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise ApplicationError("Could not validate credentials", status_code=401)

    if payload.get("role") != "admin":
        raise ApplicationError("Admin access required", status_code=403)

    admin_id_raw = payload.get("sub")
    if admin_id_raw is None:
        raise ApplicationError("Invalid token payload", status_code=401)

    try:
        admin_id = int(admin_id_raw)
    except (ValueError, TypeError):
        raise ApplicationError("Invalid token payload", status_code=401)

    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if admin is None:
        raise ApplicationError("Admin not found", status_code=401)
    if not admin.is_active:
        raise ApplicationError("Admin account is inactive", status_code=403)

    return admin


def require_roles(*roles: Role):
    """Dependency factory to require specific roles."""

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.status_tier not in [r.value for r in roles]:
            raise ApplicationError("Not enough permissions", status_code=403)
        return current_user

    return role_checker
