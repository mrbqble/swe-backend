from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from app.core.security import Role
from app.schemas.base import ORMModel


class UserCreate(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: Role


class UserRead(ORMModel):
    id: int
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime


class SupplierRead(ORMModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime


class ConsumerRead(ORMModel):
    id: int
    org_name: str
    created_at: datetime


class SupplierCreate(ORMModel):
    user_id: int
    name: str = Field(min_length=1, max_length=255)


class ConsumerCreate(ORMModel):
    user_id: int
    org_name: str = Field(min_length=1, max_length=255)
