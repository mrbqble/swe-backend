"""Seed chat_messages table."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatMessage, ChatSession
from app.modules.user.model import User


async def seed_chat_messages(
    session: AsyncSession,
    chat_sessions: list[ChatSession],
    users: dict[str, User],
) -> list[ChatMessage]:
    """
    Seed chat_messages table.

    Args:
        session: Database session
        chat_sessions: List of ChatSession objects
        users: Dictionary of users keyed by email

    Returns:
        List of ChatMessage objects.
    """
    # Get existing chat messages
    result = await session.execute(select(ChatMessage))
    existing_messages = result.scalars().all()

    # Validate required data exists
    if len(chat_sessions) < 10:
        raise ValueError(
            f"Need at least 10 chat sessions, but only {len(chat_sessions)} found. Please run seed_chat_sessions first."
        )

    required_user_emails = [
        "consumer1@example.com",
        "consumer2@example.com",
        "consumer3@example.com",
        "consumer4@example.com",
        "consumer5@example.com",
        "consumer6@example.com",
        "consumer7@example.com",
        "sales1@example.com",
        "sales2@example.com",
        "sales3@example.com",
        "sales4@example.com",
        "sales5@example.com",
        "sales6@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )

    # If we already have many messages, assume seeding is done
    if len(existing_messages) >= 24:  # We create 24 messages
        print(
            f"⚠️  Chat messages already exist ({len(existing_messages)} messages), skipping seed_chat_messages"
        )
        return existing_messages

    base_time = datetime.now(UTC) - timedelta(days=2)

    messages_data = [
        # Messages for session 0 (Retail Chain ABC - sales1 - pending order)
        {
            "session": chat_sessions[0],
            "sender": users["consumer1@example.com"],
            "text": "Hello, I have a question about the laptop order.",
            "file_url": None,
            "created_at": base_time + timedelta(hours=1),
        },
        {
            "session": chat_sessions[0],
            "sender": users["sales1@example.com"],
            "text": "Hi! I'd be happy to help. What would you like to know?",
            "file_url": None,
            "created_at": base_time + timedelta(hours=1, minutes=5),
        },
        {
            "session": chat_sessions[0],
            "sender": users["consumer1@example.com"],
            "text": "When can I expect delivery?",
            "file_url": None,
            "created_at": base_time + timedelta(hours=1, minutes=10),
        },
        {
            "session": chat_sessions[0],
            "sender": users["sales1@example.com"],
            "text": "The order is currently pending approval. Once approved, delivery will take 3-5 business days.",
            "file_url": None,
            "created_at": base_time + timedelta(hours=1, minutes=15),
        },
        # Messages for session 1 (Retail Chain ABC - sales1 - accepted order)
        {
            "session": chat_sessions[1],
            "sender": users["sales1@example.com"],
            "text": "Your order has been accepted! We're processing it now.",
            "file_url": None,
            "created_at": base_time + timedelta(hours=2),
        },
        {
            "session": chat_sessions[1],
            "sender": users["consumer1@example.com"],
            "text": "Great! Thank you for the update.",
            "file_url": None,
            "created_at": base_time + timedelta(hours=2, minutes=10),
        },
        # Messages for session 2 (Wholesale Distributor XYZ - sales1 - in progress order)
        {
            "session": chat_sessions[2],
            "sender": users["consumer2@example.com"],
            "text": "Can I add more items to my current order?",
            "file_url": None,
            "created_at": base_time + timedelta(hours=3),
        },
        {
            "session": chat_sessions[2],
            "sender": users["sales1@example.com"],
            "text": "I'm sorry, but your order is already in progress. You'll need to place a new order for additional items.",
            "file_url": None,
            "created_at": base_time + timedelta(hours=3, minutes=8),
        },
        # Messages for session 3 (Retail Chain ABC - sales2 - completed order)
        {
            "session": chat_sessions[3],
            "sender": users["sales2@example.com"],
            "text": "Your order has been completed and shipped!",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=10),
        },
        {
            "session": chat_sessions[3],
            "sender": users["consumer1@example.com"],
            "text": "Excellent! Can you provide the tracking number?",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=10, minutes=5),
        },
        {
            "session": chat_sessions[3],
            "sender": users["sales2@example.com"],
            "text": "Tracking number: TRK123456789. You can track it on our website.",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=10, minutes=7),
        },
        # Messages for session 4 (Supermarket Network 123 - sales2 - accepted order)
        {
            "session": chat_sessions[4],
            "sender": users["consumer3@example.com"],
            "text": "I need to modify the quantity of office chairs.",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=14),
        },
        {
            "session": chat_sessions[4],
            "sender": users["sales2@example.com"],
            "text": "I can help with that. How many chairs would you like?",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=14, minutes=3),
        },
        # Messages for session 5 (Wholesale Distributor XYZ - sales3 - no order)
        {
            "session": chat_sessions[5],
            "sender": users["consumer2@example.com"],
            "text": "Hello, I'm interested in your product catalog.",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=16),
        },
        {
            "session": chat_sessions[5],
            "sender": users["sales3@example.com"],
            "text": "Hello! I'd be happy to send you our latest catalog. Let me prepare that for you.",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=16, minutes=5),
        },
        {
            "session": chat_sessions[5],
            "sender": users["sales3@example.com"],
            "text": "Here's our catalog:",
            "file_url": "https://example.com/catalog.pdf",
            "created_at": base_time + timedelta(days=1, hours=16, minutes=10),
        },
        # Messages for session 6 (Department Store Group - sales1 - no order)
        {
            "session": chat_sessions[6],
            "sender": users["consumer4@example.com"],
            "text": "What are your bulk pricing options?",
            "file_url": None,
            "created_at": base_time + timedelta(days=2, hours=9),
        },
        {
            "session": chat_sessions[6],
            "sender": users["sales1@example.com"],
            "text": "We offer volume discounts for orders over 10 units. Would you like me to send you our pricing sheet?",
            "file_url": None,
            "created_at": base_time + timedelta(days=2, hours=9, minutes=8),
        },
        # Messages for session 7 (Corporate Buyers Alliance - sales4 - accepted order)
        {
            "session": chat_sessions[7],
            "sender": users["sales4@example.com"],
            "text": "Your order has been accepted and is being processed.",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=11),
        },
        {
            "session": chat_sessions[7],
            "sender": users["consumer5@example.com"],
            "text": "Thank you! When can we expect delivery?",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=11, minutes=5),
        },
        # Messages for session 8 (Retail Outlet Network - sales5 - in progress order)
        {
            "session": chat_sessions[8],
            "sender": users["consumer6@example.com"],
            "text": "Can you provide an update on our order status?",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=15),
        },
        {
            "session": chat_sessions[8],
            "sender": users["sales5@example.com"],
            "text": "Your order is currently in progress. We'll notify you once it ships.",
            "file_url": None,
            "created_at": base_time + timedelta(days=1, hours=15, minutes=10),
        },
        # Messages for session 9 (Bulk Purchase Consortium - sales6 - completed order)
        {
            "session": chat_sessions[9],
            "sender": users["sales6@example.com"],
            "text": "Your order has been completed and is ready for pickup.",
            "file_url": None,
            "created_at": base_time + timedelta(days=2, hours=10),
        },
        {
            "session": chat_sessions[9],
            "sender": users["consumer7@example.com"],
            "text": "Perfect! We'll arrange pickup tomorrow.",
            "file_url": None,
            "created_at": base_time + timedelta(days=2, hours=10, minutes=15),
        },
    ]

    # If we have existing messages, use them (up to 24)
    messages = (
        existing_messages[:24]
        if len(existing_messages) >= 24
        else existing_messages.copy()
    )
    created_count = 0

    # Create missing chat messages
    for message_data in messages_data:
        if len(messages) >= 24:
            break  # We have enough messages

        chat_session = message_data["session"]
        sender = message_data["sender"]
        assert isinstance(chat_session, ChatSession), (
            f"Expected ChatSession, got {type(chat_session)}"
        )
        assert isinstance(sender, User), f"Expected User, got {type(sender)}"
        message = ChatMessage(
            session_id=chat_session.id,
            sender_id=sender.id,
            text=message_data["text"],
            file_url=message_data["file_url"],
            created_at=message_data["created_at"],
        )
        session.add(message)
        messages.append(message)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new chat messages (total: {len(messages)} messages)"
        )
    else:
        print(f"✅ All required chat messages already exist ({len(messages)} messages)")

    return messages[:24]  # Return exactly 24 messages for compatibility


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_chat_sessions import seed_chat_sessions
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
            chat_sessions = await seed_chat_sessions(session, consumers, users, orders)
            await seed_chat_messages(session, chat_sessions, users)

    asyncio.run(main())
