"""Admin: push broadcast."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.admin.model import AdminUser
from app.modules.notification.model import Notification
from app.modules.user.model import User

AdminNotificationRouter = APIRouter(tags=["admin"])
logger = logging.getLogger(__name__)


@AdminNotificationRouter.post("/notifications/broadcast")
async def broadcast(
    body: dict,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create push notification records for a target audience.

    audience: "all" | "city" | "date_range"
    city: required if audience=city
    date_from / date_to: required if audience=date_range (ISO date strings)
    """
    title: str = (body.get("title") or "").strip()
    msg_body: str = (body.get("body") or "").strip()
    audience: str = (body.get("audience") or "all").lower()

    if not title:
        raise ApplicationError("'title' is required.")
    if not msg_body:
        raise ApplicationError("'body' is required.")
    if len(title) > 60:
        raise ApplicationError("'title' must be 60 characters or fewer.")
    if len(msg_body) > 200:
        raise ApplicationError("'body' must be 200 characters or fewer.")
    if audience not in ("all", "city", "date_range"):
        raise ApplicationError("'audience' must be 'all', 'city', or 'date_range'.")

    base = select(User.id).where(User.is_active == True, User.is_frozen == False)  # noqa: E712

    if audience == "city":
        city = (body.get("city") or "").strip()
        if not city:
            raise ApplicationError("'city' is required when audience=city.")
        base = base.where(User.city.ilike(f"%{city}%"))

    elif audience == "date_range":
        date_from = body.get("date_from")
        date_to = body.get("date_to")
        if not date_from or not date_to:
            raise ApplicationError("'date_from' and 'date_to' are required when audience=date_range.")
        try:
            base = base.where(
                User.created_at >= datetime.fromisoformat(date_from),
                User.created_at <= datetime.fromisoformat(date_to + "T23:59:59"),
            )
        except ValueError:
            raise ApplicationError("Invalid date format. Use YYYY-MM-DD.")

    target_ids = (await db.execute(base)).scalars().all()

    if not target_ids:
        return {"queued": 0}

    now = datetime.now(UTC)
    payload = {"title": title, "body": msg_body}

    notifications = [
        Notification(
            recipient_id=uid,
            type="broadcast",
            message=msg_body,
            notification_metadata=payload,
            is_read=False,
            created_at=now,
        )
        for uid in target_ids
    ]
    db.add_all(notifications)
    await db.commit()

    count = len(target_ids)

    if settings.ENV == "dev":
        logger.info(f"BROADCAST to {count} users: {title}")
        # TODO: Expo push delivery in production
    else:
        pass  # TODO: send via Expo Push API

    return {"queued": count}
