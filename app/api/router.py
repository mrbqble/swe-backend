"""Router registration."""

from fastapi import FastAPI

from app.core.config import settings
from app.modules.auth.router import AuthRouter
from app.modules.user.router import UserRouter


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    app.include_router(AuthRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(UserRouter, prefix=settings.API_V1_PREFIX)
