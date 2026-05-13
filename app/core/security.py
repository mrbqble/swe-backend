"""Security utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire

    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])

    return jwt.encode(to_encode, str(settings.SECRET_KEY), algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Any:
    """Decode a JWT access token. Returns payload or None on failure."""
    try:
        return jwt.decode(token, str(settings.SECRET_KEY), algorithms=[settings.ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
