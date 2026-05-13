"""Exception handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorResponse
from app.utils.password_policy import PasswordPolicyError

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Custom application error that can be raised anywhere and handled globally.

    Usage:
        raise ApplicationError("Not found")
        raise ApplicationError("Too many requests", status_code=429)
    """

    def __init__(self, message: str, code: str | None = None, status_code: int = 400):
        self.message = message
        self.code = code or "APPLICATION_ERROR"
        self.status_code = status_code
        super().__init__(self.message)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with unified error response format."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        correlation_id = getattr(request.state, "correlation_id", None)

        errors = exc.errors()
        # Format errors for better readability
        formatted_errors: list[dict[str, Any]] = []
        for error in errors:
            error_dict = {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            # Include input value if available
            if "input" in error:
                error_dict["input"] = str(error["input"])
            formatted_errors.append(error_dict)

        # Log detailed error information
        logger.error(
            f"Request validation error on {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "query_params": str(request.url.query),
                "errors": formatted_errors,
                "full_error_details": errors,  # Include full error details
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail="Validation error: Invalid input data",
                code="VALIDATION_ERROR",
                meta={"errors": formatted_errors},
            ).model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic model validation errors."""
        correlation_id = getattr(request.state, "correlation_id", None)

        validation_errors = exc.errors()
        # Format errors for better readability
        formatted_errors: list[dict[str, Any]] = []
        for error in validation_errors:
            error_dict = {
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", "Unknown error"),
                "type": error.get("type", "unknown"),
            }
            # Include input value if available
            if "input" in error:
                error_dict["input"] = str(error["input"])[:500]  # Limit length
            formatted_errors.append(error_dict)

        # Log detailed error information
        logger.error(
            f"Pydantic model validation error on {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "query_params": str(request.url.query),
                "errors": formatted_errors,
                "full_error_details": validation_errors,  # Include full error details
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail="Validation error: Invalid model data",
                code="VALIDATION_ERROR",
                meta={"errors": exc.errors()},
            ).model_dump(),
        )

    @app.exception_handler(PasswordPolicyError)
    async def password_policy_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: PasswordPolicyError
    ) -> JSONResponse:
        """Handle password policy validation errors."""
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.warning(
            "Password policy error",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail=str(exc),
                code="PASSWORD_POLICY_ERROR",
            ).model_dump(),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """Handle database integrity errors (unique constraints, foreign keys, etc.)."""
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.warning(
            "Integrity error",
            exc_info=True,  # Include stack trace
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )

        # Try to extract meaningful error message
        error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)

        # Common integrity error patterns
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            detail = "Resource already exists (unique constraint violation)"
            code = "DUPLICATE_RESOURCE"
        elif "foreign key" in error_msg.lower():
            detail = "Referenced resource does not exist"
            code = "FOREIGN_KEY_VIOLATION"
        else:
            detail = "Database integrity constraint violation"
            code = "INTEGRITY_ERROR"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail=detail,
                code=code,
            ).model_dump(),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle SQLAlchemy database errors with structured logging."""
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.error(
            "Database error",
            exc_info=True,  # Include full stack trace
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail="Database error occurred",
                code="DATABASE_ERROR",
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions with standardized format."""
        correlation_id = getattr(request.state, "correlation_id", None)

        # Map common status codes to error codes
        status_code_map = {
            status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
            status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
            status.HTTP_403_FORBIDDEN: "FORBIDDEN",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_409_CONFLICT: "CONFLICT",
            status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
        }

        error_code = status_code_map.get(
            exc.status_code, f"HTTP_{exc.status_code}")

        # Log 4xx and 5xx errors with correlation ID
        if exc.status_code >= 400:
            log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
            logger.log(
                log_level,
                "HTTP exception",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": exc.status_code,
                    "error_code": error_code,
                },
            )

        # Preserve headers from HTTPException (e.g., WWW-Authenticate for 401)
        headers: dict[str, str] = {}
        if hasattr(exc, "headers") and exc.headers:
            headers.update(exc.headers)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=headers,
            content=ErrorResponse(
                detail=exc.detail,
                code=error_code,
            ).model_dump(),
        )

    @app.exception_handler(ApplicationError)
    async def application_error_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        """Handle custom application errors."""
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.warning(
            "Application error",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "error": exc.message,
                "error_code": exc.code,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.message,
                code=exc.code,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all other unhandled exceptions with structured logging."""
        # Get correlation ID from request state if available
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.error(
            "Unhandled exception",
            exc_info=True,  # Include full stack trace
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
                "error_type": type(exc).__name__,
                "client_ip": request.client.host if request.client else None,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail="Internal server error",
                code="INTERNAL_SERVER_ERROR",
            ).model_dump(),
        )
