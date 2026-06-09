from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.auth.model import Session
    from app.modules.cart.model import CartItem
    from app.modules.notification.model import Notification
    from app.modules.order.model import Order


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    patronymic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ref_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_root: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_tier: Mapped[str] = mapped_column(String(50), default="partner", nullable=False)
    is_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    team_volume: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    payout_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ref_code_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    welcomed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_cancel_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)
    consent_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    parent: Mapped[User | None] = relationship("User", remote_side="User.id", foreign_keys=[parent_id])
    children: Mapped[list[User]] = relationship("User", back_populates="parent", foreign_keys=[parent_id])
    sessions: Mapped[list[Session]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    cart_items: Mapped[list[CartItem]] = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list[Order]] = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="recipient", cascade="all, delete-orphan")
