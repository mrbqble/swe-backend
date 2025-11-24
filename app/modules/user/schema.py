"""User response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(
        from_attributes=True,
        strict=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": "consumer",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """User update schema."""

    model_config = ConfigDict(from_attributes=True, strict=False)

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)


class PasswordChange(BaseModel):
    """Password change schema."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
