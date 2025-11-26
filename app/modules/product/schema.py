"""Product schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    """Schema for creating a product."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "name": "Premium Widget",
                "description": "High-quality widget for industrial use",
                "price_kzt": "15000.00",
                "currency": "KZT",
                "sku": "WID-001",
                "stock_qty": 100,
                "is_active": True,
            }
        },
    )

    name: str = Field(..., max_length=255, description="Product name")
    description: str | None = Field(None, description="Product description")
    price_kzt: Decimal = Field(..., ge=0, decimal_places=2,
                               description="Price in KZT")

    @field_validator("price_kzt", mode="before")
    @classmethod
    def convert_price_to_decimal(cls, v: str | float | Decimal) -> Decimal:
        """Convert string or float to Decimal for strict mode compatibility."""
        if isinstance(v, Decimal):
            return v
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int | float)):
            return Decimal(v)
        raise ValueError(f"Cannot convert {type(v).__name__} to Decimal")

    currency: str = Field(
        default="KZT", max_length=3, description="Currency code (ISO 4217)"
    )
    sku: str = Field(
        ..., max_length=100, description="Stock keeping unit (unique per supplier)"
    )
    stock_qty: int = Field(default=0, ge=0, description="Stock quantity")
    unit: str | None = Field(
        default="pcs",
        max_length=50,
        description="Unit of measurement (e.g., pcs, kg, m)",
    )
    min_order_qty: int | None = Field(
        default=1, ge=1, description="Minimum order quantity"
    )
    discount_percent: Decimal | None = Field(
        None, ge=0, le=100, decimal_places=2, description="Discount percentage (0-100)"
    )

    @field_validator("discount_percent", mode="before")
    @classmethod
    def convert_discount_to_decimal(
        cls, v: str | float | Decimal | None
    ) -> Decimal | None:
        """Convert string or float to Decimal for strict mode compatibility."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        raise ValueError(f"Cannot convert {type(v).__name__} to Decimal")

    delivery_available: bool = Field(
        default=True, description="Whether delivery is available for this product"
    )
    pickup_available: bool = Field(
        default=True, description="Whether pickup is available for this product"
    )
    lead_time_days: int | None = Field(
        None, ge=0, description="Lead time in days for delivery/pickup"
    )
    is_active: bool = Field(
        default=True, description="Whether product is active")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "name": "Updated Premium Widget",
                "price_kzt": "16000.00",
                "stock_qty": 150,
            }
        },
    )

    name: str | None = Field(None, max_length=255, description="Product name")
    description: str | None = Field(None, description="Product description")
    price_kzt: Decimal | None = Field(
        None, ge=0, decimal_places=2, description="Price in KZT"
    )

    @field_validator("price_kzt", mode="before")
    @classmethod
    def convert_price_to_decimal(
        cls, v: str | float | Decimal | None
    ) -> Decimal | None:
        """Convert string or float to Decimal for strict mode compatibility."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        raise ValueError(f"Cannot convert {type(v).__name__} to Decimal")

    currency: str | None = Field(
        None, max_length=3, description="Currency code (ISO 4217)"
    )
    sku: str | None = Field(
        None, max_length=100, description="Stock keeping unit (unique per supplier)"
    )
    stock_qty: int | None = Field(None, ge=0, description="Stock quantity")
    unit: str | None = Field(
        None, max_length=50, description="Unit of measurement (e.g., pcs, kg, m)"
    )
    min_order_qty: int | None = Field(
        None, ge=1, description="Minimum order quantity")
    discount_percent: Decimal | None = Field(
        None, ge=0, le=100, decimal_places=2, description="Discount percentage (0-100)"
    )

    @field_validator("discount_percent", mode="before")
    @classmethod
    def convert_discount_to_decimal(
        cls, v: str | float | Decimal | None
    ) -> Decimal | None:
        """Convert string or float to Decimal for strict mode compatibility."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        raise ValueError(f"Cannot convert {type(v).__name__} to Decimal")

    delivery_available: bool | None = Field(
        None, description="Whether delivery is available for this product"
    )
    pickup_available: bool | None = Field(
        None, description="Whether pickup is available for this product"
    )
    lead_time_days: int | None = Field(
        None, ge=0, description="Lead time in days for delivery/pickup"
    )
    is_active: bool | None = Field(
        None, description="Whether product is active")


class ProductResponse(BaseModel):
    """Schema for product response."""

    model_config = ConfigDict(
        from_attributes=True,
        strict=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "supplier_id": 1,
                "name": "Premium Widget",
                "description": "High-quality widget for industrial use",
                "price_kzt": "15000.00",
                "currency": "KZT",
                "sku": "WID-001",
                "stock_qty": 100,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )

    id: int = Field(..., description="Product ID")
    supplier_id: int = Field(..., description="Supplier ID")
    name: str = Field(..., description="Product name")
    description: str | None = Field(None, description="Product description")
    price_kzt: Decimal = Field(..., description="Price in KZT")
    currency: str = Field(..., description="Currency code")
    sku: str = Field(..., description="Stock keeping unit")
    stock_qty: int = Field(..., description="Stock quantity")
    unit: str | None = Field(None, description="Unit of measurement")
    min_order_qty: int | None = Field(
        None, description="Minimum order quantity")
    discount_percent: Decimal | None = Field(
        None, description="Discount percentage")
    delivery_available: bool = Field(...,
                                     description="Whether delivery is available")
    pickup_available: bool = Field(...,
                                   description="Whether pickup is available")
    lead_time_days: int | None = Field(None, description="Lead time in days")
    is_active: bool = Field(..., description="Whether product is active")
    created_at: datetime = Field(..., description="Creation timestamp")
