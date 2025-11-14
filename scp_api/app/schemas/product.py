from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import ORMModel


class ProductCreate(ORMModel):
    supplier_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price_kzt: Decimal = Field(gt=0)
    sku: str | None = Field(default=None, max_length=64)
    stock_qty: int = Field(default=0, ge=0)


class ProductRead(ORMModel):
    id: int
    supplier_id: int
    name: str
    description: str | None
    price_kzt: Decimal
    sku: str | None
    stock_qty: int
    created_at: datetime
