"""Notification schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: int
    recipient_id: int
    type: str
    message: str
    entity_id: int | None = None
    entity_type: str | None = None
    metadata: dict[str, Any] | None = Field(
        None, alias="notification_metadata")
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
