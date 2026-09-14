"""Merge activity check-in and resource center migration heads.

Revision ID: 2a7c9e4b1f60
Revises: 7d3e9f1c2b6a, d8e4f1a2b3c4
Create Date: 2026-09-13 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "2a7c9e4b1f60"
down_revision: str | Sequence[str] | None = (
    "7d3e9f1c2b6a",
    "d8e4f1a2b3c4",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
