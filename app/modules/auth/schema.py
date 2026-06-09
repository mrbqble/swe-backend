"""Authentication request/response schemas."""

import re
from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.utils.phone import normalize_phone, validate_e164

class SendOtpRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    phone: str = Field(..., description="Phone number in E.164 format")
    purpose: str | None = Field(None, description="Reason for this OTP (registration/login/forgot_password/deletion). Optional tag stored in DB.")

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
    """Registration request — accepts both mobile field names and legacy field names.

    Mobile sends:  full_name / date_of_birth / consent_version / (no code)
    Legacy sent:   first_name+last_name / dob / consent / code
    Both are accepted and normalised by the model_validator.
    Unknown extra fields (e.g. country_code) are silently ignored.
    """
    model_config = ConfigDict(strict=False, extra="ignore")

    phone: str = Field(..., description="Phone number in E.164 format")

    # OTP — optional: mobile verifies via /otp/verify first, so code is not re-sent here.
    # Legacy/test clients may still include it for the dev bypass.
    code: str | None = Field(None, description="OTP code (optional — use /otp/verify first)")

    # Name fields — accept full_name (mobile) OR first_name+last_name (legacy)
    full_name: str | None = Field(None, max_length=255, description="Full name (mobile)")
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)

    # Date of birth — accept date_of_birth (mobile) OR dob (legacy)
    date_of_birth: date | None = Field(None, description="Date of birth (mobile)")
    dob: date | None = Field(None, description="Date of birth (legacy)")

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Account password")
    confirm_password: str = Field(..., description="Password confirmation")
    city: str | None = Field(None, max_length=100)
    ref_code: str = Field(..., description="Referral code of the inviting partner")

    # Consent — accept consent_version (mobile, e.g. "1.0") OR consent bool (legacy)
    consent: bool | None = Field(None)
    consent_version: str | None = Field(None, description="Consent version string (mobile)")

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("Code must be exactly 6 digits")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 64:
            raise ValueError("Password must be at most 64 characters")
        if " " in v:
            raise ValueError("Password must not contain spaces")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @model_validator(mode="after")
    def _normalise_and_validate(self) -> "RegisterRequest":
        # ── Name ──────────────────────────────────────────────────────────────
        if self.full_name and not self.first_name:
            parts = self.full_name.strip().split(maxsplit=1)
            self.first_name = parts[0]
            if len(parts) > 1:
                self.last_name = parts[1]
        if not self.first_name:
            raise ValueError("first_name or full_name is required")

        # ── Date of birth ──────────────────────────────────────────────────────
        if self.date_of_birth and not self.dob:
            self.dob = self.date_of_birth
        if not self.dob:
            raise ValueError("dob or date_of_birth is required")

        # ── Consent ────────────────────────────────────────────────────────────
        if self.consent_version and self.consent is None:
            self.consent = True  # any truthy consent_version string = accepted
        if not self.consent:
            raise ValueError("You must consent to the terms to register")

        # ── Password match ─────────────────────────────────────────────────────
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self


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


# ── Utility responses ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    message: str


class CheckPhoneResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    registered: bool
    account_state: str | None = None  # email_unconfirmed | active | blocked | soft_deleting


class CheckRefCodeResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    valid: bool
    owner_name: str | None = None


# ── Email confirmation ─────────────────────────────────────────────────────────

class ConfirmEmailRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be exactly 6 digits")
        return v


class ChangeEmailRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    new_email: EmailStr


# ── Password reset ─────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    phone: str

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized


def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(v) > 64:
        raise ValueError("Password must be at most 64 characters")
    if " " in v:
        raise ValueError("Password must not contain spaces")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", v):
        raise ValueError("Password must contain at least one special character")
    return v


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(strict=False)
    phone: str
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str
    confirm_password: str

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        normalized = normalize_phone(v)
        if not validate_e164(normalized):
            raise ValueError("Phone must be in E.164 format (e.g. +77771234567)")
        return normalized

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be exactly 6 digits")
        return v

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def _passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# ── Account deletion ───────────────────────────────────────────────────────────

class AccountDeletionRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be exactly 6 digits")
        return v


class CancelDeletionRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    token: str = Field(..., min_length=1)


# ── Sessions ───────────────────────────────────────────────────────────────────

class SessionInfoResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int
    device_info: dict | None = None
    city: str | None = None
    last_active: str
    is_current: bool


class SessionListResponse(BaseModel):
    model_config = ConfigDict(strict=True)
    sessions: list[SessionInfoResponse]


# ── Ref code ───────────────────────────────────────────────────────────────────

_REF_CODE_RESERVED = frozenset({
    "ADMIN", "ROOT", "ICARE", "LULU", "BAYBEE", "TEST", "SYSTEM", "SUPPORT", "HELP",
})
_REF_CODE_RE = re.compile(r"^[A-Z0-9]{4,10}$")


class ChangeRefCodeRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    new_ref_code: str

    @field_validator("new_ref_code", mode="before")
    @classmethod
    def _validate_ref_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not _REF_CODE_RE.match(v):
            raise ValueError("Ref code must be 4–10 Latin letters (A–Z) or digits (0–9)")
        if v in _REF_CODE_RESERVED:
            raise ValueError("This ref code is reserved and cannot be used")
        return v
