from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.security import Role
from app.models.link import Link
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import Consumer, Supplier, User


@pytest.mark.asyncio
async def test_user_supplier_product_crud(session_factory):
    async with session_factory() as session:
        user = User(email="supplier@example.com", password_hash="hash", role=Role.SUPPLIER_OWNER)
        session.add(user)
        await session.flush()

        supplier = Supplier(user_id=user.id, name="Acme Supplies")
        session.add(supplier)
        await session.flush()

        product = Product(supplier_id=supplier.id, name="Tomatoes", price_kzt=Decimal("1250.00"))
        session.add(product)
        await session.commit()

    async with session_factory() as session:
        stmt = select(Product).where(Product.name == "Tomatoes")
        result = await session.execute(stmt)
        stored = result.scalar_one()
        assert stored.price_kzt == Decimal("1250.00")
        assert stored.supplier_id == supplier.id


@pytest.mark.asyncio
async def test_order_flow(session_factory):
    async with session_factory() as session:
        supplier_user = User(email="owner@example.com", password_hash="hash", role=Role.SUPPLIER_OWNER)
        consumer_user = User(email="consumer@example.com", password_hash="hash", role=Role.CONSUMER)
        session.add_all([supplier_user, consumer_user])
        await session.flush()

        supplier = Supplier(user_id=supplier_user.id, name="Veggie Supply")
        consumer = Consumer(user_id=consumer_user.id, org_name="Fresh Eats")
        session.add_all([supplier, consumer])
        await session.flush()

        link = Link(supplier_id=supplier.id, consumer_id=consumer.id)
        session.add(link)
        await session.flush()

        product = Product(supplier_id=supplier.id, name="Carrots", price_kzt=Decimal("500.00"))
        session.add(product)
        await session.flush()

        order = Order(supplier_id=supplier.id, consumer_id=consumer.id, total_kzt=Decimal("1500.00"))
        session.add(order)
        await session.flush()

        item = OrderItem(order_id=order.id, product_id=product.id, qty=3, unit_price_kzt=Decimal("500.00"))
        session.add(item)
        await session.commit()

    async with session_factory() as session:
        stmt = select(Order).where(Order.id == order.id)
        result = await session.execute(stmt)
        stored = result.scalar_one()
        assert stored.total_kzt == Decimal("1500.00")
        assert len(stored.items) == 1
        assert stored.items[0].qty == 3
