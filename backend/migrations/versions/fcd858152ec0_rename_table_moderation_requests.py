"""rename_table_moderation_requests

Revision ID: fcd858152ec0
Revises: 5eee790bfb8f
Create Date: 2026-05-25 13:48:55.405930

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fcd858152ec0'
down_revision: Union[str, Sequence[str], None] = '5eee790bfb8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Map: old singular table name → new plural table name
_RENAMES = [
    ("club_activity_create_request", "club_activity_create_requests"),
    ("club_activity_update_request", "club_activity_update_requests"),
    ("club_update_request", "club_update_requests"),
    ("user_update_request", "user_update_requests"),
]

# Tables with a partial unique index that needs to be dropped before rename
# and recreated after.  (club_activity_create_request has no such index.)
_INDEXED_TABLES = {
    "club_activity_update_request": {
        "index_name": "ix_single_pending_club_activity_update_request",
        "column": "club_activity_id",
    },
    "club_update_request": {
        "index_name": "ix_single_pending_club_update_request",
        "column": "club_id",
    },
    "user_update_request": {
        "index_name": "ix_single_pending_user_update_request",
        "column": "user_id",
    },
}


def upgrade() -> None:
    """Rename four moderation-request tables from singular to plural."""

    # 1. Drop partial unique indexes on old tables
    for old_name, info in _INDEXED_TABLES.items():
        op.drop_index(
            info["index_name"],
            table_name=old_name,
            schema="app",
            postgresql_where=sa.text("moderate_status = 'pending'"),
        )

    # 2. Rename each table + its PK constraint
    for old_name, new_name in _RENAMES:
        op.rename_table(old_name, new_name, schema="app")
        # PK constraint naming: pk_<table_name>
        op.execute(
            f"ALTER TABLE app.{new_name} RENAME CONSTRAINT pk_{old_name} TO pk_{new_name}"
        )

    # 3. Recreate partial unique indexes on new tables
    for old_name, info in _INDEXED_TABLES.items():
        new_name = dict(_RENAMES)[old_name]
        op.create_index(
            info["index_name"],
            new_name,
            [info["column"]],
            unique=True,
            schema="app",
            postgresql_where=sa.text("moderate_status = 'pending'"),
        )


def downgrade() -> None:
    """Rename four moderation-request tables back from plural to singular."""

    # 1. Drop partial unique indexes on new (plural) tables
    for old_name, info in _INDEXED_TABLES.items():
        new_name = dict(_RENAMES)[old_name]
        op.drop_index(
            info["index_name"],
            table_name=new_name,
            schema="app",
            postgresql_where=sa.text("moderate_status = 'pending'"),
        )

    # 2. Rename each table back + its PK constraint
    for old_name, new_name in _RENAMES:
        op.rename_table(new_name, old_name, schema="app")
        op.execute(
            f"ALTER TABLE app.{old_name} RENAME CONSTRAINT pk_{new_name} TO pk_{old_name}"
        )

    # 3. Recreate partial unique indexes on old (singular) tables
    for old_name, info in _INDEXED_TABLES.items():
        op.create_index(
            info["index_name"],
            old_name,
            [info["column"]],
            unique=True,
            schema="app",
            postgresql_where=sa.text("moderate_status = 'pending'"),
        )
