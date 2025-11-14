from datetime import datetime

from app.models.enums import LinkStatus
from app.schemas.base import ORMModel


class LinkCreate(ORMModel):
    supplier_id: int
    consumer_id: int


class LinkRead(ORMModel):
    id: int
    supplier_id: int
    consumer_id: int
    status: LinkStatus
    created_at: datetime
