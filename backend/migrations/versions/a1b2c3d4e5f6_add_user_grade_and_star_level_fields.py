"""add_user_grade_and_star_level_fields

Revision ID: a1b2c3d4e5f6
Revises: 75546634f304
Create Date: 2026-05-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "75546634f304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_USER_GRADE_ENUM_VALUES = (
    "grade_7",
    "grade_8",
    "grade_9",
    "grade_10",
    "grade_11",
    "grade_12",
    "inter_grade_9",
    "inter_grade_10",
    "inter_grade_11",
    "inter_grade_12",
)


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE app.usergradeenum AS ENUM ("
        "'grade_7','grade_8','grade_9','grade_10','grade_11','grade_12',"
        "'inter_grade_9','inter_grade_10','inter_grade_11','inter_grade_12'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    usergrade = sa.Enum(
        *_USER_GRADE_ENUM_VALUES,
        name="usergradeenum",
        schema="app",
        create_type=False,
    )

    op.add_column(
        "users",
        sa.Column("grade", usergrade, nullable=True),
        schema="app",
    )

    op.add_column(
        "star_level_applications",
        sa.Column("growth_story_url", sa.Text(), nullable=True),
        schema="app",
    )
    op.add_column(
        "star_level_applications",
        sa.Column("growth_story_approved", sa.Boolean(), nullable=True),
        schema="app",
    )

    op.add_column(
        "star_level_applications",
        sa.Column("target_grade_1", usergrade, nullable=True),
        schema="app",
    )
    op.add_column(
        "star_level_applications",
        sa.Column("target_grade_2", usergrade, nullable=True),
        schema="app",
    )

    op.add_column(
        "user_update_requests",
        sa.Column("grade", usergrade, nullable=True),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("user_update_requests", "grade", schema="app")
    op.drop_column("star_level_applications", "target_grade_2", schema="app")
    op.drop_column("star_level_applications", "target_grade_1", schema="app")
    op.drop_column("star_level_applications", "growth_story_approved", schema="app")
    op.drop_column("star_level_applications", "growth_story_url", schema="app")
    op.drop_column("users", "grade", schema="app")
    op.execute("DROP TYPE IF EXISTS app.usergradeenum")
