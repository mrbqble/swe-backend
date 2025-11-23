"""Seed notifications table."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.model import Notification
from app.modules.user.model import User


async def seed_notifications(
    session: AsyncSession, users: dict[str, User]
) -> list[Notification]:
    """
    Seed notifications table.

    Args:
        session: Database session
        users: Dictionary of users keyed by email

    Returns:
        List of Notification objects.
    """
    # Get existing notifications
    result = await session.execute(select(Notification))
    existing_notifications = result.scalars().all()

    # Validate required users exist
    required_user_emails = [
        "consumer1@example.com",
        "consumer2@example.com",
        "consumer3@example.com",
        "sales1@example.com",
        "sales2@example.com",
        "manager1@example.com",
        "manager2@example.com",
        "supplier1@example.com",
        "supplier2@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )

    # If we already have many notifications, assume seeding is done
    if len(existing_notifications) >= 17:  # We create 17 notifications
        print(
            f"⚠️  Notifications already exist ({len(existing_notifications)} notifications), skipping seed_notifications"
        )
        return existing_notifications

    base_time = datetime.now(UTC) - timedelta(days=1)

    notifications_data = [
        # Notifications for consumer1
        {
            "recipient": users["consumer1@example.com"],
            "type": "order_status",
            "message": "Your order #1 status has been updated to 'Accepted'",
            "is_read": False,
            "created_at": base_time + timedelta(hours=2),
        },
        {
            "recipient": users["consumer1@example.com"],
            "type": "order_status",
            "message": "Your order #3 has been completed and shipped",
            "is_read": True,
            "created_at": base_time + timedelta(days=1, hours=10),
        },
        {
            "recipient": users["consumer1@example.com"],
            "type": "complaint",
            "message": "Your complaint #3 has been resolved",
            "is_read": True,
            "created_at": base_time + timedelta(days=1, hours=15),
        },
        # Notifications for consumer2
        {
            "recipient": users["consumer2@example.com"],
            "type": "order_status",
            "message": "Your order #2 status has been updated to 'In Progress'",
            "is_read": False,
            "created_at": base_time + timedelta(hours=4),
        },
        {
            "recipient": users["consumer2@example.com"],
            "type": "order_status",
            "message": "Your order #5 has been completed",
            "is_read": False,
            "created_at": base_time + timedelta(days=1, hours=12),
        },
        {
            "recipient": users["consumer2@example.com"],
            "type": "order_status",
            "message": "Your order #6 has been rejected",
            "is_read": True,
            "created_at": base_time + timedelta(days=1, hours=14),
        },
        {
            "recipient": users["consumer2@example.com"],
            "type": "complaint",
            "message": "Your complaint #2 has been escalated",
            "is_read": False,
            "created_at": base_time + timedelta(days=1, hours=16),
        },
        # Notifications for consumer3
        {
            "recipient": users["consumer3@example.com"],
            "type": "order_status",
            "message": "Your order #4 status has been updated to 'Accepted'",
            "is_read": False,
            "created_at": base_time + timedelta(hours=6),
        },
        # Notifications for sales reps
        {
            "recipient": users["sales1@example.com"],
            "type": "new_order",
            "message": "New order received from Retail Chain ABC",
            "is_read": False,
            "created_at": base_time + timedelta(hours=1),
        },
        {
            "recipient": users["sales1@example.com"],
            "type": "complaint",
            "message": "New complaint received for order #1",
            "is_read": False,
            "created_at": base_time + timedelta(hours=3),
        },
        {
            "recipient": users["sales1@example.com"],
            "type": "complaint",
            "message": "Complaint #2 has been escalated to manager",
            "is_read": True,
            "created_at": base_time + timedelta(days=1, hours=8),
        },
        {
            "recipient": users["sales2@example.com"],
            "type": "new_order",
            "message": "New order received from Supermarket Network 123",
            "is_read": False,
            "created_at": base_time + timedelta(hours=5),
        },
        {
            "recipient": users["sales2@example.com"],
            "type": "complaint",
            "message": "Complaint #3 has been resolved",
            "is_read": True,
            "created_at": base_time + timedelta(days=1, hours=15),
        },
        # Notifications for managers
        {
            "recipient": users["manager1@example.com"],
            "type": "complaint",
            "message": "Complaint #2 has been escalated and requires your attention",
            "is_read": False,
            "created_at": base_time + timedelta(days=1, hours=8),
        },
        {
            "recipient": users["manager2@example.com"],
            "type": "complaint",
            "message": "New complaint #4 requires your review",
            "is_read": False,
            "created_at": base_time + timedelta(days=1, hours=18),
        },
        # Notifications for supplier owners
        {
            "recipient": users["supplier1@example.com"],
            "type": "link_request",
            "message": "New link request from Department Store Group",
            "is_read": False,
            "created_at": base_time + timedelta(hours=7),
        },
        {
            "recipient": users["supplier2@example.com"],
            "type": "link_request",
            "message": "Link request from Department Store Group has been blocked",
            "is_read": True,
            "created_at": base_time + timedelta(days=1, hours=9),
        },
    ]

    # If we have existing notifications, use them (up to 17)
    notifications = (
        existing_notifications[:17]
        if len(existing_notifications) >= 17
        else existing_notifications.copy()
    )
    created_count = 0

    # Create missing notifications
    for notification_data in notifications_data:
        if len(notifications) >= 17:
            break  # We have enough notifications

        recipient = notification_data["recipient"]
        assert isinstance(recipient, User), f"Expected User, got {type(recipient)}"
        notification = Notification(
            recipient_id=recipient.id,
            type=notification_data["type"],
            message=notification_data["message"],
            is_read=notification_data["is_read"],
            created_at=notification_data["created_at"],
        )
        session.add(notification)
        notifications.append(notification)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new notifications (total: {len(notifications)} notifications)"
        )
    else:
        print(
            f"✅ All required notifications already exist ({len(notifications)} notifications)"
        )

    return notifications[:17]  # Return exactly 17 notifications for compatibility


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            await seed_notifications(session, users)

    asyncio.run(main())
