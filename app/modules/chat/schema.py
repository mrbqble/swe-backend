"""Chat schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.consumer.schema import ConsumerResponse
from app.modules.user.schema import UserResponse


class ChatSessionCreate(BaseModel):
    """Chat session creation request schema."""

    sales_rep_id: int | None = Field(
        None,
        description="Sales representative user ID (auto-assigned if not provided and order_id is given)",
    )
    order_id: int | None = Field(None, description="Optional order ID to link the chat")


class ChatMessageCreate(BaseModel):
    """Chat message creation request schema."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,  # Max message length (10KB) - security limit
        description="Message text",
    )
    file_url: str | None = Field(
        None,
        max_length=500,
        description="Optional file URL (must be a valid URL, no direct file uploads)",
    )


class ChatMessageResponse(BaseModel):
    """Chat message response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    sender_id: int
    text: str
    file_url: str | None
    created_at: datetime
    sender: UserResponse | None = Field(None, description="Sender user information")


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    consumer_id: int
    sales_rep_id: int
    order_id: int | None
    created_at: datetime
    consumer: ConsumerResponse | None = Field(None, description="Consumer information")
    sales_rep: UserResponse | None = Field(
        None, description="Sales representative information"
    )
    last_message: str | None = Field(
        None, description="Last message text in the session"
    )
