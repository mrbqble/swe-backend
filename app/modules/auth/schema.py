"""Authentication request schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.roles import Role


class SignupRequest(BaseModel):
    """Signup request schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "role": "consumer",
            }
        },
    )

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,  # Reasonable max length for passwords
        description="User password (min 8 chars, must contain uppercase, lowercase, and digit)",
    )
    role: Literal[Role.CONSUMER, Role.SUPPLIER_OWNER] = Field(
        ..., description="User role (consumer or supplier_owner)"
    )
    organization_name: str | None = Field(None, description="Optional consumer organization name")


class LoginRequest(BaseModel):
    """Login request schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
            }
        },
    )

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshRequest(BaseModel):
    """Refresh token request schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        },
    )

    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Token response schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        },
    )

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
