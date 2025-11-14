from datetime import datetime
from typing import List, Optional

from app.models.enums import ComplaintStatus
from app.schemas.base import ORMModel


class ChatMessageRead(ORMModel):
    id: int
    sender_id: int
    text: str
    file_url: Optional[str]
    created_at: datetime


class ChatSessionRead(ORMModel):
    id: int
    consumer_id: int
    sales_rep_id: Optional[int]
    order_id: Optional[int]
    created_at: datetime
    messages: List[ChatMessageRead]


class ComplaintRead(ORMModel):
    id: int
    order_id: int
    consumer_id: int
    sales_rep_id: Optional[int]
    manager_id: Optional[int]
    status: ComplaintStatus
    description: str
    resolution: Optional[str]
    created_at: datetime


class ComplaintCreate(ORMModel):
    order_id: int
    consumer_id: int
    description: str
