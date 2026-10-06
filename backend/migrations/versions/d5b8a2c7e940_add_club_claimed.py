"""Add the club claimed flag and backfill it from existing presidents.

Revision ID: d5b8a2c7e940
Revises: c6e8a2d4f901
Create Date: 2026-10-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5b8a2c7e940"
down_revision: str | Sequence[str] | None = "c6e8a2d4f901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "clubs",
        sa.Column("claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="app",
    )
    op.execute(
        sa.text(
            "UPDATE app.clubs SET claimed = EXISTS ("
            "SELECT 1 FROM app.club_members "
            "WHERE club_members.club_id = clubs.id "
            "AND club_members.membership = 'president')"
        )
    )


def downgrade() -> None:
    op.drop_column("clubs", "claimed", schema="app")
