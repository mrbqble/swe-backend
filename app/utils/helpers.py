"""API helper functions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.model import User


async def get_user_by_phone(phone: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: int, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
