from __future__ import annotations

from enum import Enum


class LinkStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DENIED = "denied"
    BLOCKED = "blocked"


class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ComplaintStatus(str, Enum):
    OPEN = "open"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class NotificationType(str, Enum):
    SYSTEM = "system"
    ORDER = "order"
    CHAT = "chat"
    COMPLAINT = "complaint"
