"""phase4-schema

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ip_too ────────────────────────────────────────────────────────────────
    op.create_table(
        "ip_too",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("iin_bin", sa.String(12), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_ip_too_user_id", "ip_too", ["user_id"])
    op.create_index("ix_ip_too_iin_bin", "ip_too", ["iin_bin"], unique=True)

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer,
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider_payment_id", sa.String(255), nullable=True, unique=True),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])

    # ── suggestions ───────────────────────────────────────────────────────────
    op.create_table(
        "suggestions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_suggestions_user_id", "suggestions", ["user_id"])


def downgrade() -> None:
    op.drop_table("suggestions")
    op.drop_table("payments")
    op.drop_table("ip_too")
