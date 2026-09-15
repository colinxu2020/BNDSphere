"""Merge login attempt and resource center migration heads.

Revision ID: e4d1a8b7c6f5
Revises: b1c2d3e4f5a6, c9b1d4e7f2a6
Create Date: 2026-09-15 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "e4d1a8b7c6f5"
down_revision: str | Sequence[str] | None = (
    "b1c2d3e4f5a6",
    "c9b1d4e7f2a6",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
