from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.consumer.model import Consumer
    from app.modules.order.model import Order
    from app.modules.user.model import User


class ComplaintStatus(enum.Enum):
    """Complaint status enum."""

    OPEN = "open"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class Complaint(Base):
    """Complaint model."""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_rep_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus), default=ComplaintStatus.OPEN, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    consumer_feedback: Mapped[bool | None] = mapped_column(
        nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="complaints")
    consumer: Mapped[Consumer] = relationship(
        "Consumer", back_populates="complaints")
    sales_rep: Mapped[User] = relationship(
        "User", foreign_keys=[sales_rep_id], back_populates="complaints_as_sales_rep"
    )
    manager: Mapped[User] = relationship(
        "User", foreign_keys=[manager_id], back_populates="complaints_as_manager"
    )
