from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import Role
from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.chat import ChatSession, Complaint
    from app.models.link import Link
    from app.models.notification import Notification
    from app.models.order import Order
    from app.models.product import Product


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    supplier: Mapped["Supplier"] = relationship(back_populates="owner", uselist=False)
    consumer: Mapped["Consumer"] = relationship(back_populates="user", uselist=False)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="recipient")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    owner: Mapped[User] = relationship(back_populates="supplier")
    products: Mapped[list["Product"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")
    links: Mapped[list["Link"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="supplier")


class Consumer(Base):
    __tablename__ = "consumers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="consumer")
    links: Mapped[list["Link"]] = relationship(back_populates="consumer", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="consumer")
    chats: Mapped[list["ChatSession"]] = relationship(back_populates="consumer")
    complaints: Mapped[list["Complaint"]] = relationship(back_populates="consumer")
