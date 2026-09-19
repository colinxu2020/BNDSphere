"""Update club categories.

Revision ID: f3a7c2d9e1b4
Revises: c8e4f2a1b7d9
Create Date: 2026-09-19 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f3a7c2d9e1b4"
down_revision: str | Sequence[str] | None = "c8e4f2a1b7d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE app.clubcategoryenum_new AS ENUM (
            'stage_design',
            'information_technology',
            'charity',
            'performing_arts',
            'social_science',
            'handicraft',
            'literature_publishing',
            'business',
            'art_design',
            'campus_management',
            'natural_science',
            'language_learning',
            'sports',
            'anime',
            'film_news_media'
        )
        """,
    )
    op.execute(
        """
        ALTER TABLE app.clubs
        ALTER COLUMN category TYPE app.clubcategoryenum_new
        USING (
            CASE category::text
                WHEN 'sports' THEN 'sports'
                WHEN 'humanity' THEN 'social_science'
                WHEN 'arts' THEN 'art_design'
                WHEN 'science' THEN 'natural_science'
                WHEN 'charity' THEN 'charity'
                WHEN 'business' THEN 'business'
                WHEN 'campus' THEN 'campus_management'
                WHEN 'other' THEN 'social_science'
            END
        )::app.clubcategoryenum_new
        """,
    )
    op.execute("DROP TYPE app.clubcategoryenum")
    op.execute("ALTER TYPE app.clubcategoryenum_new RENAME TO clubcategoryenum")


def downgrade() -> None:
    op.execute(
        """
        CREATE TYPE app.clubcategoryenum_old AS ENUM (
            'sports',
            'humanity',
            'arts',
            'science',
            'charity',
            'business',
            'campus',
            'other'
        )
        """,
    )
    op.execute(
        """
        ALTER TABLE app.clubs
        ALTER COLUMN category TYPE app.clubcategoryenum_old
        USING (
            CASE category::text
                WHEN 'stage_design' THEN 'arts'
                WHEN 'information_technology' THEN 'science'
                WHEN 'charity' THEN 'charity'
                WHEN 'performing_arts' THEN 'arts'
                WHEN 'social_science' THEN 'humanity'
                WHEN 'handicraft' THEN 'arts'
                WHEN 'literature_publishing' THEN 'humanity'
                WHEN 'business' THEN 'business'
                WHEN 'art_design' THEN 'arts'
                WHEN 'campus_management' THEN 'campus'
                WHEN 'natural_science' THEN 'science'
                WHEN 'language_learning' THEN 'humanity'
                WHEN 'sports' THEN 'sports'
                WHEN 'anime' THEN 'arts'
                WHEN 'film_news_media' THEN 'arts'
            END
        )::app.clubcategoryenum_old
        """,
    )
    op.execute("DROP TYPE app.clubcategoryenum")
    op.execute("ALTER TYPE app.clubcategoryenum_old RENAME TO clubcategoryenum")
