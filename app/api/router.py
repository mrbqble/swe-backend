"""Router registration."""

from fastapi import FastAPI

from app.core.config import settings
from app.modules.admin.audit_router import AdminAuditRouter
from app.modules.admin.auth_router import AdminAuthRouter
from app.modules.admin.faq_router import AdminFaqRouter, PublicFaqRouter
from app.modules.admin.inventory_router import AdminInventoryRouter
from app.modules.admin.notification_router import AdminNotificationRouter
from app.modules.admin.order_router import AdminOrderRouter
from app.modules.admin.partner_router import AdminPartnerRouter
from app.modules.auth.router import AuthRouter
from app.modules.cart.router import CartRouter
from app.modules.ip_too.router import IpTooRouter
from app.modules.notification.router import NotificationRouter
from app.modules.order.router import OrderRouter
from app.modules.payment.router import PaymentRouter
from app.modules.product.router import ProductRouter
from app.modules.support.router import AdminSuggestionRouter, SupportRouter
from app.modules.user.router import UserRouter

_ADMIN = "/admin"


def register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    # Partner-facing
    app.include_router(AuthRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(UserRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(IpTooRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(ProductRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(CartRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(OrderRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(PaymentRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(NotificationRouter, prefix=settings.API_V1_PREFIX)
    app.include_router(SupportRouter, prefix=settings.API_V1_PREFIX)

    # Public (no auth)
    app.include_router(PublicFaqRouter, prefix=settings.API_V1_PREFIX)

    # Admin panel
    app.include_router(AdminAuthRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminPartnerRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminOrderRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminInventoryRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminFaqRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminNotificationRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminAuditRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
    app.include_router(AdminSuggestionRouter, prefix=settings.API_V1_PREFIX + _ADMIN)
