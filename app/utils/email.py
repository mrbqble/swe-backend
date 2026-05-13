"""Email delivery mock for dev; stub for prod."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATES: dict[str, tuple[str, str]] = {
    "email_confirmation": (
        "Confirm your iCare email",
        "Your confirmation code: {code}",
    ),
    "password_changed": (
        "iCare: password changed",
        "Your password was changed on {date} from IP {ip}. If this wasn't you, contact support.",
    ),
    "email_changed": (
        "iCare: email address changed",
        "Your account email was changed to {new_email}. If this wasn't you, contact support.",
    ),
    "order_placed": (
        "iCare: order #{order_id} placed",
        "Your order for {blocks} blocks has been placed. Total: {amount} KZT.",
    ),
    "order_paid": (
        "iCare: order #{order_id} confirmed",
        "Payment received. Your order is being prepared.",
    ),
}


async def send_email(to: str, subject: str, body: str) -> None:
    if settings.ENV == "dev":
        logger.info("DEV EMAIL to %s | Subject: %s | Body: %s", to, subject, body)
        return
    # TODO: implement SendGrid/Mailgun delivery
    raise NotImplementedError("Email delivery not configured")


async def send_transactional(to: str, template: str, data: dict) -> None:
    subject_tpl, body_tpl = _TEMPLATES[template]
    subject = subject_tpl.format_map(data)
    body = body_tpl.format_map(data)
    await send_email(to, subject, body)
