"""initial models"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_initial_models"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


role_enum = sa.Enum(
    "consumer",
    "supplier_owner",
    "supplier_manager",
    "supplier_sales",
    name="role",
)

link_status_enum = sa.Enum("pending", "accepted", "denied", "blocked", name="link_status")
order_status_enum = sa.Enum(
    "pending",
    "accepted",
    "rejected",
    "in_progress",
    "completed",
    name="order_status",
)
complaint_status_enum = sa.Enum("open", "escalated", "resolved", name="complaint_status")
notification_type_enum = sa.Enum("system", "order", "chat", "complaint", name="notification_type")


def upgrade() -> None:
    bind = op.get_bind()
    role_enum.create(bind, checkfirst=True)
    link_status_enum.create(bind, checkfirst=True)
    order_status_enum.create(bind, checkfirst=True)
    complaint_status_enum.create(bind, checkfirst=True)
    notification_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "consumers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("stock_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consumer_id", sa.Integer(), sa.ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", link_status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consumer_id", sa.Integer(), sa.ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", order_status_enum, nullable=False, server_default="pending"),
        sa.Column("total_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price_kzt", sa.Numeric(12, 2), nullable=False),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("consumer_id", sa.Integer(), sa.ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sales_rep_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consumer_id", sa.Integer(), sa.ForeignKey("consumers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sales_rep_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manager_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", complaint_status_enum, nullable=False, server_default="open"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("complaints")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("links")
    op.drop_table("products")
    op.drop_table("consumers")
    op.drop_table("suppliers")
    op.drop_table("users")

    bind = op.get_bind()
    notification_type_enum.drop(bind, checkfirst=True)
    complaint_status_enum.drop(bind, checkfirst=True)
    order_status_enum.drop(bind, checkfirst=True)
    link_status_enum.drop(bind, checkfirst=True)
    role_enum.drop(bind, checkfirst=True)
