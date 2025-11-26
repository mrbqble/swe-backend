"""add_unlinked_status_to_link_status_enum

Revision ID: 6730a24ca95b
Revises: 7b5e3f9e3b2d
Create Date: 2025-11-26 21:03:44.104527

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6730a24ca95b'
down_revision: Union[str, None] = '7b5e3f9e3b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'UNLINKED' value to the linkstatus enum (uppercase to match existing enum values)
    # Note: The initial migration created the enum with uppercase values ('PENDING', 'ACCEPTED', etc.)
    # SQLAlchemy's Enum(LinkStatus) uses the enum's .value property which is lowercase ('unlinked'),
    # but the database enum has uppercase values. SQLAlchemy should handle the conversion automatically.
    # However, to be safe and match the existing pattern, we add uppercase 'UNLINKED'.
    # If lowercase 'unlinked' already exists, we'll add uppercase as well.
    op.execute("ALTER TYPE linkstatus ADD VALUE 'UNLINKED'")


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # This would require recreating the enum type, which is complex and risky
    # For now, we'll leave the enum value in place
    # If removal is absolutely necessary, it would require:
    # 1. Create new enum without 'unlinked'
    # 2. Update all columns to use new enum
    # 3. Drop old enum
    # 4. Rename new enum to old name
    pass
