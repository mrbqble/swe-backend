"""Push notification utility. Dev: logs. Prod: TODO Expo Push API."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_push(user_id: int, title: str, body: str, db: AsyncSession) -> None:
    from app.modules.user.model import User

    push_token = (
        await db.execute(select(User.push_token).where(User.id == user_id))
    ).scalar_one_or_none()

    if not push_token:
        return

    if settings.ENV == "dev":
        logger.info(
            "DEV PUSH to user %d (token: %s): %s — %s", user_id, push_token, title, body
        )
        return

    # Production: Expo Push API not yet wired up.
    # Logged as a warning so push failures don't abort the primary request flow.
    logger.warning(
        "PROD PUSH SKIPPED — Expo Push API not configured. user=%d title=%r", user_id, title
    )
