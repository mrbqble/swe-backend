"""make_complaint_manager_id_nullable

Revision ID: c12624820ae7
Revises: 6730a24ca95b
Create Date: 2025-11-26 21:34:21.944132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c12624820ae7'
down_revision: Union[str, None] = '6730a24ca95b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make manager_id nullable in complaints table
    op.alter_column('complaints', 'manager_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Make manager_id non-nullable again (note: this will fail if there are NULL values)
    op.alter_column('complaints', 'manager_id',
                    existing_type=sa.Integer(),
                    nullable=False)

