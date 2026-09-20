"""Add user sessions.

Backs cookie-based login. A session is a server-side row addressed by an
opaque token, replacing the self-contained JWT that could not be revoked
before its own expiry. Only the SHA-256 of the token is stored.

Revision ID: b3f7d1c4a9e2
Revises: a6d4e2f9c1b7
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3f7d1c4a9e2"
down_revision: str | Sequence[str] | None = "a6d4e2f9c1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_user_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_sessions_token_hash")),
        schema="app",
    )
    op.create_index(
        op.f("ix_user_sessions_user_id"),
        "user_sessions",
        ["user_id"],
        unique=False,
        schema="app",
    )
    # Serves the retention sweep, which deletes everything past its expiry.
    op.create_index(
        op.f("ix_user_sessions_expires_at"),
        "user_sessions",
        ["expires_at"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_sessions_expires_at"),
        table_name="user_sessions",
        schema="app",
    )
    op.drop_index(
        op.f("ix_user_sessions_user_id"),
        table_name="user_sessions",
        schema="app",
    )
    op.drop_table("user_sessions", schema="app")
