"""Chat schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.consumer.schema import ConsumerResponse
from app.modules.user.schema import UserResponse


class ChatSessionCreate(BaseModel):
    """Chat session creation request schema.

    According to specs: One chat thread per Consumer-Supplier pair (once link is approved).
    The thread is reused for all conversations about any order.
    """

    sales_rep_id: int | None = Field(
        None,
        description="Sales representative user ID (auto-assigned if not provided and supplier_id is given)",
    )
    supplier_id: int | None = Field(
        None,
        description="Supplier ID (used to find/create the 1-1 chat thread for this Consumer-Supplier pair)",
    )


class ChatAttachmentCreate(BaseModel):
    """Chat attachment creation request schema."""

    file_type: str = Field(
        ...,
        description="Type of file: 'image', 'file', or 'audio'",
        pattern="^(image|file|audio)$",
    )
    file_name: str = Field(..., max_length=255,
                           description="Original file name")
    mime_type: str | None = Field(
        None, max_length=100, description="MIME type of the file")
    file_data: str = Field(..., description="Base64 encoded file data")
    file_size: int | None = Field(None, description="File size in bytes")


class ChatAttachmentResponse(BaseModel):
    """Chat attachment response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    file_type: str
    file_name: str
    mime_type: str | None
    file_data: str  # Base64 encoded data
    file_size: int | None
    created_at: datetime


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
    attachments: list[ChatAttachmentCreate] = Field(
        default_factory=list,
        description="List of attachments (images, files, audio) to include with the message",
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
    sender: UserResponse | None = Field(
        None, description="Sender user information")
    attachments: list[ChatAttachmentResponse] = Field(
        default_factory=list, description="List of attachments for this message"
    )


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    consumer_id: int
    sales_rep_id: int
    created_at: datetime
    consumer: ConsumerResponse | None = Field(
        None, description="Consumer information")
    sales_rep: UserResponse | None = Field(
        None, description="Sales representative information"
    )
    last_message: str | None = Field(
        None, description="Last message text in the session"
    )
