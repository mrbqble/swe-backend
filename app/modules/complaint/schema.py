"""Complaint schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.complaint.model import ComplaintStatus
from app.modules.consumer.schema import ConsumerResponse
from app.modules.order.schema import OrderResponse


class ComplaintCreate(BaseModel):
    """Complaint creation request schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "order_id": 1,
                "sales_rep_id": 3,
                "manager_id": 2,
                "description": "Product arrived damaged. Need replacement or refund.",
            }
        },
    )

    order_id: int = Field(..., description="Order ID")
    sales_rep_id: int | None = Field(
        None, description="Sales representative user ID (auto-assigned if not provided)"
    )
    manager_id: int | None = Field(
        None, description="Manager user ID (not used, kept for backward compatibility)"
    )
    description: str = Field(
        ..., min_length=1, max_length=10000, description="Complaint description"
    )


class ComplaintStatusUpdate(BaseModel):
    """Complaint status update request schema."""

    model_config = ConfigDict(
        # Do not use strict=True here so that string values like "resolved"
        # from JSON are coerced into the ComplaintStatus enum by Pydantic.
        strict=False,
        json_schema_extra={
            "example": {
                "status": "resolved",
                "resolution": "Replacement product shipped. Tracking number: TRACK123456",
            }
        },
    )

    status: ComplaintStatus = Field(..., description="New complaint status")
    resolution: str | None = Field(
        None, max_length=10000, description="Resolution text (required when resolving)"
    )


class ComplaintFeedbackUpdate(BaseModel):
    """Consumer feedback update request schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "satisfied": True,
            }
        },
    )

    satisfied: bool = Field(
        ..., description="Whether the consumer is satisfied with the resolution"
    )


class ComplaintResponse(BaseModel):
    """Complaint response schema."""

    model_config = ConfigDict(
        from_attributes=True,
        strict=False,  # Allow None values for manager_id
        json_schema_extra={
            "example": {
                "id": 1,
                "order_id": 1,
                "consumer_id": 1,
                "sales_rep_id": 3,
                "manager_id": 2,
                "status": "open",
                "description": "Product arrived damaged. Need replacement or refund.",
                "resolution": None,
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )

    id: int
    order_id: int
    consumer_id: int
    sales_rep_id: int
    manager_id: int | None
    status: ComplaintStatus
    description: str
    resolution: str | None
    consumer_feedback: bool | None = Field(
        None,
        description="Consumer feedback: true=satisfied, false=not satisfied, null=no feedback",
    )
    created_at: datetime
    consumer: ConsumerResponse | None = Field(
        None, description="Consumer information")
    order: OrderResponse | None = Field(None, description="Order information")
