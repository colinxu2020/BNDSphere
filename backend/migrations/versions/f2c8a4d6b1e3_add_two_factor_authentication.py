"""Two-factor authentication: TOTP, SMS second factor, recovery codes.

Adds the TOTP secret and the two arming timestamps to ``users``, a
``recovery_codes`` table, and the ``two_factor`` value to the verification
purpose enum so a login code cannot be redeemed as a binding or reset code.

Revision ID: f2c8a4d6b1e3
Revises: e5b9c1d7a3f2
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2c8a4d6b1e3"
down_revision: str | Sequence[str] | None = "e5b9c1d7a3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL 12+ allows ADD VALUE inside a transaction as long as the new
    # value is not also *used* in it, which is why nothing below writes a
    # two_factor row.
    op.execute(
        "ALTER TYPE app.verificationpurposeenum ADD VALUE IF NOT EXISTS 'two_factor'",
    )
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.Text(), nullable=True),
        schema="app",
    )
    op.add_column(
        "users",
        sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.add_column(
        "users",
        sa.Column(
            "sms_two_factor_enabled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="app",
    )
    op.create_table(
        "recovery_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_recovery_codes_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recovery_codes"),
        schema="app",
    )
    op.create_index(
        "ix_recovery_codes_user_id",
        "recovery_codes",
        ["user_id"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_codes_user_id", table_name="recovery_codes", schema="app")
    op.drop_table("recovery_codes", schema="app")
    op.drop_column("users", "sms_two_factor_enabled_at", schema="app")
    op.drop_column("users", "totp_confirmed_at", schema="app")
    op.drop_column("users", "totp_secret", schema="app")
    # The enum value is deliberately left in place. PostgreSQL cannot drop one,
    # and recreating the type would mean rewriting every column that uses it —
    # far more risk than an unused label is worth.
