"""add_metadata_to_notifications

Revision ID: 56c28d2a8840
Revises: 3c9aac1d990c
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '56c28d2a8840'
down_revision: Union[str, None] = '3c9aac1d990c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metadata JSONB column to notifications table
    op.add_column('notifications', sa.Column(
        'metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove metadata column
    op.drop_column('notifications', 'metadata')
