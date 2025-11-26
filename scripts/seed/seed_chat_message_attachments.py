"""Seed chat_message_attachments table."""

import asyncio
import base64
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatMessage, ChatMessageAttachment


async def seed_chat_message_attachments(
    session: AsyncSession,
    chat_messages: list[ChatMessage],
) -> list[ChatMessageAttachment]:
    """
    Seed chat_message_attachments table.

    Args:
        session: Database session
        chat_messages: List of ChatMessage objects

    Returns:
        List of ChatMessageAttachment objects.
    """
    # Get existing attachments
    result = await session.execute(select(ChatMessageAttachment))
    existing_attachments = result.scalars().all()

    # Validate required data exists
    if len(chat_messages) < 1:
        raise ValueError(
            f"Need at least 1 chat message, but only {len(chat_messages)} found. Please run seed_chat_messages first."
        )

    # If we already have attachments, assume seeding is done
    if len(existing_attachments) >= 3:
        print(
            f"⚠️  Chat message attachments already exist ({len(existing_attachments)} attachments), skipping seed_chat_message_attachments"
        )
        return existing_attachments

    base_time = datetime.now(UTC) - timedelta(days=2)

    # Create a simple base64-encoded image (1x1 pixel PNG) for testing
    # This is a minimal valid PNG file
    minimal_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("utf-8")

    # Create a simple text file content (base64 encoded)
    text_file_content = base64.b64encode(
        b"This is a sample text file for testing purposes."
    ).decode("utf-8")

    # Create attachments for messages that have file_url or use first few messages
    attachments_data = []

    # Find messages with file_url first (prefer those)
    messages_with_file = [msg for msg in chat_messages if msg.file_url]

    if messages_with_file:
        # Attachment for a message with file_url (catalog PDF)
        attachments_data.append({
            "message": messages_with_file[0],
            "file_type": "file",
            "file_name": "product_catalog.pdf",
            "mime_type": "application/pdf",
            "file_data": text_file_content,  # Using text as placeholder
            "file_size": len(text_file_content),
            "created_at": base_time + timedelta(days=1, hours=16, minutes=10),
        })

    # Add image attachment to first message
    if len(chat_messages) > 0:
        attachments_data.append({
            "message": chat_messages[0],
            "file_type": "image",
            "file_name": "product_image.png",
            "mime_type": "image/png",
            "file_data": minimal_png,
            "file_size": len(minimal_png),
            "created_at": base_time + timedelta(hours=1, minutes=20),
        })

    # Add another file attachment if we have enough messages
    if len(chat_messages) > 2:
        attachments_data.append({
            "message": chat_messages[min(2, len(chat_messages) - 1)],
            "file_type": "file",
            "file_name": "tracking_info.txt",
            "mime_type": "text/plain",
            "file_data": text_file_content,
            "file_size": len(text_file_content),
            "created_at": base_time + timedelta(days=1, hours=10, minutes=10),
        })

    attachments = existing_attachments.copy()
    created_count = 0

    # Create missing attachments
    for attachment_data in attachments_data:
        if len(attachments) >= 3:
            break  # We have enough attachments

        message = attachment_data["message"]
        assert isinstance(message, ChatMessage), (
            f"Expected ChatMessage, got {type(message)}"
        )

        attachment = ChatMessageAttachment(
            message_id=message.id,
            file_type=attachment_data["file_type"],
            file_name=attachment_data["file_name"],
            mime_type=attachment_data["mime_type"],
            file_data=attachment_data["file_data"],
            file_size=attachment_data["file_size"],
            created_at=attachment_data["created_at"],
        )
        session.add(attachment)
        attachments.append(attachment)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new chat message attachments (total: {len(attachments)} attachments)"
        )
    else:
        print(
            f"✅ All required chat message attachments already exist ({len(attachments)} attachments)"
        )

    return attachments


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from app.modules.chat.model import ChatSession
    from scripts.seed.seed_chat_messages import seed_chat_messages
    from scripts.seed.seed_consumers import seed_consumers
    from scripts.seed.seed_links import seed_links
    from scripts.seed.seed_orders import seed_orders
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
            chat_messages = await seed_chat_messages(session, chat_sessions, users)
            await seed_chat_message_attachments(session, chat_messages)

    asyncio.run(main())

