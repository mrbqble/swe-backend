from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.chat.model import ChatSession
    from app.modules.complaint.model import Complaint
    from app.modules.link.model import Link
    from app.modules.order.model import Order
    from app.modules.user.model import User


class Consumer(Base):
    """Consumer model."""

    __tablename__ = "consumers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_image: Mapped[str | None] = mapped_column(Text, nullable=True)  # Base64 encoded image data
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="consumer")
    links: Mapped[list[Link]] = relationship("Link", back_populates="consumer")
    orders: Mapped[list[Order]] = relationship("Order", back_populates="consumer")
    chat_sessions: Mapped[list[ChatSession]] = relationship(
        "ChatSession", back_populates="consumer"
    )
    complaints: Mapped[list[Complaint]] = relationship(
        "Complaint", back_populates="consumer"
    )
