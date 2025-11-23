"""Seed users table."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        # Admin
        {
            "email": "admin@example.com",
            "password_hash": hash_password("Admin123!"),
            "first_name": "Admin",
            "last_name": "User",
            "role": Role.ADMIN,
            "is_active": True,
        },
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
