"""Seed links table.

According to new backend structure:
- Chat sessions are automatically created when links are accepted
- Each consumer is assigned to 1 sales rep per supplier when link is accepted
"""

import asyncio
import random
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatSession
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import create_notification


async def assign_sales_rep_for_link_seed(
    supplier_id: int, session: AsyncSession, batch_sessions: list[ChatSession]
) -> int:
    """
    Assign a sales representative for link acceptance with even distribution.

    Counts ChatSessions (consumer assignments) to ensure even distribution.

    Args:
        supplier_id: Supplier ID
        session: Database session
        batch_sessions: List of chat sessions being created in this batch (for counting)

    Returns:
        User ID of the assigned sales representative
    """
    # Get all active sales reps for this supplier
    result = await session.execute(
        select(SupplierStaff)
        .join(User, SupplierStaff.user_id == User.id)
        .where(SupplierStaff.supplier_id == supplier_id)
        .where(SupplierStaff.staff_role.ilike("%sales%"))
        .where(User.is_active)
    )
    sales_reps = result.scalars().all()

    if not sales_reps:
        # If no sales rep found, try to get any active staff member
        result = await session.execute(
            select(SupplierStaff)
            .join(User, SupplierStaff.user_id == User.id)
            .where(SupplierStaff.supplier_id == supplier_id)
            .where(User.is_active)
        )
        sales_reps = result.scalars().all()

    if not sales_reps:
        # Last resort: try to get the supplier owner
        result = await session.execute(
            select(Supplier)
            .join(User, Supplier.user_id == User.id)
            .where(Supplier.id == supplier_id)
            .where(User.is_active)
        )
        supplier = result.scalar_one_or_none()
        if supplier and supplier.user_id:
            return supplier.user_id
        raise ValueError(
            f"No sales representative found for supplier {supplier_id}"
        )

    # Count ChatSessions (consumer assignments) for each sales rep for this supplier
    # Count from database + batch sessions
    sales_rep_counts: dict[int, int] = {}
    for sales_rep_staff in sales_reps:
        user_id = sales_rep_staff.user_id

        # Count ChatSessions from database for this sales rep and supplier
        # Now we can use supplier_id directly in ChatSession
        count_result = await session.execute(
            select(func.count(func.distinct(ChatSession.consumer_id)))
            .where(ChatSession.sales_rep_id == user_id)
            .where(ChatSession.supplier_id == supplier_id)
        )
        db_count = count_result.scalar_one() or 0

        # Also count from batch sessions (sessions being created in this run) for this supplier
        batch_count = sum(
            1
            for chat_session in batch_sessions
            if getattr(chat_session, 'sales_rep_id', None) == user_id
            and getattr(chat_session, 'supplier_id', None) == supplier_id
            and getattr(chat_session, 'consumer_id', None) is not None
        )

        sales_rep_counts[user_id] = db_count + batch_count

    # Find sales rep with minimum consumer assignment count
    min_count = min(sales_rep_counts.values())
    candidates = [
        user_id
        for user_id, count in sales_rep_counts.items()
        if count == min_count
    ]

    # If all have equal assignments, assign randomly; otherwise assign to the one with least
    selected_user_id = random.choice(candidates)
    return selected_user_id


