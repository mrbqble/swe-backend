from datetime import datetime

from pydantic import BaseModel, field_validator


class BindIpTooRequest(BaseModel):
    iin_bin: str

    @field_validator("iin_bin")
    @classmethod
    def validate_iin_bin(cls, v: str) -> str:
        if not (v.isdigit() and len(v) == 12):
            raise ValueError("IIN/BIN must be exactly 12 digits")
        return v


class IpTooResponse(BaseModel):
    id: int
    user_id: int
    type: str
    iin_bin: str
    name: str | None
    status: str
    rejection_reason: str | None
    verified_at: datetime | None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
