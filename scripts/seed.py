"""Database seeding script.

This script creates initial seed data for development and testing:
- One supplier with owner, manager, and sales staff
- One consumer
- Sample products
- A pending link between consumer and supplier
- A sample order
"""

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select

from app.core.roles import Role
from app.db.session import AsyncSessionLocal, engine
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.order.model import Order, OrderItem, OrderStatus
from app.modules.product.model import Product
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.hashing import hash_password
import app.modules.chat.model
import app.modules.complaint.model
import app.modules.notification.model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_database() -> None:
    """Seed the database with initial data."""
    logger.info("🌱 Starting database seeding...")

    async with AsyncSessionLocal() as session:
        try:
            # Check if data already exists
            result = await session.execute(select(User).limit(1))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                logger.warning("⚠️  Database already contains data. Skipping seed.")
                logger.info("   To re-seed, clear the database first.")
                return

            # ====================================================================
            # 1. Create Supplier Owner User
            # ====================================================================
            logger.info("📦 Creating supplier owner...")
            supplier_owner_user = User(
                email="supplier.owner@example.com",
                password_hash=hash_password("Password123"),
                role=Role.SUPPLIER_OWNER.value,
                is_active=True,
            )
            session.add(supplier_owner_user)
            await session.flush()

            # ====================================================================
            # 2. Create Supplier
            # ====================================================================
            logger.info("🏢 Creating supplier...")
            supplier = Supplier(
                user_id=supplier_owner_user.id,
                company_name="Acme Wholesale Supplies",
                is_active=True,
            )
            session.add(supplier)
            await session.flush()

            # ====================================================================
            # 3. Create Supplier Manager User
            # ====================================================================
            logger.info("👔 Creating supplier manager...")
            supplier_manager_user = User(
                email="supplier.manager@example.com",
                password_hash=hash_password("Password123"),
                role=Role.SUPPLIER_MANAGER.value,
                is_active=True,
            )
            session.add(supplier_manager_user)
            await session.flush()

            # Add manager to supplier staff
            manager_staff = SupplierStaff(
                user_id=supplier_manager_user.id,
                supplier_id=supplier.id,
                staff_role="manager",
            )
            session.add(manager_staff)

            # ====================================================================
            # 4. Create Supplier Sales User
            # ====================================================================
            logger.info("💼 Creating supplier sales rep...")
            supplier_sales_user = User(
                email="supplier.sales@example.com",
                password_hash=hash_password("Password123"),
                role=Role.SUPPLIER_SALES.value,
                is_active=True,
            )
            session.add(supplier_sales_user)
            await session.flush()

            # Add sales rep to supplier staff
            sales_staff = SupplierStaff(
                user_id=supplier_sales_user.id,
                supplier_id=supplier.id,
                staff_role="sales",
            )
            session.add(sales_staff)

            # ====================================================================
            # 5. Create Consumer User
            # ====================================================================
            logger.info("🛒 Creating consumer...")
            consumer_user = User(
                email="consumer@example.com",
                password_hash=hash_password("Password123"),
                role=Role.CONSUMER.value,
                is_active=True,
            )
            session.add(consumer_user)
            await session.flush()

            consumer = Consumer(
                user_id=consumer_user.id,
                organization_name="Retail Store Chain",
            )
            session.add(consumer)
            await session.flush()

            # ====================================================================
            # 6. Create Products
            # ====================================================================
            logger.info("📦 Creating products...")
            products_data = [
                {
                    "name": "Premium Widget A",
                    "description": "High-quality widget for industrial use",
                    "price_kzt": Decimal("15000.00"),
                    "currency": "KZT",
                    "sku": "WID-A-001",
                    "stock_qty": 100,
                    "is_active": True,
                },
                {
                    "name": "Standard Widget B",
                    "description": "Standard widget for general use",
                    "price_kzt": Decimal("10000.00"),
                    "currency": "KZT",
                    "sku": "WID-B-002",
                    "stock_qty": 250,
                    "is_active": True,
                },
                {
                    "name": "Economy Widget C",
                    "description": "Budget-friendly widget option",
                    "price_kzt": Decimal("7500.00"),
                    "currency": "KZT",
                    "sku": "WID-C-003",
                    "stock_qty": 500,
                    "is_active": True,
                },
            ]

            products = []
            for product_data in products_data:
                product = Product(
                    supplier_id=supplier.id,
                    **product_data,
                )
                session.add(product)
                products.append(product)

            await session.flush()

            # ====================================================================
            # 7. Create Pending Link
            # ====================================================================
            logger.info("🔗 Creating pending link...")
            link = Link(
                consumer_id=consumer.id,
                supplier_id=supplier.id,
                status=LinkStatus.PENDING,
            )
            session.add(link)
            await session.flush()

            # ====================================================================
            # 8. Create Sample Order (requires accepted link, so we'll accept it first)
            # ====================================================================
            logger.info("📋 Creating sample order...")
            # Accept the link first (orders require accepted links)
            link.status = LinkStatus.ACCEPTED

            # Create order with items
            order = Order(
                supplier_id=supplier.id,
                consumer_id=consumer.id,
                status=OrderStatus.PENDING,
                total_kzt=Decimal("0.00"),  # Will be calculated
            )
            session.add(order)
            await session.flush()

            # Add order items
            order_items = [
                OrderItem(
                    order_id=order.id,
                    product_id=products[0].id,
                    qty=5,
                    unit_price_kzt=products[0].price_kzt,
                ),
                OrderItem(
                    order_id=order.id,
                    product_id=products[1].id,
                    qty=10,
                    unit_price_kzt=products[1].price_kzt,
                ),
            ]
            for item in order_items:
                session.add(item)

            # Calculate total
            total = sum(item.qty * item.unit_price_kzt for item in order_items)
            order.total_kzt = total

            # ====================================================================
            # Commit all changes
            # ====================================================================
            await session.commit()
            logger.info("✅ Database seeded successfully!")

            # ====================================================================
            # Print summary
            # ====================================================================
            logger.info("\n" + "=" * 60)
            logger.info("📊 Seed Data Summary")
            logger.info("=" * 60)
            logger.info(f"✅ Supplier Owner: {supplier_owner_user.email} (Password123)")
            logger.info(
                f"✅ Supplier Manager: {supplier_manager_user.email} (Password123)"
            )
            logger.info(f"✅ Supplier Sales: {supplier_sales_user.email} (Password123)")
            logger.info(f"✅ Consumer: {consumer_user.email} (Password123)")
            logger.info(f"✅ Supplier: {supplier.company_name}")
            logger.info(f"✅ Products: {len(products)} created")
            logger.info(f"✅ Link: {link.status.value} (consumer ↔ supplier)")
            logger.info(
                f"✅ Order: {order.status.value} (total: {order.total_kzt} KZT)"
            )
            logger.info("=" * 60)
            logger.info(
                "\n💡 You can now log in with any of the above email addresses."
            )
            logger.info("   All passwords are: Password123")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error seeding database: {e}", exc_info=True)
            raise


async def main() -> None:
    """Main entry point."""
    try:
        await seed_database()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
