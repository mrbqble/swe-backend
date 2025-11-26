"""Supplier schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierResponse(BaseModel):
    """Schema for supplier response."""

    model_config = ConfigDict(from_attributes=True, strict=True)

    id: int
    company_name: str
    is_active: bool
    created_at: datetime
    # Base64-encoded company logo (no file upload, stored as string)
    company_logo: str | None = None


class SupplierUpdate(BaseModel):
    """Schema for supplier update."""

    model_config = ConfigDict(from_attributes=True, strict=False)

    company_name: str | None = None
    is_active: bool | None = None
    company_logo: str | None = None


class StaffCreateRequest(BaseModel):
    """Schema for creating a new staff member."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "email": "staff@example.com",
                "password": "SecurePass123",
                "first_name": "John",
                "last_name": "Doe",
                "staff_role": "manager",
            }
        },
    )

    email: EmailStr = Field(..., description="Staff member email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Staff member password (min 8 chars, must contain uppercase, lowercase, and digit)",
    )
    first_name: str = Field(..., min_length=1, max_length=100,
                            description="Staff member first name")
    last_name: str = Field(..., min_length=1, max_length=100,
                           description="Staff member last name")
    staff_role: Literal["manager", "sales"] = Field(
        ..., description="Staff role (manager or sales)"
    )


class StaffResponse(BaseModel):
    """Schema for staff member response."""

    model_config = ConfigDict(from_attributes=True, strict=True)

    id: int
    user_id: int
    first_name: str
    last_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class StaffUpdate(BaseModel):
    """Schema for updating an existing staff member."""

    model_config = ConfigDict(from_attributes=True, strict=False)

    email: EmailStr | None = Field(
        None, description="Updated staff member email address"
    )
    first_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Updated staff member first name",
    )
    last_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Updated staff member last name",
    )
    staff_role: Literal["manager", "sales"] | None = Field(
        None, description="Updated staff role (manager or sales)"
    )
