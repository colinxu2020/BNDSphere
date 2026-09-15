"""Add legal consent records.

Revision ID: c8e4f2a1b7d9
Revises: e4d1a8b7c6f5
Create Date: 2026-09-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8e4f2a1b7d9"
down_revision: str | Sequence[str] | None = "e4d1a8b7c6f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

legal_document_enum = sa.Enum(
    "privacy_policy",
    "user_agreement",
    "cross_border_transfer_consent",
    name="legaldocumentenum",
)


def upgrade() -> None:
    op.create_table(
        "legal_consents",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document", legal_document_enum, nullable=False),
        sa.Column("document_version", sa.Date(), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_legal_consents_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_consents")),
        sa.UniqueConstraint(
            "user_id",
            "document",
            "document_version",
            name=op.f(
                "uq_legal_consents_user_id_document_document_version",
            ),
        ),
        schema="app",
    )
    op.create_index(
        "ix_legal_consents_document_document_version",
        "legal_consents",
        ["document", "document_version"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legal_consents_document_document_version",
        table_name="legal_consents",
        schema="app",
    )
    op.drop_table("legal_consents", schema="app")
    legal_document_enum.drop(op.get_bind(), checkfirst=False)
