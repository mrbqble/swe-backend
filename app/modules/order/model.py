from __future__ import annotations

import enum
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.chat.model import ChatSession
    from app.modules.complaint.model import Complaint
    from app.modules.consumer.model import Consumer
    from app.modules.product.model import Product
    from app.modules.supplier.model import Supplier


class OrderItem(Base):
    """OrderItem model."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_kzt: Mapped[Decimal] = mapped_column(
        Numeric[Decimal](10, 2), nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Product] = relationship("Product", back_populates="order_items")


class OrderStatus(enum.Enum):
    """Order status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Order(Base):
    """Order model."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumer_id: Mapped[int] = mapped_column(
        ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_rep_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True
    )
    total_kzt: Mapped[Decimal] = mapped_column(Numeric[Decimal](10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    supplier: Mapped[Supplier] = relationship("Supplier", back_populates="orders")
    consumer: Mapped[Consumer] = relationship("Consumer", back_populates="orders")
    sales_rep: Mapped["User"] = relationship(
        "User", foreign_keys=[sales_rep_id], back_populates="orders_as_sales_rep"
    )
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    complaints: Mapped[list[Complaint]] = relationship(
        "Complaint", back_populates="order"
    )