async def seed_links(
    session: AsyncSession,
    consumers: dict[str, Consumer],
    suppliers: dict[str, Supplier],
) -> list[Link]:
    """
    Seed links table.

    Args:
        session: Database session
        consumers: Dictionary of consumers keyed by organization name
        suppliers: Dictionary of suppliers keyed by company name

    Returns:
        List of Link objects.
    """
    # Get existing links (keyed by (consumer_id, supplier_id) tuple)
    result = await session.execute(select(Link))
    existing_links_map = {
        (link.consumer_id, link.supplier_id): link for link in result.scalars().all()
    }

    # Validate required consumers and suppliers exist
    required_consumer_names = [
        "Retail Chain ABC",
        "Wholesale Distributor XYZ",
        "Supermarket Network 123",
        "Department Store Group",
        "Corporate Buyers Alliance",
        "Retail Outlet Network",
        "Bulk Purchase Consortium",
    ]
    for name in required_consumer_names:
        if name not in consumers:
            raise ValueError(
                f"Required consumer {name} not found. Please run seed_consumers first."
            )

    required_supplier_names = [
        "Tech Supplies Co.",
        "Global Merchandise Ltd.",
        "Premium Products Inc.",
        "Industrial Equipment Solutions",
        "Office Essentials Pro",
        "Digital Devices Direct",
    ]
    for name in required_supplier_names:
        if name not in suppliers:
            raise ValueError(
                f"Required supplier {name} not found. Please run seed_suppliers first."
            )

    links_data = [
        # Retail Chain ABC links
        {
            "consumer": consumers["Retail Chain ABC"],
            "supplier": suppliers["Tech Supplies Co."],
            "status": LinkStatus.ACCEPTED,
        },
        {
            "consumer": consumers["Retail Chain ABC"],
            "supplier": suppliers["Global Merchandise Ltd."],
            "status": LinkStatus.ACCEPTED,
        },
        {
            "consumer": consumers["Retail Chain ABC"],
            "supplier": suppliers["Premium Products Inc."],
            "status": LinkStatus.PENDING,
        },
        # Wholesale Distributor XYZ links
        {
            "consumer": consumers["Wholesale Distributor XYZ"],
            "supplier": suppliers["Tech Supplies Co."],
            "status": LinkStatus.ACCEPTED,
        },
        {
            "consumer": consumers["Wholesale Distributor XYZ"],
            "supplier": suppliers["Premium Products Inc."],
            "status": LinkStatus.ACCEPTED,
        },
        # Supermarket Network 123 links
        {
            "consumer": consumers["Supermarket Network 123"],
            "supplier": suppliers["Global Merchandise Ltd."],
            "status": LinkStatus.ACCEPTED,
        },
        {
            "consumer": consumers["Supermarket Network 123"],
            "supplier": suppliers["Premium Products Inc."],
            "status": LinkStatus.DENIED,
        },
        # Department Store Group links
        {
            "consumer": consumers["Department Store Group"],
            "supplier": suppliers["Tech Supplies Co."],
            "status": LinkStatus.PENDING,
        },
        {
            "consumer": consumers["Department Store Group"],
            "supplier": suppliers["Global Merchandise Ltd."],
            "status": LinkStatus.BLOCKED,
        },
        {
            "consumer": consumers["Corporate Buyers Alliance"],
            "supplier": suppliers["Industrial Equipment Solutions"],
            "status": LinkStatus.ACCEPTED,
        },
        # Retail Outlet Network links (for order seeding)
        {
            "consumer": consumers["Retail Outlet Network"],
            "supplier": suppliers["Office Essentials Pro"],
            "status": LinkStatus.ACCEPTED,
        },
        # Bulk Purchase Consortium links (for order seeding)
        {
            "consumer": consumers["Bulk Purchase Consortium"],
            "supplier": suppliers["Digital Devices Direct"],
            "status": LinkStatus.ACCEPTED,
        },
    ]

    links = []
    created_count = 0
    batch_chat_sessions: list[ChatSession] = []  # Track sessions being created in this batch

    for link_data in links_data:
        consumer = link_data["consumer"]
        supplier = link_data["supplier"]
        assert isinstance(consumer, Consumer), (
            f"Expected Consumer, got {type(consumer)}"
        )
        assert isinstance(supplier, Supplier), (
            f"Expected Supplier, got {type(supplier)}"
        )
        consumer_id = consumer.id
        supplier_id = supplier.id
        key = (consumer_id, supplier_id)

        if key in existing_links_map:
            # Link already exists, use it
            existing_link = existing_links_map[key]
            links.append(existing_link)

            # If link is accepted, ensure chat session exists
            if existing_link.status == LinkStatus.ACCEPTED:
                result = await session.execute(
                    select(ChatSession).where(
                        ChatSession.consumer_id == consumer_id,
                        ChatSession.supplier_id == supplier_id,
                    )
                )
                existing_session = result.scalar_one_or_none()
                if not existing_session:
                    # Assign sales rep and create session
                    sales_rep_id = await assign_sales_rep_for_link_seed(supplier_id, session, batch_chat_sessions)
                    chat_session = ChatSession(
                        consumer_id=consumer_id,
                        supplier_id=supplier_id,
                        sales_rep_id=sales_rep_id,
                        created_at=datetime.now(UTC),
                    )
                    session.add(chat_session)
                    batch_chat_sessions.append(chat_session)
        else:
            # Create new link
            link = Link(
                consumer_id=consumer_id,
                supplier_id=supplier_id,
                status=link_data["status"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(link)
            links.append(link)
            created_count += 1

            # Create notification for consumer when link request is created (matches backend router logic)
            if consumer.user_id:
                supplier_name = supplier.company_name if supplier and supplier.company_name else "Supplier"
                message = f"Your linking request to {supplier_name} has been submitted and is pending approval."
                await create_notification(consumer.user_id, "link_request_created", message, session, entity_id=link.id, entity_type="link")

            # If link is accepted, automatically create chat session
            if link_data["status"] == LinkStatus.ACCEPTED:
                # Assign sales rep for this consumer-supplier pair
                sales_rep_id = await assign_sales_rep_for_link_seed(supplier_id, session, batch_chat_sessions)

                # Check if session already exists
                result = await session.execute(
                    select(ChatSession).where(
                        ChatSession.consumer_id == consumer_id,
                        ChatSession.supplier_id == supplier_id,
                    )
                )
                existing_session = result.scalar_one_or_none()

                if not existing_session:
                    # Create the chat session
                    chat_session = ChatSession(
                        consumer_id=consumer_id,
                        supplier_id=supplier_id,
                        sales_rep_id=sales_rep_id,
                        created_at=datetime.now(UTC),
                    )
                    session.add(chat_session)
                    batch_chat_sessions.append(chat_session)

                # Create notification for consumer when link is accepted (matches backend router logic)
                if consumer.user_id:
                    supplier_name = supplier.company_name if supplier and supplier.company_name else "Supplier"
                    message = f"Your linking request to {supplier_name} has been accepted."
                    await create_notification(consumer.user_id, "link_accepted", message, session, entity_id=link.id, entity_type="link")

    notifications_created = created_count  # One notification per new link (request created)
    accepted_links_count = sum(1 for link in links if link.status == LinkStatus.ACCEPTED)
    if accepted_links_count > 0:
        # Count how many accepted links were newly created (not existing)
        newly_accepted = sum(1 for link_data in links_data if link_data["status"] == LinkStatus.ACCEPTED and (link_data["consumer"].id, link_data["supplier"].id) not in existing_links_map)
        notifications_created += newly_accepted  # One notification per newly accepted link

    if created_count > 0 or len(batch_chat_sessions) > 0:
        await session.flush()
        await session.commit()

        # Log what was created
        link_msg = f"✅ Created {created_count} new links (total: {len(links)} links)"
        session_msg = f"✅ Created {len(batch_chat_sessions)} chat sessions for accepted links"
        print(link_msg)
        if len(batch_chat_sessions) > 0:
            print(session_msg)
        print(f"   🔔 Created {notifications_created} notifications for consumers")

        # Count total links, chat sessions, and notifications in database
        from sqlalchemy import func
        from app.modules.notification.model import Notification
        link_count = await session.execute(select(func.count(Link.id)))
        session_count = await session.execute(select(func.count(ChatSession.id)))
        notif_count = await session.execute(select(func.count(Notification.id)))
        print(f"   📊 Database totals: {link_count.scalar()} links, {session_count.scalar()} chat sessions, {notif_count.scalar()} notifications")
    else:
        print(f"✅ All required links already exist ({len(links)} links)")

    return links


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_consumers import seed_consumers
    from scripts.seed.seed_suppliers import seed_suppliers
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            suppliers = await seed_suppliers(session, users)
            consumers = await seed_consumers(session, users)
            await seed_links(session, consumers, suppliers)

    asyncio.run(main())
