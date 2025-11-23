"""Seed complaints table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.complaint.model import Complaint, ComplaintStatus
from app.modules.consumer.model import Consumer
from app.modules.order.model import Order
from app.modules.user.model import User


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

    required_consumer_names = ["Retail Chain ABC", "Wholesale Distributor XYZ"]
    for name in required_consumer_names:
        if name not in consumers:
            raise ValueError(
                f"Required consumer {name} not found. Please run seed_consumers first."
            )

    required_user_emails = [
        "sales1@example.com",
        "sales2@example.com",
        "sales3@example.com",
        "manager1@example.com",
        "manager2@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )

    # If we already have 4 or more complaints, assume seeding is done
    if len(existing_complaints) >= 4:
        print(
            f"⚠️  Complaints already exist ({len(existing_complaints)} complaints), skipping seed_complaints"
        )
        return existing_complaints[:4]  # Return first 4 for compatibility

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
    ]

    # If we have existing complaints, use them (up to 4)
    complaints = (
        existing_complaints[:4]
        if len(existing_complaints) >= 4
        else existing_complaints.copy()
    )
    created_count = 0

    # Create missing complaints
    for complaint_data in complaints_data:
        if len(complaints) >= 4:
            break  # We have enough complaints

        order = complaint_data["order"]
        consumer = complaint_data["consumer"]
        sales_rep = complaint_data["sales_rep"]
        manager = complaint_data["manager"]
        assert isinstance(order, Order), f"Expected Order, got {type(order)}"
        assert isinstance(consumer, Consumer), (
            f"Expected Consumer, got {type(consumer)}"
        )
        assert isinstance(sales_rep, User), f"Expected User, got {type(sales_rep)}"
        assert isinstance(manager, User), f"Expected User, got {type(manager)}"
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
        complaints.append(complaint)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new complaints (total: {len(complaints)} complaints)"
        )
    else:
        print(
            f"✅ All required complaints already exist ({len(complaints)} complaints)"
        )

    return complaints[:4]  # Return exactly 4 complaints for compatibility


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
