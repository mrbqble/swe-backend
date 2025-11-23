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
    if len(chat_sessions) < 7:
        raise ValueError(
            f"Need at least 7 chat sessions, but only {len(chat_sessions)} found. Please run seed_chat_sessions first."
        )

    required_user_emails = [
        "consumer1@example.com",
        "consumer2@example.com",
        "consumer3@example.com",
        "consumer4@example.com",
        "sales1@example.com",
        "sales2@example.com",
        "sales3@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )

    # If we already have many messages, assume seeding is done
    if len(existing_messages) >= 17:  # We create 17 messages
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
    ]

    # If we have existing messages, use them (up to 17)
    messages = (
        existing_messages[:17]
        if len(existing_messages) >= 17
        else existing_messages.copy()
    )
    created_count = 0

    # Create missing chat messages
    for message_data in messages_data:
        if len(messages) >= 17:
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

    return messages[:17]  # Return exactly 17 messages for compatibility


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
