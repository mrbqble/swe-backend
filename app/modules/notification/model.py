from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.user.model import User


class Notification(Base):
    """Notification model."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # ID of the related entity (order_id, complaint_id, session_id)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Type of entity: 'order', 'complaint', 'chat_session'
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notification_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        # Additional metadata (e.g., message_id for chat notifications)]
        "metadata", JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    recipient: Mapped[User] = relationship(
        "User", back_populates="notifications")
