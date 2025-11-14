from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.schemas.error import ErrorResponse


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version=settings.version,
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url=None if settings.environment == "prod" else "/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(logging_middleware)

    register_exception_handlers(app)
    register_routes(app)
    register_health_route(app)

    return app


def register_routes(app: FastAPI) -> None:
    prefix = "/api/v1"
    app.include_router(auth.router, prefix=f"{prefix}/auth")
    app.include_router(users.router, prefix=f"{prefix}/users")
    app.include_router(suppliers.router, prefix=f"{prefix}/suppliers")
    app.include_router(consumers.router, prefix=f"{prefix}/consumers")
    app.include_router(products.router, prefix=f"{prefix}/products")
    app.include_router(links.router, prefix=f"{prefix}/links")
    app.include_router(orders.router, prefix=f"{prefix}/orders")
    app.include_router(chats.router, prefix=f"{prefix}/chats")
    app.include_router(complaints.router, prefix=f"{prefix}/complaints")
    app.include_router(notifications.router, prefix=f"{prefix}/notifications")


def register_health_route(app: FastAPI) -> None:
    @app.get("/health", tags=["Health"], response_model=dict[str, str])
    async def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "env": settings.environment,
            "version": settings.version,
        }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(detail="Validation error", code="validation_error", meta={"errors": exc.errors()})
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        payload = ErrorResponse(detail=str(exc), code="internal_server_error")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())


app = create_app()
