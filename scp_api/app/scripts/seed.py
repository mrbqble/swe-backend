import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.security import Role
from app.db.session import get_session_factory
from app.models import Consumer, Link, Product, Supplier, User
from app.models.enums import LinkStatus
from app.utils.hashing import hash_password

OWNER_EMAIL = "owner@example.com"
CONSUMER_EMAIL = "consumer@example.com"
DEFAULT_PASSWORD = "ChangeMe123!"


async def run_seed() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == OWNER_EMAIL))
        owner = result.scalar_one_or_none()
        if owner is None:
            owner = User(
                email=OWNER_EMAIL,
                password_hash=hash_password(DEFAULT_PASSWORD),
                role=Role.SUPPLIER_OWNER,
            )
            session.add(owner)
            await session.flush()

        result = await session.execute(select(Supplier).where(Supplier.user_id == owner.id))
        supplier = result.scalar_one_or_none()
        if supplier is None:
            supplier = Supplier(user_id=owner.id, name="Demo Supplier")
            session.add(supplier)
            await session.flush()

        result = await session.execute(select(User).where(User.email == CONSUMER_EMAIL))
        consumer_user = result.scalar_one_or_none()
        if consumer_user is None:
            consumer_user = User(
                email=CONSUMER_EMAIL,
                password_hash=hash_password(DEFAULT_PASSWORD),
                role=Role.CONSUMER,
            )
            session.add(consumer_user)
            await session.flush()

        result = await session.execute(select(Consumer).where(Consumer.user_id == consumer_user.id))
        consumer = result.scalar_one_or_none()
        if consumer is None:
            consumer = Consumer(user_id=consumer_user.id, org_name="Demo Consumer")
            session.add(consumer)
            await session.flush()

        product_specs = [
            ("Apples", "Fresh apples", Decimal("1200.00")),
            ("Oranges", "Sweet oranges", Decimal("1500.00")),
            ("Bananas", "Ripe bananas", Decimal("900.00")),
        ]

        for name, description, price in product_specs:
            result = await session.execute(
                select(Product).where(Product.supplier_id == supplier.id, Product.name == name)
            )
            product = result.scalar_one_or_none()
            if product is None:
                session.add(
                    Product(
                        supplier_id=supplier.id,
                        name=name,
                        description=description,
                        price_kzt=price,
                    )
                )

        result = await session.execute(
            select(Link).where(Link.supplier_id == supplier.id, Link.consumer_id == consumer.id)
        )
        link = result.scalar_one_or_none()
        if link is None:
            session.add(Link(supplier_id=supplier.id, consumer_id=consumer.id, status=LinkStatus.PENDING))

        await session.commit()

    print("Seed data inserted.")


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
