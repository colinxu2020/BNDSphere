"""Add homepage activity and announcement fields.

Revision ID: 9c1f2a3b4d5e
Revises: d2f6b1a9c8e0
Create Date: 2026-06-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c1f2a3b4d5e"
down_revision: str | Sequence[str] | None = "d2f6b1a9c8e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "general_activities",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.add_column(
        "general_activities",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.add_column(
        "general_activities",
        sa.Column("poster_uri", sa.Text(), nullable=True),
        schema="app",
    )
    op.add_column(
        "general_activities",
        sa.Column("article_url", sa.Text(), nullable=True),
        schema="app",
    )
    op.create_index(
        op.f("ix_general_activities_starts_at"),
        "general_activities",
        ["starts_at"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_general_activities_ends_at"),
        "general_activities",
        ["ends_at"],
        unique=False,
        schema="app",
    )

    op.create_table(
        "announcements",
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcements")),
        schema="app",
    )
    op.create_index(
        op.f("ix_announcements_title"),
        "announcements",
        ["title"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_announcements_starts_at"),
        "announcements",
        ["starts_at"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_announcements_ends_at"),
        "announcements",
        ["ends_at"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_announcements_is_active"),
        "announcements",
        ["is_active"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_announcements_is_active"), table_name="announcements", schema="app")
    op.drop_index(op.f("ix_announcements_ends_at"), table_name="announcements", schema="app")
    op.drop_index(op.f("ix_announcements_starts_at"), table_name="announcements", schema="app")
    op.drop_index(op.f("ix_announcements_title"), table_name="announcements", schema="app")
    op.drop_table("announcements", schema="app")

    op.drop_index(
        op.f("ix_general_activities_ends_at"),
        table_name="general_activities",
        schema="app",
    )
    op.drop_index(
        op.f("ix_general_activities_starts_at"),
        table_name="general_activities",
        schema="app",
    )
    op.drop_column("general_activities", "article_url", schema="app")
    op.drop_column("general_activities", "poster_uri", schema="app")
    op.drop_column("general_activities", "ends_at", schema="app")
    op.drop_column("general_activities", "starts_at", schema="app")
