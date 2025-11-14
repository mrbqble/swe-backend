from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel

from app.core.config import settings


class Role(str, Enum):
    CONSUMER = "consumer"
    SUPPLIER_OWNER = "supplier_owner"
    SUPPLIER_MANAGER = "supplier_manager"
    SUPPLIER_SALES = "supplier_sales"


class TokenError(Exception):
    """Raised when a JWT cannot be validated."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TokenPayload(BaseModel):
    sub: str
    role: Role
    exp: datetime
    iat: datetime
    token_type: str


def _create_token(
    subject: str,
    role: Role,
    expires_delta: timedelta,
    token_type: str,
    additional_claims: Dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + expires_delta
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "token_type": token_type,
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str,
    role: Role,
    *,
    additional_claims: Dict[str, Any] | None = None,
) -> str:
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(subject, role, expires, "access", additional_claims)


def create_refresh_token(
    subject: str,
    role: Role,
    *,
    additional_claims: Dict[str, Any] | None = None,
) -> str:
    expires = timedelta(days=settings.refresh_token_expire_days)
    return _create_token(subject, role, expires, "refresh", additional_claims)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub", "role", "token_type"]},
    )


def verify_token(token: str, expected_type: str = "access") -> TokenPayload:
    try:
        decoded = decode_token(token)
    except ExpiredSignatureError as exc:
        raise TokenError("Token expired") from exc
    except InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    token_type = decoded.get("token_type")
    if expected_type and token_type != expected_type:
        raise TokenError("Invalid token type")

    try:
        payload = TokenPayload(
            sub=decoded["sub"],
            role=Role(decoded["role"]),
            iat=datetime.fromtimestamp(decoded["iat"], tz=timezone.utc),
            exp=datetime.fromtimestamp(decoded["exp"], tz=timezone.utc),
            token_type=token_type,
        )
    except KeyError as exc:
        raise TokenError(f"Missing claim: {exc.args[0]}") from exc

    return payload


__all__ = [
    "Role",
    "TokenError",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
]
