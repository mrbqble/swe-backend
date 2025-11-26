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
                "first_name": "John",
                "last_name": "Doe",
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
    first_name: str = Field(
        ..., min_length=1, max_length=100, description="User first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=100, description="User last name"
    )
    role: Literal[Role.CONSUMER, Role.SUPPLIER_OWNER] = Field(
        ..., description="User role (consumer or supplier_owner)"
    )
    organization_name: str | None = Field(
        None, description="Optional consumer organization name"
    )


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


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "new_password": "NewSecurePass123",
            }
        },
    )

    email: EmailStr = Field(..., description="User email address")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, must contain uppercase, lowercase, and digit)",
    )


class PasswordResetResponse(BaseModel):
    """Password reset response schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "message": "Password reset successfully",
            }
        },
    )

    message: str = Field(..., description="Success message")


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
