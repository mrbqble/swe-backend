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

    # TODO: Expo Push API call
    # async with httpx.AsyncClient() as client:
    #     await client.post("https://exp.host/--/api/v2/push/send", json={
    #         "to": push_token, "title": title, "body": body
    #     })
