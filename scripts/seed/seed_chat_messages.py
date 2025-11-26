"""Seed chat_messages table."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatMessage, ChatSession
from app.modules.consumer.model import Consumer
from app.modules.user.model import User
from app.utils.helpers import create_notification


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
    if len(chat_sessions) < 1:
        raise ValueError(
            f"Need at least 1 chat session, but only {len(chat_sessions)} found. Chat sessions are created automatically when links are accepted."
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

    # Build a map of session_id -> (consumer_user, sales_rep_user)
    session_users: dict[int, tuple[User, User]] = {}
    for chat_session in chat_sessions:
        # Get consumer and its user
        consumer_result = await session.execute(
            select(Consumer).where(Consumer.id == chat_session.consumer_id)
        )
        consumer = consumer_result.scalar_one()

        # Get consumer user
        consumer_user_result = await session.execute(
            select(User).where(User.id == consumer.user_id)
        )
        consumer_user = consumer_user_result.scalar_one()

        # Get sales rep user
        sales_rep_user_result = await session.execute(
            select(User).where(User.id == chat_session.sales_rep_id)
        )
        sales_rep_user = sales_rep_user_result.scalar_one()

        session_users[chat_session.id] = (consumer_user, sales_rep_user)

    # If we already have many messages, assume seeding is done
    if len(existing_messages) >= len(chat_sessions) * 4:  # ~4 messages per session
        print(
            f"⚠️  Chat messages already exist ({len(existing_messages)} messages), skipping seed_chat_messages"
        )
        return existing_messages

    base_time = datetime.now(UTC) - timedelta(days=2)

    # Define message templates (alternating between consumer and sales rep)
    message_templates = [
        {"is_consumer": True, "text": "Hello, I have a question about my order.", "file_url": None},
        {"is_consumer": False, "text": "Hi! I'd be happy to help. What would you like to know?", "file_url": None},
        {"is_consumer": True, "text": "When can I expect delivery?", "file_url": None},
        {"is_consumer": False, "text": "The order is currently pending approval. Once approved, delivery will take 3-5 business days.", "file_url": None},
        {"is_consumer": False, "text": "Your order has been accepted! We're processing it now.", "file_url": None},
        {"is_consumer": True, "text": "Great! Thank you for the update.", "file_url": None},
        {"is_consumer": True, "text": "Can I add more items to my current order?", "file_url": None},
        {"is_consumer": False, "text": "I'm sorry, but your order is already in progress. You'll need to place a new order for additional items.", "file_url": None},
        {"is_consumer": False, "text": "Your order has been completed and shipped!", "file_url": None},
        {"is_consumer": True, "text": "Excellent! Can you provide the tracking number?", "file_url": None},
        {"is_consumer": False, "text": "Tracking number: TRK123456789. You can track it on our website.", "file_url": None},
        {"is_consumer": True, "text": "I need to modify the quantity of office chairs.", "file_url": None},
        {"is_consumer": False, "text": "I can help with that. How many chairs would you like?", "file_url": None},
        {"is_consumer": True, "text": "Hello, I'm interested in your product catalog.", "file_url": None},
        {"is_consumer": False, "text": "Hello! I'd be happy to send you our latest catalog. Let me prepare that for you.", "file_url": None},
        {"is_consumer": False, "text": "Here's our catalog:", "file_url": "https://example.com/catalog.pdf"},
        {"is_consumer": True, "text": "What are your bulk pricing options?", "file_url": None},
        {"is_consumer": False, "text": "We offer volume discounts for orders over 10 units. Would you like me to send you our pricing sheet?", "file_url": None},
        {"is_consumer": False, "text": "Your order has been accepted and is being processed.", "file_url": None},
        {"is_consumer": True, "text": "Thank you! When can we expect delivery?", "file_url": None},
        {"is_consumer": True, "text": "Can you provide an update on our order status?", "file_url": None},
        {"is_consumer": False, "text": "Your order is currently in progress. We'll notify you once it ships.", "file_url": None},
        {"is_consumer": False, "text": "Your order has been completed and is ready for pickup.", "file_url": None},
        {"is_consumer": True, "text": "Perfect! We'll arrange pickup tomorrow.", "file_url": None},
    ]

    # If we have existing messages, use them
    messages = existing_messages.copy()
    created_count = 0

    # Distribute messages across available sessions
    # Each session gets messages only from its consumer and sales rep
    template_index = 0
    notifications_created = 0
    for chat_session in chat_sessions:
        if chat_session.id not in session_users:
            continue  # Skip if we don't have user info for this session

        consumer_user, sales_rep_user = session_users[chat_session.id]

        # Get consumer for this session to check user_id
        consumer_result = await session.execute(
            select(Consumer).where(Consumer.id == chat_session.consumer_id)
        )
        consumer_in_session = consumer_result.scalar_one_or_none()

        # Create 3-5 messages per session (alternating between consumer and sales rep)
        messages_per_session = min(5, len(message_templates) - template_index)
        session_time = base_time + timedelta(hours=1)

        for i in range(messages_per_session):
            if template_index >= len(message_templates):
                break

            template = message_templates[template_index]
            template_index += 1

            # Choose sender based on template
            sender = consumer_user if template["is_consumer"] else sales_rep_user

            # Increment time for each message
            session_time += timedelta(minutes=5 + i * 2)

            message = ChatMessage(
                session_id=chat_session.id,
                sender_id=sender.id,
                text=template["text"],
                file_url=template["file_url"],
                created_at=session_time,
            )
            session.add(message)
            messages.append(message)
            created_count += 1

            # Create notification for consumer when message is sent from supplier side (matches backend router logic)
            if not template["is_consumer"] and consumer_in_session and consumer_in_session.user_id:
                sender_name = f"{sender.first_name} {sender.last_name}".strip() or sender.email
                message_text = template["text"] or ""
                notification_message = f"{sender_name} sent you a message: {message_text[:100]}{'...' if len(message_text) > 100 else ''}"
                # Flush to get message.id before creating notification
                await session.flush()
                await create_notification(
                    consumer_in_session.user_id,
                    "chat_message",
                    notification_message,
                    session,
                    entity_id=chat_session.id,
                    entity_type="chat_session",
                    metadata={"message_id": message.id}  # Store message_id in metadata for scrolling
                )
                notifications_created += 1

    if created_count > 0:
        await session.flush()
        await session.commit()

        # Log what was created
        print(
            f"✅ Created {created_count} new chat messages (total: {len(messages)} messages)"
        )
        print(f"   🔔 Created {notifications_created} notifications for consumers (from supplier-side messages)")

        # Count total chat messages and notifications in database
        from sqlalchemy import func
        from app.modules.notification.model import Notification
        chat_msg_count = await session.execute(select(func.count(ChatMessage.id)))
        notif_count = await session.execute(select(func.count(Notification.id)))
        print(f"   📊 Database totals: {chat_msg_count.scalar()} chat messages, {notif_count.scalar()} notifications")
    else:
        print(f"✅ All required chat messages already exist ({len(messages)} messages)")

    return messages


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.modules.chat.model import ChatSession
    from scripts.seed.seed_consumers import seed_consumers
    from scripts.seed.seed_links import seed_links
    from scripts.seed.seed_suppliers import seed_suppliers
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            suppliers = await seed_suppliers(session, users)
            consumers = await seed_consumers(session, users)
            await seed_links(session, consumers, suppliers)
            # Get chat sessions created from accepted links
            result = await session.execute(select(ChatSession))
            chat_sessions = result.scalars().all()
            await seed_chat_messages(session, chat_sessions, users)

    asyncio.run(main())
