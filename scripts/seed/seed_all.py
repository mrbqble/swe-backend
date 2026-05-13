"""Main script to seed all database tables in the correct order."""

import asyncio
import sys

from app.modules.auth.model import OtpCode, Session  # noqa: F401
from app.modules.user.model import User  # noqa: F401

from app.db.session import AsyncSessionLocal
from scripts.seed.seed_users import seed_users


async def seed_all():
    """Seed all database tables in the correct dependency order."""
    print("Starting database seeding...")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        try:
            print("\nStep 1: Seeding users...")
            await seed_users(session)

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
