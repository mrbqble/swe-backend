"""User schemas."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    first_name: str
    last_name: str | None
    patronymic: str | None
    dob: date
    email: str | None
    email_confirmed: bool
    city: str | None
    avatar_url: str | None
    ref_code: str
    ref_code_changed: bool
    status_tier: str
    is_active: bool
    is_frozen: bool
    team_volume: float
    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    patronymic: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    city: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    current_password: str
    new_password: str = Field(..., min_length=8)


class SessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_info: dict[str, Any] | None
    ip: str | None
    created_at: datetime
    last_used_at: datetime
    is_current: bool


class ChangeRefCodeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    new_code: str = Field(..., min_length=4, max_length=10)


class DeleteConfirmRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str = Field(..., min_length=6, max_length=6)


class EmailConfirmRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str = Field(..., min_length=6, max_length=6)


class PushTokenRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    token: str = Field(..., min_length=1, max_length=255)
