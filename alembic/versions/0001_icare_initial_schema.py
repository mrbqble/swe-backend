"""icare-initial-schema

Revision ID: 0001
Revises:
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that existed in the old SCP schema (drop order respects FK dependencies)
OLD_TABLES = [
    "chat_message_attachments",
    "chat_messages",
    "complaints",
    "order_items",
    "orders",
    "chat_sessions",
    "links",
    "products",
    "supplier_staff",
    "consumers",
    "suppliers",
    "notifications",
    "users",
]

# Old enum types to drop
OLD_ENUMS = [
    "linkstatus",
    "orderstatus",
    "complaintstatus",
]


def upgrade() -> None:
    # Drop old SCP tables (CASCADE handles FK deps)
    for table in OLD_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

    # Drop old enum types
    for enum in OLD_ENUMS:
        op.execute(f'DROP TYPE IF EXISTS "{enum}" CASCADE')

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("patronymic", sa.String(100), nullable=True),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("email_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("ref_code", sa.String(20), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_root", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status_tier", sa.String(50), nullable=False, server_default=sa.text("'partner'")),
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("team_volume", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("payout_method", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("ref_code"),
    )
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_ref_code", "users", ["ref_code"])

    # Create otp_codes table
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_codes_phone", "otp_codes", ["phone"])

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("device_info", sa.JSON(), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("otp_codes")
    op.drop_table("users")
