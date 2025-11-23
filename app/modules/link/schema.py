"""Link schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.link.model import LinkStatus
from app.modules.supplier.schema import SupplierResponse
from app.modules.consumer.schema import ConsumerResponse


class LinkRequestCreate(BaseModel):
    """Schema for creating a link request."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "supplier_id": 1,
            }
        },
    )

    supplier_id: int = Field(..., description="ID of the supplier to request link with")


class LinkStatusUpdate(BaseModel):
    """Schema for updating link status."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "status": "accepted",
            }
        },
    )

    status: LinkStatus = Field(..., description="New status for the link")


class LinkResponse(BaseModel):
    """Schema for link response."""

    model_config = ConfigDict(
        from_attributes=True,
        strict=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "consumer_id": 1,
                "supplier_id": 1,
                "status": "accepted",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z",
            }
        },
    )

    id: int
    consumer_id: int
    supplier_id: int
    status: LinkStatus
    created_at: datetime
    updated_at: datetime
    # Include supplier details for convenience so frontend can show company info
    supplier: SupplierResponse | None = Field(None, description="Supplier info")
    consumer: ConsumerResponse | None = Field(None, description="Consumer info")
