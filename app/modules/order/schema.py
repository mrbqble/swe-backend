from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    notes: str | None = Field(None, max_length=500)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    product_name: str
    qty: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    total_amount: Decimal
    currency: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]
