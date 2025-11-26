"""Application middleware."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

logger = logging.getLogger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging with correlation IDs."""

    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: Callable[[StarletteRequest], Awaitable[Response]],
    ) -> Response:
        """Log request and response with structured data and correlation ID."""
        start_time = time.time()

        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Store correlation ID in request state for use in handlers
        request.state.correlation_id = correlation_id

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        logger.info(
            f"Request started: {method} {path}",
            extra={
                "correlation_id": correlation_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "query_params": str(request.query_params)
                if request.query_params
                else None,
            },
        )

        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Request completed: {method} {path} - {response.status_code} ({round(latency_ms, 2)}ms)",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 2),
                    "client_ip": client_ip,
                },
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path} - {type(e).__name__} ({round(latency_ms, 2)}ms)",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "latency_ms": round(latency_ms, 2),
                    "client_ip": client_ip,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,  # Include full stack trace
            )
            raise
