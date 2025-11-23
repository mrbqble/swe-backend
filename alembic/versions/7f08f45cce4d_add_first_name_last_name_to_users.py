"""add_first_name_last_name_to_users

Revision ID: 7f08f45cce4d
Revises: 0320da79bb1c
Create Date: 2025-01-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f08f45cce4d"
down_revision: str | None = "0320da79bb1c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add first_name and last_name columns to users table
    op.add_column(
        "users",
        sa.Column(
            "first_name", sa.String(length=100), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_name", sa.String(length=100), nullable=False, server_default=""
        ),
    )

    # Remove server defaults after adding columns (they were just for migration)
    op.alter_column("users", "first_name", server_default=None)
    op.alter_column("users", "last_name", server_default=None)


def downgrade() -> None:
    # Remove first_name and last_name columns from users table
    # Using IF EXISTS to handle cases where columns might not exist
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_name")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS first_name")
