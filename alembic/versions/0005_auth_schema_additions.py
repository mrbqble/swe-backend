"""auth-schema-additions

Adds columns needed for the full auth state machine:
- users: welcomed, deletion_scheduled_at, deletion_cancel_token, language,
         consent_version, consent_recorded_at
- otp_codes: purpose, resend_count, locked_until
- email_confirmations: email_change_count, locked_until
- new table: ref_code_history

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-15 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users additions ───────────────────────────────────────────────────────
    op.add_column("users", sa.Column("welcomed", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("users", sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("deletion_cancel_token", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("language", sa.String(5), nullable=False, server_default="ru"))
    op.add_column("users", sa.Column("consent_version", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_deletion_cancel_token", "users", ["deletion_cancel_token"], unique=True)

    # ── otp_codes additions ───────────────────────────────────────────────────
    op.add_column("otp_codes", sa.Column("purpose", sa.String(20), nullable=True))
    op.add_column("otp_codes", sa.Column("resend_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("otp_codes", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    # ── email_confirmations additions ─────────────────────────────────────────
    op.add_column("email_confirmations", sa.Column("email_change_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("email_confirmations", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    # ── ref_code_history (new table) ──────────────────────────────────────────
    op.create_table(
        "ref_code_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("old_ref_code", sa.String(20), nullable=False),
        sa.Column("new_ref_code", sa.String(20), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_ref_code_history_user_id", "ref_code_history", ["user_id"])


def downgrade() -> None:
    op.drop_table("ref_code_history")

    op.drop_column("email_confirmations", "locked_until")
    op.drop_column("email_confirmations", "email_change_count")

    op.drop_column("otp_codes", "locked_until")
    op.drop_column("otp_codes", "resend_count")
    op.drop_column("otp_codes", "purpose")

    op.drop_index("ix_users_deletion_cancel_token", table_name="users")
    op.drop_column("users", "consent_recorded_at")
    op.drop_column("users", "consent_version")
    op.drop_column("users", "language")
    op.drop_column("users", "deletion_cancel_token")
    op.drop_column("users", "deletion_scheduled_at")
    op.drop_column("users", "welcomed")
