from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.consumer.model import Consumer
    from app.modules.order.model import Order
    from app.modules.supplier.model import Supplier
    from app.modules.user.model import User


class ChatMessageAttachment(Base):
    """Chat message attachment model."""

    __tablename__ = "chat_message_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False)  # 'image', 'file', 'audio'
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_data: Mapped[str] = mapped_column(
        Text, nullable=False)  # Base64 encoded data
    file_size: Mapped[int | None] = mapped_column(
        Integer, nullable=True)  # Size in bytes
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    message: Mapped["ChatMessage"] = relationship(
        "ChatMessage", back_populates="attachments"
    )


class ChatMessage(Base):
    """ChatMessage model."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    session: Mapped[ChatSession] = relationship(
        "ChatSession", back_populates="messages"
    )
    sender: Mapped[User] = relationship("User", back_populates="chat_messages")
    attachments: Mapped[list[ChatMessageAttachment]] = relationship(
        "ChatMessageAttachment", back_populates="message", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    """ChatSession model."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("consumer_id", "supplier_id",
                         name="uq_chat_sessions_consumer_supplier"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_rep_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    consumer: Mapped[Consumer] = relationship(
        "Consumer", back_populates="chat_sessions"
    )
    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="chat_sessions"
    )
    sales_rep: Mapped[User] = relationship(
        "User", foreign_keys=[sales_rep_id], back_populates="chat_sessions"
    )
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )
