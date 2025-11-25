"""Seed links table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.supplier.model import Supplier


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
    ]

    links = []
    created_count = 0
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
            links.append(existing_links_map[key])
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

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(f"✅ Created {created_count} new links (total: {len(links)} links)")
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
