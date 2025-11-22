"""Security utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings
from app.core.roles import Role


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    scopes: list[str] | None = None,
) -> str:
    """
    Create a JWT access token with optional scopes.

    Args:
        data: Token payload data (must include 'sub' for user ID)
        expires_delta: Custom expiration time
        scopes: List of permission scopes (e.g., ['read:orders', 'write:products'])

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    # Add scopes if provided
    if scopes:
        to_encode["scopes"] = scopes

    # Add role-based default scopes if role is in data
    if "role" in data:
        role = data.get("role")
        if role:
            role_scopes = _get_role_scopes(role)
            if role_scopes:
                existing_scopes = set(to_encode.get("scopes", []))
                to_encode["scopes"] = list(existing_scopes | set(role_scopes))

    # Ensure subject is a string to satisfy jwt library validation
    if "sub" in to_encode and to_encode["sub"] is not None:
        try:
            to_encode["sub"] = str(to_encode["sub"])
        except Exception:
            # fallback: remove malformed subject to avoid decode errors
            to_encode.pop("sub", None)

    return jwt.encode(to_encode, str(settings.SECRET_KEY), algorithm=settings.ALGORITHM)


def _get_role_scopes(role: str) -> list[str]:
    """Get default scopes for a role."""
    role_scope_map = {
        Role.ADMIN.value: [
            "read:all",
            "write:all",
            "admin:users",
            "admin:suppliers",
        ],
        Role.CONSUMER.value: [
            "read:own_orders",
            "write:own_orders",
            "read:own_links",
            "write:own_links",
            "read:own_notifications",
        ],
        Role.SUPPLIER_OWNER.value: [
            "read:own_orders",
            "write:own_orders",
            "read:own_products",
            "write:own_products",
            "read:own_links",
            "write:own_links",
            "read:own_notifications",
            "admin:supplier_staff",
        ],
        Role.SUPPLIER_MANAGER.value: [
            "read:own_orders",
            "write:own_orders",
            "read:own_products",
            "write:own_products",
            "read:own_links",
            "read:own_notifications",
        ],
        Role.SUPPLIER_SALES.value: [
            "read:own_orders",
            "read:own_products",
            "read:own_links",
            "read:own_notifications",
            "write:chat",
        ],
    }
    return role_scope_map.get(role, [])


def verify_token_scope(payload: dict[str, Any], required_scope: str) -> bool:
    """
    Verify that token payload has the required scope.

    Args:
        payload: Decoded JWT payload
        required_scope: Required scope (supports wildcards like 'read:*')

    Returns:
        True if scope is present, False otherwise
    """
    scopes = payload.get("scopes", [])

    # Check exact match
    if required_scope in scopes:
        return True

    # Check wildcard match (e.g., 'read:*' matches 'read:orders')
    if "*" in required_scope:
        prefix = required_scope.split("*")[0]
        return any(scope.startswith(prefix) for scope in scopes)

    # Check if 'read:all' or 'write:all' is present for admin-like access
    if required_scope.startswith("read:") and "read:all" in scopes:
        return True

    return required_scope.startswith("write:") and "write:all" in scopes


def decode_access_token(token: str) -> Any:
    """Decode a JWT access token."""
    try:
        payload = jwt.decode(token, str(settings.SECRET_KEY), algorithms=[settings.ALGORITHM])
        # If subject was stored as a string, convert numeric subject back to int
        sub = payload.get("sub")
        if isinstance(sub, str) and sub.isdigit():
            try:
                payload["sub"] = int(sub)
            except Exception:
                # leave as-is if conversion fails
                pass
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None




def create_refresh_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    # Ensure subject is a string in refresh token as well
    if "sub" in to_encode and to_encode["sub"] is not None:
        try:
            to_encode["sub"] = str(to_encode["sub"])
        except Exception:
            to_encode.pop("sub", None)
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, str(settings.SECRET_KEY), algorithm=settings.ALGORITHM)


def decode_refresh_token(token: str) -> Any:
    """Decode a JWT refresh token."""
    try:
        payload = jwt.decode(
            token, str(settings.SECRET_KEY), algorithms=[settings.ALGORITHM]
        )
        # normalize subject type if present
        sub = payload.get("sub")
        if isinstance(sub, str) and sub.isdigit():
            try:
                payload["sub"] = int(sub)
            except Exception:
                pass
        if payload.get("type") != "refresh":
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
