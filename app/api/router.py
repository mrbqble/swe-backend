"""Router registration."""

from fastapi import FastAPI

from app.api.catalog import CatalogueRouter
from app.core.config import settings
from app.modules.auth.router import AuthRouter
from app.modules.chat.router import ChatRouter
from app.modules.complaint.router import ComplaintRouter
from app.modules.link.router import LinkRouter
from app.modules.notification.router import NotificationRouter
from app.modules.order.router import OrderRouter
from app.modules.product.router import ProductRouter
from app.modules.supplier.router import SupplierRouter
from app.modules.user.router import UserRouter


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    app.include_router(CatalogueRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(AuthRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(ChatRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(ComplaintRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(LinkRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(NotificationRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(OrderRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(ProductRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(SupplierRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(UserRouter, prefix=settings.API_V1_PREFIX)
