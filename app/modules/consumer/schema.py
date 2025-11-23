"""Consumer schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsumerResponse(BaseModel):
    """Short consumer schema for embedding in responses."""

    model_config = ConfigDict(from_attributes=True, strict=True)

    id: int
    organization_name: str
    created_at: datetime
