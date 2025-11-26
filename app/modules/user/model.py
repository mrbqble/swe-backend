from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.chat.model import ChatMessage, ChatSession
    from app.modules.complaint.model import Complaint
    from app.modules.consumer.model import Consumer
    from app.modules.notification.model import Notification
    from app.modules.order.model import Order
    from app.modules.supplier.model import Supplier, SupplierStaff


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    supplier: Mapped[Supplier | None] = relationship(
        "Supplier", back_populates="user", uselist=False
    )
    consumer: Mapped[Consumer | None] = relationship(
        "Consumer", back_populates="user", uselist=False
    )
    supplier_staff: Mapped[list[SupplierStaff]] = relationship(
        "SupplierStaff", back_populates="user"
    )
    chat_sessions: Mapped[list[ChatSession]] = relationship(
        "ChatSession",
        foreign_keys="ChatSession.sales_rep_id",
        back_populates="sales_rep",
    )
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="sender"
    )
    complaints_as_sales_rep: Mapped[list[Complaint]] = relationship(
        "Complaint", foreign_keys="Complaint.sales_rep_id", back_populates="sales_rep"
    )
    complaints_as_manager: Mapped[list[Complaint]] = relationship(
        "Complaint", foreign_keys="Complaint.manager_id", back_populates="manager"
    )
    orders_as_sales_rep: Mapped[list[Order]] = relationship(
        "Order", foreign_keys="Order.sales_rep_id", back_populates="sales_rep"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="recipient"
    )
