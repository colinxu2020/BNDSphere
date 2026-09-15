"""Add login attempts.

Backs the per-account failed-login throttle and a short-lived audit trail of
login attempts (username, source IP, outcome). ``username`` is the submitted
string rather than a foreign key so attempts against nonexistent accounts are
recorded too.

Revision ID: b1c2d3e4f5a6
Revises: 7d3e9f1c2b6a
Create Date: 2026-09-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "7d3e9f1c2b6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempts")),
        schema="app",
    )
    # (username, created_at) serves the failure-count lookup and its ordering;
    # the standalone created_at index serves the retention sweep.
    op.create_index(
        op.f("ix_login_attempts_created_at"),
        "login_attempts",
        ["created_at"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_login_attempts_username_created_at"),
        "login_attempts",
        ["username", "created_at"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_login_attempts_username_created_at"),
        table_name="login_attempts",
        schema="app",
    )
    op.drop_index(
        op.f("ix_login_attempts_created_at"),
        table_name="login_attempts",
        schema="app",
    )
    op.drop_table("login_attempts", schema="app")
