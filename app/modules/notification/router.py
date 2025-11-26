"""Notification management routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.notification.model import Notification
from app.modules.notification.schema import NotificationResponse
from app.modules.user.model import User
from app.utils.pagination import create_pagination_response

NotificationRouter = APIRouter(prefix="/notifications", tags=["notifications"])


@NotificationRouter.get(
    "", response_model=dict
)  # Will be PaginationResponse[NotificationResponse]
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    is_read: bool | None = Query(None, description="Filter by read status"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get notifications for the current user."""
    query = select(Notification).where(
        Notification.recipient_id == current_user.id)

    # Apply read status filter
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    # Get total count
    count_query = select(func.count(Notification.id)).where(
        Notification.recipient_id == current_user.id
    )
    if is_read is not None:
        count_query = count_query.where(Notification.is_read == is_read)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    # Create response
    notification_responses = [
        NotificationResponse.model_validate(notification)
        for notification in notifications
    ]
    return create_pagination_response(
        notification_responses, page, size, total
    ).model_dump()


@NotificationRouter.patch(
    "/{notification_id}/read", response_model=NotificationResponse
)
async def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read (only by the recipient)."""
    # Get notification
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise ApplicationError("Notification not found",
                               )

    # Check if user is the recipient
    if notification.recipient_id != current_user.id:
        raise ApplicationError("You do not have permission to modify this notification",
                               )

    # Mark as read
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)

    return NotificationResponse.model_validate(notification)
