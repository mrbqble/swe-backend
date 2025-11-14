from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import LinkStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import Consumer, Supplier


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[LinkStatus] = mapped_column(Enum(LinkStatus, name="link_status"), default=LinkStatus.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    supplier: Mapped["Supplier"] = relationship(back_populates="links")
    consumer: Mapped["Consumer"] = relationship(back_populates="links")
