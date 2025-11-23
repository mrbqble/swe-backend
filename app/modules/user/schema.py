"""User response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


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
