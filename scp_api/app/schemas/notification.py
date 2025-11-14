from datetime import datetime

from app.models.enums import NotificationType
from app.schemas.base import ORMModel


class NotificationCreate(ORMModel):
    recipient_id: int
    type: NotificationType
    message: str


class NotificationRead(ORMModel):
    id: int
    recipient_id: int
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime
