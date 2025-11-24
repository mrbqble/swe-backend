from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.order.model import OrderItem
    from app.modules.supplier.model import Supplier


class Product(Base):
    """Product model."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_kzt: Mapped[Decimal] = mapped_column(Numeric[Decimal](10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KZT", nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    stock_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True, default="pcs")
    min_order_qty: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    discount_percent: Mapped[Decimal | None] = mapped_column(
        Numeric[Decimal](5, 2), nullable=True, default=None
    )
    delivery_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    pickup_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    lead_time_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    supplier: Mapped[Supplier] = relationship("Supplier", back_populates="products")
    order_items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="product"
    )
