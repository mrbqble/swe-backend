from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    description: str | None
    price: Decimal
    currency: str
    stock_qty: int
    available_qty: int  # stock_qty minus active cart reservations — injected at query time
    unit: str
    min_order_qty: int
    category: str | None
    image_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
