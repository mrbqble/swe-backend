"""Database session management with slow query logging."""

import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection, ExecutionContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create engine with slow query logging
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable default SQLAlchemy echo (we'll log manually)
)


# Slow query logging for async engine
# Note: We listen to the sync_engine which is the underlying synchronous engine
@event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
def receive_before_cursor_execute(
    conn: Connection,
    _cursor: Any,  # DBAPI cursor type varies by database driver
    statement: str,
    parameters: Any,  # Can be tuple, dict, or list depending on database
    _context: ExecutionContext | None,
    _executemany: bool,
) -> tuple[str, Any]:
    """Log slow queries before execution."""
    conn.info.setdefault("query_start_time", []).append(time.time())
    return statement, parameters


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def receive_after_cursor_execute(
    conn: Connection,
    _cursor: Any,  # DBAPI cursor type varies by database driver
    statement: str,
    _parameters: Any,  # Can be tuple, dict, or list depending on database
    _context: ExecutionContext | None,
    _executemany: bool,
) -> None:
    """Log slow queries after execution."""
    if conn.info.get("query_start_time"):
        total = time.time() - conn.info["query_start_time"].pop(-1)
        if total * 1000 > settings.SLOW_QUERY_THRESHOLD_MS:
            logger.warning(
                "Slow query detected",
                extra={
                    "query": statement[:500]
                    if statement
                    else None,  # Truncate long queries
                    "duration_ms": round(total * 1000, 2),
                    "threshold_ms": settings.SLOW_QUERY_THRESHOLD_MS,
                },
            )


AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session
