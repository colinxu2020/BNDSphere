"""rename_table_academic_term

Revision ID: 5eee790bfb8f
Revises: e70c1b0c1e5c
Create Date: 2026-05-25 13:29:33.415733

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5eee790bfb8f'
down_revision: Union[str, Sequence[str], None] = 'e70c1b0c1e5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables referencing academic_term via FK
_FK_TABLES = [
    {
        "table": "general_activities",
        "fk_old": "fk_general_activities_academic_term_id_academic_term",
        "fk_new": "fk_general_activities_academic_term_id_academic_terms",
    },
    {
        "table": "star_level_applications",
        "fk_old": "fk_star_level_applications_academic_term_id_academic_term",
        "fk_new": "fk_star_level_applications_academic_term_id_academic_terms",
    },
    {
        "table": "club_activities",
        "fk_old": "fk_club_activities_academic_term_id_academic_term",
        "fk_new": "fk_club_activities_academic_term_id_academic_terms",
    },
]


def upgrade() -> None:
    """Rename academic_term → academic_terms."""

    # 1. Drop FK constraints that reference academic_term
    for entry in _FK_TABLES:
        op.drop_constraint(
            entry["fk_old"], entry["table"], schema="app", type_="foreignkey"
        )

    # 2. Drop partial unique index on old table
    op.drop_index(
        "ix_only_one_current",
        table_name="academic_term",
        schema="app",
        postgresql_where=sa.text("is_current = true"),
    )

    # 3. Rename table
    op.rename_table("academic_term", "academic_terms", schema="app")

    # 4. Rename PK and unique constraint to match new table name
    op.execute("ALTER INDEX app.pk_academic_term RENAME TO pk_academic_terms")
    op.execute(
        "ALTER TABLE app.academic_terms RENAME CONSTRAINT uq_academic_term_term_name TO uq_academic_terms_term_name"
    )

    # 5. Recreate FK constraints pointing to the new table
    for entry in _FK_TABLES:
        op.create_foreign_key(
            entry["fk_new"],
            entry["table"],
            "academic_terms",
            ["academic_term_id"],
            ["id"],
            source_schema="app",
            referent_schema="app",
        )

    # 6. Recreate partial unique index on new table
    op.create_index(
        "ix_only_one_current",
        "academic_terms",
        ["is_current"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("is_current IS true"),
    )


def downgrade() -> None:
    """Rename academic_terms → academic_term (reverse)."""

    # 1. Drop FK constraints (new names)
    for entry in _FK_TABLES:
        op.drop_constraint(
            entry["fk_new"], entry["table"], schema="app", type_="foreignkey"
        )

    # 2. Drop partial unique index on new table
    op.drop_index(
        "ix_only_one_current",
        table_name="academic_terms",
        schema="app",
        postgresql_where=sa.text("is_current IS true"),
    )

    # 3. Rename table back
    op.rename_table("academic_terms", "academic_term", schema="app")

    # 4. Rename PK and unique constraint back
    op.execute("ALTER INDEX app.pk_academic_terms RENAME TO pk_academic_term")
    op.execute(
        "ALTER TABLE app.academic_term RENAME CONSTRAINT uq_academic_terms_term_name TO uq_academic_term_term_name"
    )

    # 5. Recreate FK constraints (old names)
    for entry in _FK_TABLES:
        op.create_foreign_key(
            entry["fk_old"],
            entry["table"],
            "academic_term",
            ["academic_term_id"],
            ["id"],
            source_schema="app",
            referent_schema="app",
        )

    # 6. Recreate partial unique index on old table
    op.create_index(
        "ix_only_one_current",
        "academic_term",
        ["is_current"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("is_current = true"),
    )
