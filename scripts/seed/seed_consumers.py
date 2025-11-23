"""Seed consumers table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consumer.model import Consumer
from app.modules.user.model import User


async def seed_consumers(
    session: AsyncSession, users: dict[str, User]
) -> dict[str, Consumer]:
    """
    Seed consumers table.

    Args:
        session: Database session
        users: Dictionary of users keyed by email

    Returns:
        Dictionary mapping organization name to Consumer object for use in other seed scripts.
    """
    # Get existing consumers
    result = await session.execute(select(Consumer))
    existing_consumers = {
        consumer.organization_name: consumer for consumer in result.scalars().all()
    }

    # Get consumer users - ensure they exist
    required_emails = [
        "consumer1@example.com",
        "consumer2@example.com",
        "consumer3@example.com",
        "consumer4@example.com",
    ]
    consumer_users: list[User] = []
    for email in required_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )
        user = users[email]
        assert isinstance(user, User), f"Expected User, got {type(user)}"
        consumer_users.append(user)

    consumers_data = [
        {
            "user": consumer_users[0],
            "organization_name": "Retail Chain ABC",
        },
        {
            "user": consumer_users[1],
            "organization_name": "Wholesale Distributor XYZ",
        },
        {
            "user": consumer_users[2],
            "organization_name": "Supermarket Network 123",
        },
        {
            "user": consumer_users[3],
            "organization_name": "Department Store Group",
        },
    ]

    consumers = []
    created_count = 0
    for consumer_data in consumers_data:
        org_name = consumer_data["organization_name"]
        if org_name in existing_consumers:
            # Consumer already exists, use it
            consumers.append(existing_consumers[org_name])
        else:
            # Create new consumer
            user_obj = consumer_data["user"]
            assert isinstance(user_obj, User), f"Expected User, got {type(user_obj)}"
            consumer = Consumer(
                user_id=user_obj.id,
                organization_name=org_name,
                created_at=datetime.now(UTC),
            )
            session.add(consumer)
            consumers.append(consumer)
            created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new consumers (total: {len(consumers)} consumers available)"
        )
    else:
        print(
            f"✅ All required consumers already exist ({len(consumers)} consumers available)"
        )

    return {consumer.organization_name: consumer for consumer in consumers}


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            await seed_consumers(session, users)

    asyncio.run(main())
