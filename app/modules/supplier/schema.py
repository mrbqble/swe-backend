"""Supplier schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SupplierResponse(BaseModel):
    """Schema for supplier response."""

    model_config = ConfigDict(from_attributes=True, strict=True)

    id: int
    company_name: str
    is_active: bool
    created_at: datetime


class SupplierUpdate(BaseModel):
    """Schema for supplier update."""

    model_config = ConfigDict(from_attributes=True, strict=False)

    company_name: str | None = None
    is_active: bool | None = None
