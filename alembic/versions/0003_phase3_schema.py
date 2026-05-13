"""phase3-schema

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: new columns ────────────────────────────────────────────────────
    op.add_column("users", sa.Column("ref_code_changed", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("users", sa.Column("push_token", sa.String(255), nullable=True))

    # ── orders: is_cancelled ──────────────────────────────────────────────────
    op.add_column("orders", sa.Column("is_cancelled", sa.Boolean, nullable=False, server_default="false"))

    # ── email_confirmations ───────────────────────────────────────────────────
    op.create_table(
        "email_confirmations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_email_confirmations_user_id", "email_confirmations", ["user_id"])

    # ── admin_users ───────────────────────────────────────────────────────────
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)

    # ── admin_actions ─────────────────────────────────────────────────────────
    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "admin_id",
            sa.Integer,
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.Integer, nullable=True),
        sa.Column("before_data", JSONB, nullable=True),
        sa.Column("after_data", JSONB, nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_admin_actions_admin_id", "admin_actions", ["admin_id"])
    op.create_index("ix_admin_actions_target", "admin_actions", ["target_type", "target_id"])

    # ── faq ───────────────────────────────────────────────────────────────────
    op.create_table(
        "faq",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_ru", sa.Text, nullable=False),
        sa.Column("question_kz", sa.Text, nullable=True),
        sa.Column("answer_ru", sa.Text, nullable=False),
        sa.Column("answer_kz", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default="false"),
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


def downgrade() -> None:
    op.drop_table("faq")
    op.drop_table("admin_actions")
    op.drop_table("admin_users")
    op.drop_table("email_confirmations")
    op.drop_column("orders", "is_cancelled")
    op.drop_column("users", "push_token")
    op.drop_column("users", "ref_code_changed")
