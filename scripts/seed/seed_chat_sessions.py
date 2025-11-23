"""Seed chat_sessions table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatSession
from app.modules.consumer.model import Consumer
from app.modules.order.model import Order
from app.modules.user.model import User


async def seed_chat_sessions(
    session: AsyncSession,
    consumers: dict[str, Consumer],
    users: dict[str, User],
    orders: list[Order],
) -> list[ChatSession]:
    """
    Seed chat_sessions table.

    Args:
        session: Database session
        consumers: Dictionary of consumers keyed by organization name
        users: Dictionary of users keyed by email
        orders: List of Order objects

    Returns:
        List of ChatSession objects.
    """
    # Get existing chat sessions
    result = await session.execute(select(ChatSession))
    existing_sessions = result.scalars().all()

    # Validate required data exists
    required_consumer_names = [
        "Retail Chain ABC",
        "Wholesale Distributor XYZ",
        "Supermarket Network 123",
        "Department Store Group",
    ]
    for name in required_consumer_names:
        if name not in consumers:
            raise ValueError(
                f"Required consumer {name} not found. Please run seed_consumers first."
            )

    required_user_emails = [
        "sales1@example.com",
        "sales2@example.com",
        "sales3@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )

    if len(orders) < 7:
        raise ValueError(
            f"Need at least 7 orders, but only {len(orders)} found. Please run seed_orders first."
        )

    # If we already have 7 or more sessions, assume seeding is done
    if len(existing_sessions) >= 7:
        print(
            f"⚠️  Chat sessions already exist ({len(existing_sessions)} sessions), skipping seed_chat_sessions"
        )
        return existing_sessions[:7]  # Return first 7 for compatibility

    sessions_data = [
        # Chat sessions with orders
        {
            "consumer": consumers["Retail Chain ABC"],
            "sales_rep": users["sales1@example.com"],
            "order": orders[0],  # Pending order
        },
        {
            "consumer": consumers["Retail Chain ABC"],
            "sales_rep": users["sales1@example.com"],
            "order": orders[1],  # Accepted order
        },
        {
            "consumer": consumers["Wholesale Distributor XYZ"],
            "sales_rep": users["sales1@example.com"],
            "order": orders[2],  # In Progress order
        },
        {
            "consumer": consumers["Retail Chain ABC"],
            "sales_rep": users["sales2@example.com"],
            "order": orders[3],  # Completed order
        },
        {
            "consumer": consumers["Supermarket Network 123"],
            "sales_rep": users["sales2@example.com"],
            "order": orders[4],  # Accepted order
        },
        # Chat sessions without orders (general inquiries)
        {
            "consumer": consumers["Wholesale Distributor XYZ"],
            "sales_rep": users["sales3@example.com"],
            "order": None,
        },
        {
            "consumer": consumers["Department Store Group"],
            "sales_rep": users["sales1@example.com"],
            "order": None,
        },
    ]

    # If we have existing sessions, use them (up to 7)
    sessions = (
        existing_sessions[:7]
        if len(existing_sessions) >= 7
        else existing_sessions.copy()
    )
    created_count = 0

    # Create missing chat sessions
    for session_data in sessions_data:
        if len(sessions) >= 7:
            break  # We have enough sessions

        consumer = session_data["consumer"]
        sales_rep = session_data["sales_rep"]
        order = session_data["order"]
        assert isinstance(consumer, Consumer), (
            f"Expected Consumer, got {type(consumer)}"
        )
        assert isinstance(sales_rep, User), f"Expected User, got {type(sales_rep)}"
        order_id: int | None = None
        if order is not None:
            assert isinstance(order, Order), f"Expected Order, got {type(order)}"
            order_id = order.id
        chat_session = ChatSession(
            consumer_id=consumer.id,
            sales_rep_id=sales_rep.id,
            order_id=order_id,
            created_at=datetime.now(UTC),
        )
        session.add(chat_session)
        sessions.append(chat_session)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new chat sessions (total: {len(sessions)} sessions)"
        )
    else:
        print(f"✅ All required chat sessions already exist ({len(sessions)} sessions)")

    return sessions[:7]  # Return exactly 7 sessions for compatibility


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_consumers import seed_consumers
    from scripts.seed.seed_orders import seed_orders
    from scripts.seed.seed_suppliers import seed_suppliers
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            suppliers = await seed_suppliers(session, users)
            consumers = await seed_consumers(session, users)
            orders = await seed_orders(session, suppliers, consumers)
            await seed_chat_sessions(session, consumers, users, orders)

    asyncio.run(main())
