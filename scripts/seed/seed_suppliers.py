"""Seed suppliers table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplier.model import Supplier
from app.modules.user.model import User


async def seed_suppliers(
    session: AsyncSession, users: dict[str, User]
) -> dict[str, Supplier]:
    """
    Seed suppliers table.

    Args:
        session: Database session
        users: Dictionary of users keyed by email

    Returns:
        Dictionary mapping company name to Supplier object for use in other seed scripts.
    """
    # Get existing suppliers
    result = await session.execute(select(Supplier))
    existing_suppliers = {
        supplier.company_name: supplier for supplier in result.scalars().all()
    }

    # Get supplier owner users - ensure they exist
    required_emails = [
        "supplier1@example.com",
        "supplier2@example.com",
        "supplier3@example.com",
        "supplier4@example.com",
        "supplier5@example.com",
        "supplier6@example.com",
        "supplier7@example.com",
        "supplier8@example.com",
        "supplier9@example.com",
        "supplier10@example.com",
    ]
    supplier_owners: list[User] = []
    for email in required_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
            )
        user = users[email]
        assert isinstance(user, User), f"Expected User, got {type(user)}"
        supplier_owners.append(user)

    suppliers_data = [
        {
            "user": supplier_owners[0],
            "company_name": "Tech Supplies Co.",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[1],
            "company_name": "Global Merchandise Ltd.",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[2],
            "company_name": "Premium Products Inc.",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[3],
            "company_name": "Industrial Equipment Solutions",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[4],
            "company_name": "Office Essentials Pro",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[5],
            "company_name": "Digital Devices Direct",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[6],
            "company_name": "Furniture & Fixtures Co.",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[7],
            "company_name": "Electronics Warehouse",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[8],
            "company_name": "Business Supplies Hub",
            "is_active": True,
            "company_logo": None,
        },
        {
            "user": supplier_owners[9],
            "company_name": "Tech Accessories Plus",
            "is_active": True,
            "company_logo": None,
        },
    ]

    suppliers = []
    created_count = 0
    for supplier_data in suppliers_data:
        company_name = supplier_data["company_name"]
        if company_name in existing_suppliers:
            # Supplier already exists, use it
            suppliers.append(existing_suppliers[company_name])
        else:
            # Create new supplier
            user_obj = supplier_data["user"]
            assert isinstance(user_obj, User), f"Expected User, got {type(user_obj)}"
            supplier = Supplier(
                user_id=user_obj.id,
                company_name=company_name,
                is_active=supplier_data["is_active"],
                company_logo=supplier_data.get("company_logo"),
                created_at=datetime.now(UTC),
            )
            session.add(supplier)
            suppliers.append(supplier)
            created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new suppliers (total: {len(suppliers)} suppliers available)"
        )
    else:
        print(
            f"✅ All required suppliers already exist ({len(suppliers)} suppliers available)"
        )

    return {supplier.company_name: supplier for supplier in suppliers}


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            await seed_suppliers(session, users)

    asyncio.run(main())
