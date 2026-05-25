"""rename_table_club_activity_participators

Revision ID: ce5b0aba4d25
Revises: fcd858152ec0
Create Date: 2026-05-25 15:03:58.155350

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ce5b0aba4d25'
down_revision: Union[str, Sequence[str], None] = 'fcd858152ec0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename club_activity_participators → club_activity_participants."""

    op.rename_table(
        "club_activity_participators",
        "club_activity_participants",
        schema="app",
    )

    op.execute(
        "ALTER INDEX app.pk_club_activity_participators "
        "RENAME TO pk_club_activity_participants"
    )


def downgrade() -> None:
    """Rename club_activity_participants → club_activity_participators (reverse)."""

    op.rename_table(
        "club_activity_participants",
        "club_activity_participators",
        schema="app",
    )

    op.execute(
        "ALTER INDEX app.pk_club_activity_participants "
        "RENAME TO pk_club_activity_participators"
    )
