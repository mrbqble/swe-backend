"""Common Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Error response schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "detail": "Resource not found",
                "code": "NOT_FOUND",
                "meta": None,
            }
        },
    )

    detail: str = Field(..., description="Error detail message")
    code: str = Field(..., description="Error code")
    meta: dict[str, Any] | None = Field(
        default=None, description="Additional error metadata"
    )


class PaginationResponse[T](BaseModel):
    """Pagination response schema."""

    model_config = ConfigDict(
        strict=True,
        json_schema_extra={
            "example": {
                "items": [],
                "page": 1,
                "size": 20,
                "total": 0,
                "pages": 0,
            }
        },
    )

    items: list[T] = Field(..., description="List of items in current page")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Page size")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
