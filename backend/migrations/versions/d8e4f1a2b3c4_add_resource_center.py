"""Add resource center.

Revision ID: d8e4f1a2b3c4
Revises: 6f5b2c1d9a04
Create Date: 2026-09-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d8e4f1a2b3c4"
down_revision: str | Sequence[str] | None = "6f5b2c1d9a04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resource_files",
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("uploader_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["uploader_id"],
            ["app.users.id"],
            name=op.f("fk_resource_files_uploader_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resource_files")),
        sa.UniqueConstraint("object_key", name=op.f("uq_resource_files_object_key")),
        schema="app",
    )
    op.create_index(
        op.f("ix_resource_files_filename"),
        "resource_files",
        ["filename"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_resource_files_uploader_id"),
        "resource_files",
        ["uploader_id"],
        unique=False,
        schema="app",
    )
    op.create_index(
        op.f("ix_resource_files_created_at"),
        "resource_files",
        ["created_at"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_resource_files_created_at"),
        table_name="resource_files",
        schema="app",
    )
    op.drop_index(
        op.f("ix_resource_files_uploader_id"),
        table_name="resource_files",
        schema="app",
    )
    op.drop_index(
        op.f("ix_resource_files_filename"),
        table_name="resource_files",
        schema="app",
    )
    op.drop_table("resource_files", schema="app")
