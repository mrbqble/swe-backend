from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ComplaintStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.order import Order
    from app.models.user import Consumer, User


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False)
    sales_rep_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    consumer: Mapped["Consumer"] = relationship(back_populates="chats")
    sales_rep: Mapped["User"] = relationship(foreign_keys=[sales_rep_id])
    order: Mapped["Order"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped[ChatSession] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    consumer_id: Mapped[int] = mapped_column(ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False)
    sales_rep_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus, name="complaint_status"), default=ComplaintStatus.OPEN, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="complaints")
    consumer: Mapped["Consumer"] = relationship(back_populates="complaints")
    sales_rep: Mapped["User"] = relationship(foreign_keys=[sales_rep_id])
    manager: Mapped["User"] = relationship(foreign_keys=[manager_id])
