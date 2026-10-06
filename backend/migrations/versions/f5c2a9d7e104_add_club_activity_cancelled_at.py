"""Record cancellation of club activities.

Revision ID: f5c2a9d7e104
Revises: c6e8a2d4f901
"""

import sqlalchemy as sa

from alembic import op

revision = "f5c2a9d7e104"
down_revision = "c6e8a2d4f901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "club_activities",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("club_activities", "cancelled_at", schema="app")
