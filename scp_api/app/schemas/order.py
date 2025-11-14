from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import Field

from app.models.enums import OrderStatus
from app.schemas.base import ORMModel


class OrderItemCreate(ORMModel):
    product_id: int
    qty: int = Field(ge=1)
    unit_price_kzt: Decimal = Field(gt=0)


class OrderCreate(ORMModel):
    supplier_id: int
    consumer_id: int
    items: List[OrderItemCreate]


class OrderItemRead(ORMModel):
    id: int
    product_id: int
    qty: int
    unit_price_kzt: Decimal


class OrderRead(ORMModel):
    id: int
    supplier_id: int
    consumer_id: int
    status: OrderStatus
    total_kzt: Decimal
    created_at: datetime
    items: List[OrderItemRead]
