"""Add club claim requests.

Revision ID: a6d4e2f9c1b7
Revises: f3a7c2d9e1b4
Create Date: 2026-09-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a6d4e2f9c1b7"
down_revision: str | Sequence[str] | None = "f3a7c2d9e1b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

verification_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="verificationstatusenum",
    schema="app",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "club_claim_requests",
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("verifier_id", sa.Integer(), nullable=True),
        sa.Column("verify_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applicant_id", sa.Integer(), nullable=False),
        sa.Column(
            "apply_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["app.users.id"],
            name=op.f("fk_club_claim_requests_applicant_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["club_id"],
            ["app.clubs.id"],
            name=op.f("fk_club_claim_requests_club_id_clubs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verifier_id"],
            ["app.users.id"],
            name=op.f("fk_club_claim_requests_verifier_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_claim_requests")),
        schema="app",
    )
    op.create_index(
        "ix_single_pending_club_claim_request",
        "club_claim_requests",
        ["club_id", "applicant_id"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("verification_status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_single_pending_club_claim_request",
        table_name="club_claim_requests",
        schema="app",
        postgresql_where=sa.text("verification_status = 'pending'"),
    )
    op.drop_table("club_claim_requests", schema="app")
