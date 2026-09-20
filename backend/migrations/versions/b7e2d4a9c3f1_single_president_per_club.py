"""Enforce at most one president per club.

Validates existing data first: if any club already has more than one
``president`` row the migration fails and names the offending clubs, so the
data is fixed by hand rather than silently rewritten. Then adds a partial
unique index on ``club_members.club_id`` restricted to president rows.

Revision ID: b7e2d4a9c3f1
Revises: a6d4e2f9c1b7
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e2d4a9c3f1"
down_revision: str | Sequence[str] | None = "a6d4e2f9c1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_club_members_club_id"
PRESIDENT_ONLY = sa.text("membership = 'president'")


class MultiplePresidentsError(RuntimeError):
    def __init__(self, club_ids: list[int]) -> None:
        super().__init__(
            "Cannot enforce single president per club: these clubs have more "
            f"than one 'president' row in app.club_members: {club_ids}. "
            "Fix the data manually, then re-run the migration.",
        )


def upgrade() -> None:
    conn = op.get_bind()
    offending = conn.execute(
        sa.text(
            "SELECT club_id FROM app.club_members "
            "WHERE membership = 'president' "
            "GROUP BY club_id HAVING count(*) > 1 "
            "ORDER BY club_id",
        ),
    ).scalars().all()
    if offending:
        raise MultiplePresidentsError(list(offending))

    op.create_index(
        INDEX_NAME,
        "club_members",
        ["club_id"],
        unique=True,
        schema="app",
        postgresql_where=PRESIDENT_ONLY,
    )


def downgrade() -> None:
    op.drop_index(
        INDEX_NAME,
        table_name="club_members",
        schema="app",
        postgresql_where=PRESIDENT_ONLY,
    )
