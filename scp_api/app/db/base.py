from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""

    pass


# Import models to ensure Alembic sees them.
from app.models import (  # noqa: E402,F401
    ChatMessage,
    ChatSession,
    Complaint,
    Consumer,
    Link,
    Notification,
    Order,
    OrderItem,
    Product,
    Supplier,
    User,
)
