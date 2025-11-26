"""Seed orders table."""

import asyncio
import random
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.model import ChatSession
from app.modules.consumer.model import Consumer
from app.modules.order.model import Order, OrderStatus
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import create_notification


async def assign_sales_rep_for_seed(
    supplier_id: int, session: AsyncSession, batch_orders: list[Order]
) -> int:
    """
    Assign a sales representative for seed data with even distribution.

    This mimics the production logic: assigns to sales rep with least orders.

    Args:
        supplier_id: Supplier ID
        session: Database session
        batch_orders: List of orders being created in this batch (for counting)

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

    # Count orders for each sales rep (from database + batch orders for this supplier)
    sales_rep_order_counts: dict[int, int] = {}
    for sales_rep_staff in sales_reps:
        user_id = sales_rep_staff.user_id
        # Count orders from database assigned to this sales rep for this supplier
        count_result = await session.execute(
            select(func.count(Order.id))
            .where(Order.sales_rep_id == user_id)
            .where(Order.supplier_id == supplier_id)
        )
        db_order_count = count_result.scalar_one() or 0

        # Also count from batch orders (orders being created in this run) for this supplier
        batch_count = sum(
            1
            for order in batch_orders
            if getattr(order, 'sales_rep_id', None) == user_id
            and getattr(order, 'supplier_id', None) == supplier_id
        )

        sales_rep_order_counts[user_id] = db_order_count + batch_count

    # Find sales rep with minimum order count
    min_count = min(sales_rep_order_counts.values())
    candidates = [
        user_id
        for user_id, count in sales_rep_order_counts.items()
        if count == min_count
    ]

    # If all have equal orders, assign randomly; otherwise assign to the one with least
    selected_user_id = random.choice(candidates)

    return selected_user_id


async def seed_orders(
    session: AsyncSession,
    suppliers: dict[str, Supplier],
    consumers: dict[str, Consumer],
) -> list[Order]:
    """
    Seed orders table.

    Args:
        session: Database session
        suppliers: Dictionary of suppliers keyed by company name
        consumers: Dictionary of consumers keyed by organization name

    Returns:
        List of Order objects.
    """
    # Get existing orders
    result = await session.execute(select(Order))
    existing_orders = result.scalars().all()

    # Validate required suppliers and consumers exist
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

    # If we already have 10 or more orders, assume seeding is done
    if len(existing_orders) >= 10:
        print(
            f"⚠️  Orders already exist ({len(existing_orders)} orders), skipping seed_orders"
        )
        return existing_orders[:10]  # Return first 10 for compatibility

    orders_data = [
        {
            "supplier": suppliers["Tech Supplies Co."],
            "consumer": consumers["Retail Chain ABC"],
            "status": OrderStatus.PENDING,
            "total_kzt": Decimal("500000.00"),
        },
        {
            "supplier": suppliers["Tech Supplies Co."],
            "consumer": consumers["Retail Chain ABC"],
            "status": OrderStatus.ACCEPTED,
            "total_kzt": Decimal("750000.00"),
        },
        {
            "supplier": suppliers["Tech Supplies Co."],
            "consumer": consumers["Wholesale Distributor XYZ"],
            "status": OrderStatus.IN_PROGRESS,
            "total_kzt": Decimal("1200000.00"),
        },
        {
            "supplier": suppliers["Global Merchandise Ltd."],
            "consumer": consumers["Retail Chain ABC"],
            "status": OrderStatus.COMPLETED,
            "total_kzt": Decimal("95000.00"),
        },
        {
            "supplier": suppliers["Global Merchandise Ltd."],
            "consumer": consumers["Supermarket Network 123"],
            "status": OrderStatus.ACCEPTED,
            "total_kzt": Decimal("103000.00"),
        },
        {
            "supplier": suppliers["Premium Products Inc."],
            "consumer": consumers["Wholesale Distributor XYZ"],
            "status": OrderStatus.COMPLETED,
            "total_kzt": Decimal("390000.00"),
        },
        {
            "supplier": suppliers["Premium Products Inc."],
            "consumer": consumers["Wholesale Distributor XYZ"],
            "status": OrderStatus.REJECTED,
            "total_kzt": Decimal("250000.00"),
        },
        {
            "supplier": suppliers["Industrial Equipment Solutions"],
            "consumer": consumers["Corporate Buyers Alliance"],
            "status": OrderStatus.ACCEPTED,
            "total_kzt": Decimal("850000.00"),
        },
        {
            "supplier": suppliers["Office Essentials Pro"],
            "consumer": consumers["Retail Outlet Network"],
            "status": OrderStatus.IN_PROGRESS,
            "total_kzt": Decimal("320000.00"),
        },
        {
            "supplier": suppliers["Digital Devices Direct"],
            "consumer": consumers["Bulk Purchase Consortium"],
            "status": OrderStatus.COMPLETED,
            "total_kzt": Decimal("680000.00"),
        },
    ]

    # If we have existing orders, use them (up to 10)
    orders = (
        existing_orders[:10] if len(existing_orders) >= 10 else existing_orders.copy()
    )
    created_count = 0
    batch_orders: list[Order] = []  # Track orders being created in this batch

    # Create missing orders
    for order_data in orders_data:
        if len(orders) >= 10:
            break  # We have enough orders

        supplier = order_data["supplier"]
        consumer = order_data["consumer"]
        assert isinstance(supplier, Supplier), (
            f"Expected Supplier, got {type(supplier)}"
        )
        assert isinstance(consumer, Consumer), (
            f"Expected Consumer, got {type(consumer)}"
        )

        # Verify there's an accepted link between consumer and supplier
        # Backend requires ACCEPTED link before order can be created
        from app.modules.link.model import Link, LinkStatus
        result = await session.execute(
            select(Link).where(
                Link.consumer_id == consumer.id,
                Link.supplier_id == supplier.id,
                Link.status == LinkStatus.ACCEPTED,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            # Skip this order - no accepted link exists (matches backend validation)
            print(f"⚠️  Skipping order for consumer {consumer.id} and supplier {supplier.id} - no accepted link exists")
            continue

        # Assign sales rep: first check if consumer already has a chat session (assignment) for this supplier
        # If yes, use that sales rep. If no, assign a new one.
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.consumer_id == consumer.id,
                ChatSession.supplier_id == supplier.id,
            )
        )
        existing_chat_session = result.scalar_one_or_none()

        if existing_chat_session:
            # Use the sales rep already assigned to this consumer for this supplier
            sales_rep_id = existing_chat_session.sales_rep_id
        else:
            # No existing assignment, assign a new sales rep with even distribution logic
            # Pass batch_orders to track orders being created in this run
            sales_rep_id = await assign_sales_rep_for_seed(
                supplier.id, session, batch_orders
            )

        order = Order(
            supplier_id=supplier.id,
            consumer_id=consumer.id,
            sales_rep_id=sales_rep_id,
            status=order_data["status"],
            total_kzt=order_data["total_kzt"],
            created_at=datetime.now(UTC),
        )
        session.add(order)
        await session.flush()  # Flush to get order.id
        orders.append(order)
        batch_orders.append(order)  # Track in batch for next assignment
        created_count += 1

        # Post structured order message in chat (matches backend router logic)
        # Chat session should already exist from link acceptance, but verify
        if not existing_chat_session:
            # Create chat session if it doesn't exist (should exist from link acceptance, but create as fallback)
            chat_session = ChatSession(
                consumer_id=consumer.id,
                supplier_id=supplier.id,
                sales_rep_id=sales_rep_id,
                created_at=datetime.now(UTC),
            )
            session.add(chat_session)
            await session.flush()  # Flush to get session.id
            existing_chat_session = chat_session

        # Post structured order message in the chat thread (only if link exists and is accepted)
        # Format: Clear order notification with order details (matches router logic)
        from app.modules.chat.model import ChatMessage

        # For seeding, create a simple summary (order items will be added later in seed_order_items)
        order_message_text = (
            f"📦 Order #{order.id} created\n\n"
            f"Total: {order.total_kzt:.2f} KZT\n"
            f"Status: Pending approval"
        )

        # Get consumer user for sender_id
        from app.modules.user.model import User
        consumer_user_result = await session.execute(
            select(User).where(User.id == consumer.user_id)
        )
        consumer_user = consumer_user_result.scalar_one()

        order_message = ChatMessage(
            session_id=existing_chat_session.id,
            sender_id=consumer_user.id,  # Consumer who created the order
            text=order_message_text,
            created_at=datetime.now(UTC),
        )
        session.add(order_message)

        # Create notification for consumer when order is created (matches backend router logic)
        if consumer.user_id:
            supplier_result = await session.execute(
                select(Supplier).where(Supplier.id == supplier.id)
            )
            supplier_obj = supplier_result.scalar_one_or_none()
            supplier_name = supplier_obj.company_name if supplier_obj and supplier_obj.company_name else "Supplier"
            message = f"Your order #{order.id} has been created and is pending approval from {supplier_name}."
            await create_notification(consumer.user_id, "order_created", message, session, entity_id=order.id, entity_type="order")

    if created_count > 0:
        await session.flush()
        await session.commit()

        # Log what was created
        print(f"✅ Created {created_count} new orders (total: {len(orders)} orders)")
        print(f"   📨 Posted {created_count} order messages in chat threads")
        print(f"   🔔 Created {created_count} notifications for consumers")

        # Count total orders, chat messages, and notifications in database
        from app.modules.chat.model import ChatMessage as ChatMsg
        from app.modules.notification.model import Notification
        order_count = await session.execute(select(func.count(Order.id)))
        chat_msg_count = await session.execute(select(func.count(ChatMsg.id)))
        notif_count = await session.execute(select(func.count(Notification.id)))
        print(f"   📊 Database totals: {order_count.scalar()} orders, {chat_msg_count.scalar()} chat messages, {notif_count.scalar()} notifications")
    else:
        print(f"✅ All required orders already exist ({len(orders)} orders)")

    return orders[:10]  # Return exactly 10 orders for compatibility


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
            await seed_orders(session, suppliers, consumers)

    asyncio.run(main())
