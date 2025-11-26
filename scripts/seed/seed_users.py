"""Seed users table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import Notification to ensure SQLAlchemy can resolve the relationship
from app.modules.notification.model import Notification  # noqa: F401
from app.core.roles import Role
from app.modules.user.model import User
from app.utils.hashing import hash_password


async def seed_users(session: AsyncSession) -> dict[str, User]:
    """
    Seed users table with various roles.

    Uses upsert logic: creates users if they don't exist, otherwise uses existing ones.

    Returns:
        Dictionary mapping email to User object for use in other seed scripts.
    """
    # Get existing users
    result = await session.execute(select(User))
    existing_users = {user.email: user for user in result.scalars().all()}

    users_data = [
        # Supplier Owners
        {
            "email": "supplier1@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "John",
            "last_name": "Supplier",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier2@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Jane",
            "last_name": "Merchant",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier3@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Bob",
            "last_name": "Vendor",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier4@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Carol",
            "last_name": "Trader",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier5@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Daniel",
            "last_name": "Dealer",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier6@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Emma",
            "last_name": "Exporter",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier7@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Felix",
            "last_name": "Furnisher",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier8@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Gina",
            "last_name": "Goods",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier9@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Hugo",
            "last_name": "Handler",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        {
            "email": "supplier10@example.com",
            "password_hash": hash_password("Supplier123!"),
            "first_name": "Ivy",
            "last_name": "Importer",
            "role": Role.SUPPLIER_OWNER,
            "is_active": True,
        },
        # Supplier Managers
        {
            "email": "manager1@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Alice",
            "last_name": "Manager",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager2@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Charlie",
            "last_name": "Supervisor",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager3@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Diana",
            "last_name": "Director",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager4@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Edward",
            "last_name": "Executive",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager5@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Fiona",
            "last_name": "Foreman",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager6@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "George",
            "last_name": "Governing",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager7@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Helen",
            "last_name": "Head",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager8@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Ian",
            "last_name": "Incharge",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager9@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Julia",
            "last_name": "Junior",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        {
            "email": "manager10@example.com",
            "password_hash": hash_password("Manager123!"),
            "first_name": "Kevin",
            "last_name": "Keeper",
            "role": Role.SUPPLIER_MANAGER,
            "is_active": True,
        },
        # Supplier Sales Reps
        {
            "email": "sales1@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "David",
            "last_name": "Sales",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales2@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Eva",
            "last_name": "Rep",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales3@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Frank",
            "last_name": "Agent",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales4@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Grace",
            "last_name": "Giver",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales5@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Harry",
            "last_name": "Helper",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales6@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Isabel",
            "last_name": "Informer",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales7@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "James",
            "last_name": "Juggler",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales8@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Kara",
            "last_name": "Keeper",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales9@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Liam",
            "last_name": "Liaison",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        {
            "email": "sales10@example.com",
            "password_hash": hash_password("Sales123!"),
            "first_name": "Maya",
            "last_name": "Mediator",
            "role": Role.SUPPLIER_SALES,
            "is_active": True,
        },
        # Consumers
        {
            "email": "consumer1@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Grace",
            "last_name": "Consumer",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer2@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Henry",
            "last_name": "Buyer",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer3@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Iris",
            "last_name": "Client",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer4@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Jack",
            "last_name": "Customer",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer5@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Kelly",
            "last_name": "Keeper",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer6@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Leo",
            "last_name": "Loyal",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer7@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Mia",
            "last_name": "Member",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer8@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Noah",
            "last_name": "Network",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer9@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Olivia",
            "last_name": "Outlet",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        {
            "email": "consumer10@example.com",
            "password_hash": hash_password("Consumer123!"),
            "first_name": "Paul",
            "last_name": "Partner",
            "role": Role.CONSUMER,
            "is_active": True,
        },
        # Inactive user for testing
        {
            "email": "inactive@example.com",
            "password_hash": hash_password("Inactive123!"),
            "first_name": "Inactive",
            "last_name": "User",
            "role": Role.CONSUMER,
            "is_active": False,
        },
    ]

    users = []
    created_count = 0
    for user_data in users_data:
        email = user_data["email"]
        if email in existing_users:
            # User already exists, use it
            users.append(existing_users[email])
        else:
            # Create new user
            role = user_data["role"]
            assert isinstance(role, Role), f"Expected Role, got {type(role)}"
            user = User(
                email=email,
                password_hash=user_data["password_hash"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                role=role.value,
                is_active=user_data["is_active"],
                created_at=datetime.now(UTC),
            )
            session.add(user)
            users.append(user)
            created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new users (total: {len(users)} users available)"
        )
    else:
        print(f"✅ All required users already exist ({len(users)} users available)")

    return {user.email: user for user in users}


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal

    async def main():
        async with AsyncSessionLocal() as session:
            await seed_users(session)

    asyncio.run(main())
