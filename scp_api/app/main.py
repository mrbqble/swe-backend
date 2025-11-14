from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    auth,
    chats,
    complaints,
    consumers,
    links,
    notifications,
    orders,
    products,
    suppliers,
    users,
)
from app.core.config import settings
from app.core.logging import configure_logging, logging_middleware


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version=settings.version,
        openapi_url=f"/api/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc" if settings.environment != "prod" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(logging_middleware)

    register_routes(app)
    register_health_route(app)

    return app


def register_routes(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(suppliers.router)
    app.include_router(consumers.router)
    app.include_router(products.router)
    app.include_router(links.router)
    app.include_router(orders.router)
    app.include_router(chats.router)
    app.include_router(complaints.router)
    app.include_router(notifications.router)


def register_health_route(app: FastAPI) -> None:
    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "env": settings.environment,
            "version": settings.version,
        }


app = create_app()
