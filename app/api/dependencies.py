"""API dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ErrorMessages
from app.core.roles import Role
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.user.model import User
from app.utils.helpers import get_user_by_id


class HTTPBearer401(HTTPBearer):
    """HTTPBearer that returns 401 instead of 403 for missing credentials."""

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """Override to return 401 for missing credentials instead of 403."""
        try:
            return await super().__call__(request)
        except HTTPException as e:
            # Convert 403 (Forbidden) to 401 (Unauthorized) for missing/invalid credentials
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorMessages.COULD_NOT_VALIDATE_CREDENTIALS,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise


_http_bearer = HTTPBearer401()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_http_bearer)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None or (user_id := payload.get("sub")) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.COULD_NOT_VALIDATE_CREDENTIALS
            if payload is None
            else ErrorMessages.INVALID_TOKEN_PAYLOAD,
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user_by_id(user_id, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.USER_NOT_FOUND,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.USER_INACTIVE,
        )
    return user


def require_roles(*roles: Role):
    """Dependency factory to require specific roles."""

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        """Check if current user has required role."""
        try:
            user_role = Role(current_user.role)
        except ValueError:
            user_role = None
        if user_role is None or user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
            )
        return current_user

    return role_checker
