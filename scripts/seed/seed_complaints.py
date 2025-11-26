"""Seed complaints table."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatMessage, ChatSession
from app.modules.complaint.model import Complaint, ComplaintStatus
from app.modules.consumer.model import Consumer
from app.modules.order.model import Order
from app.modules.supplier.model import Supplier
from app.modules.user.model import User
from app.utils.helpers import create_notification


async def seed_complaints(
    session: AsyncSession,
    orders: list[Order],
    consumers: dict[str, Consumer],
    users: dict[str, User],
) -> list[Complaint]:
    """
    Seed complaints table.

    Args:
        session: Database session
        orders: List of Order objects
        consumers: Dictionary of consumers keyed by organization name
        users: Dictionary of users keyed by email

    Returns:
        List of Complaint objects.
    """
    # Get existing complaints
    result = await session.execute(select(Complaint))
    existing_complaints = result.scalars().all()

    # Validate required data exists
    if len(orders) < 7:
        raise ValueError(
            f"Need at least 7 orders, but only {len(orders)} found. Please run seed_orders first."
        )

    required_consumer_names = [
        "Retail Chain ABC",
        "Wholesale Distributor XYZ",
        "Supermarket Network 123",
        "Corporate Buyers Alliance",
        "Retail Outlet Network",
        "Bulk Purchase Consortium",
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
        "sales4@example.com",
        "sales5@example.com",
        "sales6@example.com",
        "manager1@example.com",
        "manager2@example.com",
        "manager3@example.com",
        "manager4@example.com",
        "manager5@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )

    # If we already have 10 or more complaints, assume seeding is done
    if len(existing_complaints) >= 10:
        print(
            f"⚠️  Complaints already exist ({len(existing_complaints)} complaints), skipping seed_complaints"
        )
        # Return first 10 for compatibility
        return list(existing_complaints[:10])

    complaints_data = [
        {
            "order": orders[0],  # Pending order
            "consumer": consumers["Retail Chain ABC"],
            "sales_rep": users["sales1@example.com"],
            "manager": users["manager1@example.com"],
            "status": ComplaintStatus.OPEN,
            "description": "Order has been pending for too long without any updates.",
            "resolution": None,
        },
        {
            "order": orders[2],  # In Progress order
            "consumer": consumers["Wholesale Distributor XYZ"],
            "sales_rep": users["sales1@example.com"],
            "manager": users["manager1@example.com"],
            "status": ComplaintStatus.ESCALATED,
            "description": "Items received were damaged during shipping. Need immediate replacement.",
            "resolution": None,
        },
        {
            "order": orders[3],  # Completed order
            "consumer": consumers["Retail Chain ABC"],
            "sales_rep": users["sales2@example.com"],
            "manager": users["manager2@example.com"],
            "status": ComplaintStatus.RESOLVED,
            "description": "Received wrong color for the office chair. Requested black but received brown.",
            "resolution": "Replacement chair sent. Customer confirmed receipt and satisfaction.",
        },
        {
            "order": orders[6],  # Rejected order
            "consumer": consumers["Wholesale Distributor XYZ"],
            "sales_rep": users["sales3@example.com"],
            "manager": users["manager2@example.com"],
            "status": ComplaintStatus.OPEN,
            "description": "Order was rejected without proper explanation. Need clarification on rejection reason.",
            "resolution": None,
        },
        {
            "order": orders[1],  # Accepted order
            "consumer": consumers["Retail Chain ABC"],
            "sales_rep": users["sales1@example.com"],
            "manager": users["manager1@example.com"],
            "status": ComplaintStatus.OPEN,
            "description": "Delivery date was changed without notification. Need explanation.",
            "resolution": None,
        },
        {
            "order": orders[4],  # Accepted order
            "consumer": consumers["Supermarket Network 123"],
            "sales_rep": users["sales2@example.com"],
            "manager": users["manager2@example.com"],
            "status": ComplaintStatus.ESCALATED,
            "description": "Product quality does not match description. Requesting refund.",
            "resolution": None,
        },
        {
            "order": orders[5],  # Completed order
            "consumer": consumers["Wholesale Distributor XYZ"],
            "sales_rep": users["sales3@example.com"],
            "manager": users["manager1@example.com"],
            "status": ComplaintStatus.RESOLVED,
            "description": "Missing items in the shipment. Partial delivery received.",
            "resolution": "Missing items shipped separately. Customer confirmed receipt.",
        },
        {
            "order": orders[7],  # Accepted order
            "consumer": consumers["Corporate Buyers Alliance"],
            "sales_rep": users["sales4@example.com"],
            "manager": users["manager3@example.com"],
            "status": ComplaintStatus.OPEN,
            "description": "Invoice amount does not match order total. Need correction.",
            "resolution": None,
        },
        {
            "order": orders[8],  # In Progress order
            "consumer": consumers["Retail Outlet Network"],
            "sales_rep": users["sales5@example.com"],
            "manager": users["manager4@example.com"],
            "status": ComplaintStatus.ESCALATED,
            "description": "Delayed shipment affecting business operations. Urgent resolution needed.",
            "resolution": None,
        },
        {
            "order": orders[9],  # Completed order
            "consumer": consumers["Bulk Purchase Consortium"],
            "sales_rep": users["sales6@example.com"],
            "manager": users["manager5@example.com"],
            "status": ComplaintStatus.RESOLVED,
            "description": "Packaging was damaged but products were intact. Requesting better packaging for future orders.",
            "resolution": "Improved packaging standards implemented. Customer satisfied with resolution.",
        },
    ]

    # If we have existing complaints, use them (up to 10)
    complaints: list[Complaint] = (
        list(existing_complaints[:10])
        if len(existing_complaints) >= 10
        else list(existing_complaints)
    )
    created_count = 0
    chat_messages_created = 0  # Track chat messages created
    notifications_created = 0  # Track notifications created

    # Create missing complaints
    for complaint_data in complaints_data:
        if len(complaints) >= 10:
            break  # We have enough complaints

        order = complaint_data["order"]
        consumer = complaint_data["consumer"]
        sales_rep = complaint_data["sales_rep"]
        manager = complaint_data["manager"]
        assert isinstance(order, Order), f"Expected Order, got {type(order)}"
        assert isinstance(consumer, Consumer), (
            f"Expected Consumer, got {type(consumer)}"
        )
        assert isinstance(
            sales_rep, User), f"Expected User, got {type(sales_rep)}"
        assert isinstance(manager, User), f"Expected User, got {type(manager)}"

        # Validate that the order belongs to the consumer (aligns with backend logic: 1 consumer = 1 organization)
        if order.consumer_id != consumer.id:
            raise ValueError(
                f"Order {order.id} does not belong to consumer {consumer.id}. "
                f"Order consumer_id: {order.consumer_id}, Expected: {consumer.id}"
            )

        complaint = Complaint(
            order_id=order.id,
            consumer_id=consumer.id,
            sales_rep_id=sales_rep.id,
            manager_id=manager.id,
            status=complaint_data["status"],
            description=complaint_data["description"],
            resolution=complaint_data["resolution"],
            created_at=datetime.now(UTC),
        )
        session.add(complaint)
        await session.flush()  # Flush to get complaint.id

        # Find or create chat session for this consumer-sales_rep pair
        # According to SRS: complaints are posted in the same 1-1 chat thread
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.consumer_id == consumer.id,
                ChatSession.supplier_id == order.supplier_id,
            )
        )
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            # Create chat session if it doesn't exist (should exist from link acceptance, but create as fallback)
            chat_session = ChatSession(
                consumer_id=consumer.id,
                supplier_id=order.supplier_id,
                sales_rep_id=sales_rep.id,
                created_at=datetime.now(UTC),
            )
            session.add(chat_session)
            await session.flush()  # Flush to get session.id

        # Post structured complaint message in the chat thread
        # Format: Clear complaint notification with order reference (matches router logic)
        description: str = str(complaint_data.get("description", ""))
        desc_truncated = description[:300] if len(
            description) > 300 else description
        desc_suffix = "..." if len(description) > 300 else ""
        complaint_message_text = (
            f"🚨 Complaint #{complaint.id} opened for Order #{order.id}\n\n"
            f"Description: {desc_truncated}{desc_suffix}"
        )

        # Get consumer user for sender_id
        consumer_user_result = await session.execute(
            select(User).where(User.id == consumer.user_id)
        )
        consumer_user = consumer_user_result.scalar_one()

        complaint_message = ChatMessage(
            session_id=chat_session.id,
            sender_id=consumer_user.id,  # Consumer who created the complaint
            text=complaint_message_text,
            created_at=datetime.now(UTC),
        )
        session.add(complaint_message)
        chat_messages_created += 1

        # Create notification for consumer when complaint is created (matches backend router logic)
        if consumer.user_id:
            supplier_result = await session.execute(
                select(Supplier).where(Supplier.id == order.supplier_id)
            )
            supplier = supplier_result.scalar_one_or_none()
            supplier_name = supplier.company_name if supplier and supplier.company_name else "Supplier"
            message = f"Your complaint #{complaint.id} for Order #{order.id} has been submitted to {supplier_name}."
            await create_notification(
                consumer.user_id,
                "complaint_created",
                message,
                session,
                entity_id=complaint.id,
                entity_type="complaint",
                metadata={"order_id": complaint.order_id}  # Store order_id in metadata for navigation
            )
            notifications_created += 1

        # If complaint is escalated or resolved, post status change message
        # For seeding purposes, we create complaints with various statuses directly,
        # so we post status change messages to simulate the workflow
        if complaint_data["status"] in (ComplaintStatus.ESCALATED, ComplaintStatus.RESOLVED):
            resolution_text: str = str(complaint_data.get("resolution", ""))
            resolution_truncated = resolution_text[:300] if len(
                resolution_text) > 300 else resolution_text
            resolution_suffix = "..." if len(resolution_text) > 300 else ""

            status_messages = {
                ComplaintStatus.ESCALATED: (
                    f"📤 Complaint #{complaint.id} has been escalated to management for review.\n\n"
                    f"Order: #{order.id}"
                ),
                ComplaintStatus.RESOLVED: (
                    f"✅ Complaint #{complaint.id} has been resolved.\n\n"
                    f"Order: #{order.id}\n"
                    + (f"Resolution: {resolution_truncated}{resolution_suffix}" if resolution_text else "")
                ),
            }
            message_text = status_messages.get(complaint_data["status"])
            if message_text:
                # Determine sender: use manager for escalated/resolved (they would have taken the action)
                sender_id = manager.id
                complaint_status_message = ChatMessage(
                    session_id=chat_session.id,
                    sender_id=sender_id,
                    text=message_text,
                    # Post 5 minutes after complaint
                    created_at=datetime.now(UTC) + timedelta(minutes=5),
                )
                session.add(complaint_status_message)
                chat_messages_created += 1

                # Create notification for consumer when complaint status changes (matches backend router logic)
                if consumer.user_id:
                    notification_messages = {
                        ComplaintStatus.ESCALATED: f"Your complaint #{complaint.id} has been escalated and is being reviewed by management.",
                        ComplaintStatus.RESOLVED: f"Your complaint #{complaint.id} has been resolved." + (f" Resolution: {resolution_text[:100]}" if resolution_text else ""),
                    }
                    notification_message = notification_messages.get(
                        complaint_data["status"])
                    if notification_message:
                        notification_type = f"complaint_{complaint_data['status'].value}"
                        # For complaints, use order_id as entity_id so navigation goes to order details (matches backend router)
                        await create_notification(consumer.user_id, notification_type, notification_message, session, entity_id=order.id, entity_type="order")
                        notifications_created += 1

        complaints.append(complaint)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()

        # Log what was created
        print(
            f"✅ Created {created_count} new complaints (total: {len(complaints)} complaints)"
        )
        print(
            f"   📨 Posted {chat_messages_created} complaint-related messages in chat threads"
        )
        print(
            f"   🔔 Created {notifications_created} notifications for consumers")

        # Count total complaints, chat messages, and notifications in database
        from sqlalchemy import func
        from app.modules.chat.model import ChatMessage as ChatMsg
        from app.modules.notification.model import Notification
        complaint_count = await session.execute(select(func.count(Complaint.id)))
        chat_msg_count = await session.execute(select(func.count(ChatMsg.id)))
        notif_count = await session.execute(select(func.count(Notification.id)))
        print(
            f"   📊 Database totals: {complaint_count.scalar()} complaints, {chat_msg_count.scalar()} chat messages, {notif_count.scalar()} notifications")
    else:
        print(
            f"✅ All required complaints already exist ({len(complaints)} complaints)"
        )

    return complaints[:10]  # Return exactly 10 complaints for compatibility


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
            await seed_complaints(session, orders, consumers, users)

    asyncio.run(main())
