"""Normalize null proof_files values.

Revision ID: b4f7c8d9e0a1
Revises: 9c1f2a3b4d5e
Create Date: 2026-06-23 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b4f7c8d9e0a1"
down_revision: str | Sequence[str] | None = "9c1f2a3b4d5e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE app.club_general_activity_records
        SET proof_files = '[]'::json
        WHERE proof_files IS NULL OR proof_files::text = 'null'
        """,
    )


def downgrade() -> None:
    pass
