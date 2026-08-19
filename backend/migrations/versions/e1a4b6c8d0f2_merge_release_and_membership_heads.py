"""Merge release and club-membership migration heads.

Revision ID: e1a4b6c8d0f2
Revises: b4f7c8d9e0a1, c3d9f1a2b7e4
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "e1a4b6c8d0f2"
down_revision: str | Sequence[str] | None = (
    "b4f7c8d9e0a1",
    "c3d9f1a2b7e4",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
