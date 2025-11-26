"""add_company_logo_to_suppliers

Revision ID: 7b5e3f9e3b2d
Revises: 3c9aac1d990c
Create Date: 2025-11-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b5e3f9e3b2d"
# Chain this migration after the notifications metadata migration to avoid multiple heads
down_revision: Union[str, None] = "56c28d2a8840"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company_logo column to suppliers table."""
    op.add_column("suppliers", sa.Column(
        "company_logo", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove company_logo column from suppliers table."""
    op.drop_column("suppliers", "company_logo")
