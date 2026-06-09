"""Seed users table with a root partner for development."""

import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.model import OtpCode, Session  # noqa: F401 — register mappers
from app.modules.user.model import User
from app.utils.hashing import hash_password


async def seed_users(session: AsyncSession) -> dict[str, User]:
    """Create root partner user if it doesn't exist.

    Returns:
        Dict mapping phone to User object.
    """
    root_phone = "+70000000000"

    result = await session.execute(select(User).where(User.phone == root_phone))
    existing = result.scalar_one_or_none()

    if existing:
        print(f"Root user already exists: {root_phone} (ref_code: {existing.ref_code})")
        return {root_phone: existing}

    root_user = User(
        phone=root_phone,
        password_hash=hash_password("RootPass1!"),
        first_name="Root",
        last_name="Partner",
        dob=date(1990, 1, 1),
        email="root@icare.dev",
        ref_code="ICR000000",
        is_root=True,
        status_tier="partner",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(root_user)
    await session.flush()
    await session.commit()

    print(f"Created root user: {root_phone} (ref_code: ICR000000, password: RootPass1!)")
    return {root_phone: root_user}


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal

    async def main():
        async with AsyncSessionLocal() as session:
            await seed_users(session)

    asyncio.run(main())
