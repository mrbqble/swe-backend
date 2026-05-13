"""Main script to seed all database tables in the correct order."""

import asyncio
import sys

# Register all mappers before any session work
from app.modules.admin.model import AdminAction, AdminUser, FAQ  # noqa: F401
from app.modules.auth.model import EmailConfirmation, OtpCode, Session  # noqa: F401
from app.modules.cart.model import CartItem  # noqa: F401
from app.modules.ip_too.model import IpToo  # noqa: F401
from app.modules.notification.model import Notification  # noqa: F401
from app.modules.order.model import Order, OrderItem  # noqa: F401
from app.modules.payment.model import Payment  # noqa: F401
from app.modules.product.model import Product  # noqa: F401
from app.modules.support.model import Suggestion  # noqa: F401
from app.modules.user.model import User  # noqa: F401

from app.db.session import AsyncSessionLocal
from scripts.seed.seed_admin import seed_admin
from scripts.seed.seed_products import seed_products
from scripts.seed.seed_users import seed_users


async def seed_all():
    """Seed all database tables in the correct dependency order."""
    print("Starting database seeding...")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        try:
            print("\nStep 1: Seeding users...")
            await seed_users(session)

            print("\nStep 2: Seeding products...")
            await seed_products(session)

            print("\nStep 3: Seeding admin users...")
            await seed_admin(session)

            print("\n" + "=" * 60)
            print("Database seeding completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\nError during seeding: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    try:
        asyncio.run(seed_all())
    except KeyboardInterrupt:
        print("\nSeeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
