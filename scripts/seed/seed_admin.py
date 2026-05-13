"""Seed admin_users table with a default iCare admin account."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.model import AdminUser
from app.utils.hashing import hash_password

_ADMIN_EMAIL = "admin@icare.kz"
_ADMIN_PASSWORD = "Admin123!"
_ADMIN_NAME = "iCare Admin"


async def seed_admin(session: AsyncSession) -> AdminUser:
    result = await session.execute(
        select(AdminUser).where(AdminUser.email == _ADMIN_EMAIL)
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"  Admin already exists: {_ADMIN_EMAIL}")
        return existing

    admin = AdminUser(
        email=_ADMIN_EMAIL,
        password_hash=hash_password(_ADMIN_PASSWORD),
        name=_ADMIN_NAME,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    await session.commit()

    print(f"  Created admin: {_ADMIN_EMAIL} / {_ADMIN_PASSWORD}")
    print("  ⚠️  CHANGE THIS PASSWORD BEFORE PRODUCTION")
    return admin


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal

    async def main():
        async with AsyncSessionLocal() as session:
            await seed_admin(session)

    asyncio.run(main())
