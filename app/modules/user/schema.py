"""User schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfile(BaseModel):
    """Response schema for the current user's profile."""

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
    status_tier: str
    is_active: bool
    is_frozen: bool
    team_volume: float
    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    """Partial update for user profile."""

    model_config = ConfigDict(strict=True)

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    patronymic: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    city: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
