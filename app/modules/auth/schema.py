"""Authentication request/response schemas."""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.phone import normalize_phone, validate_e164


class SendOtpRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    phone: str = Field(..., description="Phone number in E.164 format")

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized


class VerifyOtpRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    phone: str = Field(..., description="Phone number in E.164 format")
    code: str = Field(..., description="6-digit OTP code", min_length=6, max_length=6)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be exactly 6 digits")
        return v


class RegisterRequest(BaseModel):
    model_config = ConfigDict(strict=False)  # date fields need string coercion from JSON

    phone: str = Field(..., description="Phone number in E.164 format")
    code: str = Field(..., description="Verified OTP code", min_length=6, max_length=6)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    dob: date = Field(..., description="Date of birth")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password (min 8 chars, 1 letter, 1 digit, 1 special char)")
    city: str | None = Field(None, max_length=100)
    ref_code: str = Field(..., description="Referral code of the inviting partner")
    consent: bool = Field(..., description="User must consent to terms")

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be exactly 6 digits")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("consent")
    @classmethod
    def validate_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must consent to the terms to register")
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    phone: str = Field(..., description="Phone number in E.164 format")
    password: str = Field(..., description="User password")

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized


class RefreshRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
