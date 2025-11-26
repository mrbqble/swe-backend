"""Application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import register_routers
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import StructuredLoggingMiddleware
from app.db.session import engine

setup_logging(log_level=settings.LOG_LEVEL, env=settings.ENV)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting up application...")
    yield
    logger.info("Shutting down application...")
    try:
        await engine.dispose()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.debug("Shutdown cancelled during cleanup")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Disable OpenAPI docs in production unless explicitly enabled
docs_url = (
    "/docs" if (settings.ENV !=
                "production" or settings.ENABLE_DOCS_IN_PROD) else None
)
redoc_url = (
    "/redoc" if (settings.ENV !=
                 "production" or settings.ENABLE_DOCS_IN_PROD) else None
)

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_tags=[
        {
            "name": "main",
            "description": "Main application endpoints (health check, root)",
        },
        {
            "name": "auth",
            "description": "Authentication endpoints (signup, login, token refresh)",
        },
        {
            "name": "products",
            "description": "Product management endpoints. **Role requirements vary by endpoint.**",
        },
        {
            "name": "orders",
            "description": "Order management endpoints. **Role requirements vary by endpoint.**",
        },
        {
            "name": "links",
            "description": "Consumer-supplier link management endpoints",
        },
        {
            "name": "chats",
            "description": "Chat and messaging endpoints",
        },
        {
            "name": "complaints",
            "description": "Complaint management endpoints",
        },
        {
            "name": "notifications",
            "description": "Notification endpoints",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
        {
            "name": "catalog",
            "description": "Public catalog endpoints",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(StructuredLoggingMiddleware)

register_exception_handlers(app)
register_routers(app)
