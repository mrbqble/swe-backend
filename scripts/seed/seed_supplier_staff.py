"""Seed supplier_staff table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User


async def seed_supplier_staff(
    session: AsyncSession, users: dict[str, User], suppliers: dict[str, Supplier]
) -> list[SupplierStaff]:
    """
    Seed supplier_staff table.

    Args:
        session: Database session
        users: Dictionary of users keyed by email
        suppliers: Dictionary of suppliers keyed by company name

    Returns:
        List of SupplierStaff objects.
    """
    # Get existing staff (keyed by (user_id, supplier_id) tuple)
    result = await session.execute(select(SupplierStaff))
    existing_staff_map = {
        (staff.user_id, staff.supplier_id): staff for staff in result.scalars().all()
    }

    # Validate required users and suppliers exist
    required_user_emails = [
        "manager1@example.com",
        "sales1@example.com",
        "manager2@example.com",
        "sales2@example.com",
        "sales3@example.com",
        "manager3@example.com",
        "sales4@example.com",
        "manager4@example.com",
        "sales5@example.com",
        "manager5@example.com",
    ]
    for email in required_user_emails:
        if email not in users:
            raise ValueError(
                f"Required user {email} not found. Please run seed_users first."
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

    staff_data = [
        # Managers for Tech Supplies Co.
        {
            "user": users["manager1@example.com"],
            "supplier": suppliers["Tech Supplies Co."],
            "staff_role": "Operations Manager",
        },
        # Sales reps for Tech Supplies Co.
        {
            "user": users["sales1@example.com"],
            "supplier": suppliers["Tech Supplies Co."],
            "staff_role": "Senior Sales Representative",
        },
        # Manager for Global Merchandise Ltd.
        {
            "user": users["manager2@example.com"],
            "supplier": suppliers["Global Merchandise Ltd."],
            "staff_role": "Sales Manager",
        },
        # Sales reps for Global Merchandise Ltd.
        {
            "user": users["sales2@example.com"],
            "supplier": suppliers["Global Merchandise Ltd."],
            "staff_role": "Sales Representative",
        },
        # Sales rep for Premium Products Inc.
        {
            "user": users["sales3@example.com"],
            "supplier": suppliers["Premium Products Inc."],
            "staff_role": "Sales Representative",
        },
        # Manager for Industrial Equipment Solutions
        {
            "user": users["manager3@example.com"],
            "supplier": suppliers["Industrial Equipment Solutions"],
            "staff_role": "Operations Manager",
        },
        # Sales rep for Office Essentials Pro
        {
            "user": users["sales4@example.com"],
            "supplier": suppliers["Office Essentials Pro"],
            "staff_role": "Sales Representative",
        },
        # Manager for Industrial Equipment Solutions
        {
            "user": users["manager4@example.com"],
            "supplier": suppliers["Industrial Equipment Solutions"],
            "staff_role": "Sales Manager",
        },
        # Sales rep for Office Essentials Pro
        {
            "user": users["sales5@example.com"],
            "supplier": suppliers["Office Essentials Pro"],
            "staff_role": "Senior Sales Representative",
        },
        # Manager for Digital Devices Direct
        {
            "user": users["manager5@example.com"],
            "supplier": suppliers["Digital Devices Direct"],
            "staff_role": "Operations Manager",
        },
    ]

    staff_list = []
    created_count = 0
    for staff_info in staff_data:
        user = staff_info["user"]
        supplier = staff_info["supplier"]
        assert isinstance(user, User), f"Expected User, got {type(user)}"
        assert isinstance(supplier, Supplier), (
            f"Expected Supplier, got {type(supplier)}"
        )
        user_id = user.id
        supplier_id = supplier.id
        key = (user_id, supplier_id)

        if key in existing_staff_map:
            # Staff relationship already exists, use it
            staff_list.append(existing_staff_map[key])
        else:
            # Create new staff relationship
            staff = SupplierStaff(
                user_id=user_id,
                supplier_id=supplier_id,
                staff_role=staff_info["staff_role"],
                created_at=datetime.now(UTC),
            )
            session.add(staff)
            staff_list.append(staff)
            created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new supplier staff relationships (total: {len(staff_list)} staff members)"
        )
    else:
        print(
            f"✅ All required supplier staff relationships already exist ({len(staff_list)} staff members)"
        )

    return staff_list


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_suppliers import seed_suppliers
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            suppliers = await seed_suppliers(session, users)
            await seed_supplier_staff(session, users, suppliers)

    asyncio.run(main())
