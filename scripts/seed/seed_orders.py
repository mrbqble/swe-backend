"""Seed orders table."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consumer.model import Consumer
from app.modules.order.model import Order, OrderStatus
from app.modules.supplier.model import Supplier


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
        order = Order(
            supplier_id=supplier.id,
            consumer_id=consumer.id,
            status=order_data["status"],
            total_kzt=order_data["total_kzt"],
            created_at=datetime.now(UTC),
        )
        session.add(order)
        orders.append(order)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(f"✅ Created {created_count} new orders (total: {len(orders)} orders)")
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
