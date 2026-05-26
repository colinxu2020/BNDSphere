"""rename_moderate_mixin

Rename column moderate_status → moderation_status in all four
moderation-request tables, and update the partial unique indexes
that reference it.

Revision ID: 75546634f304
Revises: 8b9b0e11982e
Create Date: 2026-05-25 16:11:50.029507

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '75546634f304'
down_revision: Union[str, Sequence[str], None] = '8b9b0e11982e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that have a partial unique index on moderate_status.
# (club_activity_create_requests has the column but no index.)
_INDEXED = [
    ("club_activity_update_requests", "ix_single_pending_club_activity_update_request", "club_activity_id"),
    ("club_update_requests", "ix_single_pending_club_update_request", "club_id"),
    ("user_update_requests", "ix_single_pending_user_update_request", "user_id"),
]

# All four tables that carry the column.
_ALL_TABLES = [
    "club_activity_create_requests",
    "club_activity_update_requests",
    "club_update_requests",
    "user_update_requests",
]


def upgrade() -> None:
    """Rename column moderate_status → moderation_status."""

    # 1. Drop partial unique indexes on old column name
    for table, index_name, _col in _INDEXED:
        op.drop_index(
            index_name,
            table_name=table,
            schema="app",
            postgresql_where=sa.text("moderate_status = 'pending'"),
        )

    # 2. Rename the column in every table
    for table in _ALL_TABLES:
        op.alter_column(
            table,
            "moderate_status",
            new_column_name="moderation_status",
            schema="app",
        )

    # 3. Recreate partial unique indexes on new column name
    for table, index_name, col in _INDEXED:
        op.create_index(
            index_name,
            table,
            [col],
            unique=True,
            schema="app",
            postgresql_where=sa.text("moderation_status = 'pending'"),
        )


def downgrade() -> None:
    """Rename column moderation_status → moderate_status (reverse)."""

    # 1. Drop partial unique indexes on new column name
    for table, index_name, _col in _INDEXED:
        op.drop_index(
            index_name,
            table_name=table,
            schema="app",
            postgresql_where=sa.text("moderation_status = 'pending'"),
        )

    # 2. Rename the column back
    for table in _ALL_TABLES:
        op.alter_column(
            table,
            "moderation_status",
            new_column_name="moderate_status",
            schema="app",
        )

    # 3. Recreate partial unique indexes on old column name
    for table, index_name, col in _INDEXED:
        op.create_index(
            index_name,
            table,
            [col],
            unique=True,
            schema="app",
            postgresql_where=sa.text("moderate_status = 'pending'"),
        )
