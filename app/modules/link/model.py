from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.consumer.model import Consumer
    from app.modules.supplier.model import Supplier


class LinkStatus(enum.Enum):
    """Link status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DENIED = "denied"
    BLOCKED = "blocked"
    UNLINKED = "unlinked"


class Link(Base):
    """Link model."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus), default=LinkStatus.PENDING, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    consumer: Mapped[Consumer] = relationship(
        "Consumer", back_populates="links")
    supplier: Mapped[Supplier] = relationship(
        "Supplier", back_populates="links")

    __table_args__ = (
        UniqueConstraint("consumer_id", "supplier_id",
                         name="uq_consumer_supplier"),
    )
