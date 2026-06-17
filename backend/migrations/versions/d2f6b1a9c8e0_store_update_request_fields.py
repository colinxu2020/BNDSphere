"""Store update request fields.

Revision ID: d2f6b1a9c8e0
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2f6b1a9c8e0"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPDATE_REQUEST_TABLES = (
    "club_update_requests",
    "club_activity_update_requests",
    "user_update_requests",
)


def upgrade() -> None:
    for table in _UPDATE_REQUEST_TABLES:
        op.add_column(
            table,
            sa.Column(
                "update_fields",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            schema="app",
        )

    op.create_check_constraint(
        op.f("ck_club_activity_create_requests_check_start_end_time"),
        "club_activity_create_requests",
        "end_time > start_time",
        schema="app",
    )
    op.create_check_constraint(
        op.f("ck_club_activity_update_requests_check_start_end_time"),
        "club_activity_update_requests",
        "end_time IS NULL OR start_time IS NULL OR end_time > start_time",
        schema="app",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_club_activity_update_requests_check_start_end_time"),
        "club_activity_update_requests",
        schema="app",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_club_activity_create_requests_check_start_end_time"),
        "club_activity_create_requests",
        schema="app",
        type_="check",
    )

    for table in _UPDATE_REQUEST_TABLES:
        op.drop_column(table, "update_fields", schema="app")
