"""Order schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.order.model import OrderStatus
from app.modules.user.schema import UserResponse


class OrderItemCreate(BaseModel):
    """Schema for creating an order item."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "product_id": 1,
                "qty": 5,
            }
        },
    )

    product_id: int = Field(..., description="Product ID")
    qty: int = Field(..., gt=0, description="Quantity (must be positive)")


class OrderCreate(BaseModel):
    """Schema for creating an order."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "supplier_id": 1,
                "items": [
                    {"product_id": 1, "qty": 5},
                    {"product_id": 2, "qty": 3},
                ],
            }
        },
    )

    supplier_id: int = Field(..., description="Supplier ID")
    items: list[OrderItemCreate] = Field(..., min_length=1, description="Order items")


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""

    model_config = ConfigDict(
        strict=False,  # Allow string values for enum when deserializing from JSON
        json_schema_extra={
            "example": {
                "status": "accepted",
            }
        },
    )

    status: OrderStatus = Field(..., description="New order status")


class OrderItemResponse(BaseModel):
    """Schema for order item response."""

    model_config = ConfigDict(
        from_attributes=True,
        strict=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "order_id": 1,
                "product_id": 1,
                "qty": 5,
                "unit_price_kzt": "15000.00",
            }
        },
    )

    id: int = Field(..., description="Order item ID")
    order_id: int = Field(..., description="Order ID")
    product_id: int = Field(..., description="Product ID")
    qty: int = Field(..., description="Quantity")
    unit_price_kzt: Decimal = Field(..., description="Unit price in KZT")


class SupplierInfo(BaseModel):
    """Schema for supplier information in order response."""

    model_config = ConfigDict(from_attributes=True, strict=False)

    id: int = Field(..., description="Supplier ID")
    company_name: str = Field(..., description="Company name")


class ConsumerInfo(BaseModel):
    """Schema for consumer information in order response."""

    model_config = ConfigDict(from_attributes=True, strict=False)

    id: int = Field(..., description="Consumer ID")
    organization_name: str = Field(..., description="Organization name")


class OrderResponse(BaseModel):
    """Schema for order response."""

    model_config = ConfigDict(
        from_attributes=True,
        strict=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "supplier_id": 1,
                "consumer_id": 1,
                "sales_rep_id": 3,
                "status": "pending",
                "total_kzt": "75000.00",
                "created_at": "2024-01-15T10:30:00Z",
                "items": [
                    {
                        "id": 1,
                        "order_id": 1,
                        "product_id": 1,
                        "qty": 5,
                        "unit_price_kzt": "15000.00",
                    }
                ],
            }
        },
    )

    id: int = Field(..., description="Order ID")
    supplier_id: int = Field(..., description="Supplier ID")
    consumer_id: int = Field(..., description="Consumer ID")
    sales_rep_id: int = Field(..., description="Sales representative user ID")
    status: OrderStatus = Field(..., description="Order status")
    total_kzt: Decimal = Field(..., description="Total amount in KZT")
    created_at: datetime = Field(..., description="Creation timestamp")
    items: list[OrderItemResponse] = Field(
        default_factory=list, description="Order items"
    )
    supplier: SupplierInfo | None = Field(None, description="Supplier information")
    consumer: ConsumerInfo | None = Field(None, description="Consumer information")
    sales_rep: UserResponse | None = Field(None, description="Sales representative information")
