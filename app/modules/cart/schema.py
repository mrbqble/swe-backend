from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AddToCartRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    product_id: int = Field(..., gt=0)
    qty: int = Field(..., ge=1)


class UpdateCartRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    qty: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    product_sku: str
    unit_price: Decimal
    currency: str
    qty: int
    subtotal: Decimal
    reserved_until: datetime
    available_qty: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: Decimal
    currency: str
    item_count: int
