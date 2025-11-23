"""Main script to seed all database tables in the correct order."""

import asyncio
import sys

from app.db.session import AsyncSessionLocal
from scripts.seed.seed_chat_messages import seed_chat_messages
from scripts.seed.seed_chat_sessions import seed_chat_sessions
from scripts.seed.seed_complaints import seed_complaints
from scripts.seed.seed_consumers import seed_consumers
from scripts.seed.seed_links import seed_links
from scripts.seed.seed_notifications import seed_notifications
from scripts.seed.seed_order_items import seed_order_items
from scripts.seed.seed_orders import seed_orders
from scripts.seed.seed_products import seed_products
from scripts.seed.seed_supplier_staff import seed_supplier_staff
from scripts.seed.seed_suppliers import seed_suppliers
from scripts.seed.seed_users import seed_users


async def seed_all():
    """Seed all database tables in the correct dependency order."""
    print("🌱 Starting database seeding...")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        try:
            # Step 1: Seed users (base table, no dependencies)
            print("\n📝 Step 1: Seeding users...")
            users = await seed_users(session)

            # Step 2: Seed suppliers (depends on users)
            print("\n📝 Step 2: Seeding suppliers...")
            suppliers = await seed_suppliers(session, users)

            # Step 3: Seed consumers (depends on users)
            print("\n📝 Step 3: Seeding consumers...")
            consumers = await seed_consumers(session, users)

            # Step 4: Seed supplier staff (depends on users and suppliers)
            print("\n📝 Step 4: Seeding supplier staff...")
            await seed_supplier_staff(session, users, suppliers)

            # Step 5: Seed products (depends on suppliers)
            print("\n📝 Step 5: Seeding products...")
            products = await seed_products(session, suppliers)

            # Step 6: Seed links (depends on consumers and suppliers)
            print("\n📝 Step 6: Seeding links...")
            await seed_links(session, consumers, suppliers)

            # Step 7: Seed orders (depends on suppliers and consumers)
            print("\n📝 Step 7: Seeding orders...")
            orders = await seed_orders(session, suppliers, consumers)

            # Step 8: Seed order items (depends on orders and products)
            print("\n📝 Step 8: Seeding order items...")
            await seed_order_items(session, orders, products)

            # Step 9: Seed chat sessions (depends on consumers, users, and optionally orders)
            print("\n📝 Step 9: Seeding chat sessions...")
            chat_sessions = await seed_chat_sessions(session, consumers, users, orders)

            # Step 10: Seed chat messages (depends on chat sessions and users)
            print("\n📝 Step 10: Seeding chat messages...")
            await seed_chat_messages(session, chat_sessions, users)

            # Step 11: Seed complaints (depends on orders, consumers, users)
            print("\n📝 Step 11: Seeding complaints...")
            await seed_complaints(session, orders, consumers, users)

            # Step 12: Seed notifications (depends on users)
            print("\n📝 Step 12: Seeding notifications...")
            await seed_notifications(session, users)

            print("\n" + "=" * 60)
            print("✅ Database seeding completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    try:
        asyncio.run(seed_all())
    except KeyboardInterrupt:
        print("\n⚠️  Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
