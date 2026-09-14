"""Add resource deletion state.

Revision ID: c9b1d4e7f2a6
Revises: 2a7c9e4b1f60
Create Date: 2026-09-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9b1d4e7f2a6"
down_revision: str | Sequence[str] | None = "2a7c9e4b1f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "resource_files",
        sa.Column(
            "deletion_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column(
        "resource_files",
        "deletion_requested_at",
        schema="app",
    )
