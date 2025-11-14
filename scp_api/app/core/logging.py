from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from fastapi import Request
from starlette.responses import Response

from app.core.config import settings


def configure_logging() -> None:
    if settings.environment == "prod":
        logging.basicConfig(level=logging.INFO, handlers=[StructuredJsonHandler()])
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )


class StructuredJsonHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        payload = {
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        print(json.dumps(payload))


async def logging_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start) * 1000

    if settings.environment == "prod":
        log_payload = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round(process_time, 2),
        }
        logging.getLogger("uvicorn.access").info(json.dumps(log_payload))
    else:
        logging.getLogger("uvicorn.access").info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )

    return response
