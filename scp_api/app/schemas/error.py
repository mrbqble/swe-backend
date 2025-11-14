from typing import Any, Dict, Optional

from app.schemas.base import ORMModel


class ErrorResponse(ORMModel):
    detail: str
    code: str
    meta: Optional[Dict[str, Any]] = None
