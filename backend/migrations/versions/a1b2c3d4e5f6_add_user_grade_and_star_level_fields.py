"""add_user_grade_and_star_level_fields

Revision ID: a1b2c3d4e5f6
Revises: fcd858152ec0
Create Date: 2026-05-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "75546634f304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add grade column to users
    op.add_column(
        "users",
        sa.Column("grade", sa.String(length=20), nullable=True),
        schema="app",
    )

    # Add growth story fields to star_level_applications
    op.add_column(
        "star_level_applications",
        sa.Column("growth_story_url", sa.String(length=2083), nullable=True),
        schema="app",
    )
    op.add_column(
        "star_level_applications",
        sa.Column("growth_story_approved", sa.Boolean(), nullable=True),
        schema="app",
    )

    # Add target grade fields to star_level_applications
    op.add_column(
        "star_level_applications",
        sa.Column("target_grade_1", sa.String(length=20), nullable=True),
        schema="app",
    )
    op.add_column(
        "star_level_applications",
        sa.Column("target_grade_2", sa.String(length=20), nullable=True),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("star_level_applications", "target_grade_2", schema="app")
    op.drop_column("star_level_applications", "target_grade_1", schema="app")
    op.drop_column("star_level_applications", "growth_story_approved", schema="app")
    op.drop_column("star_level_applications", "growth_story_url", schema="app")
    op.drop_column("users", "grade", schema="app")
