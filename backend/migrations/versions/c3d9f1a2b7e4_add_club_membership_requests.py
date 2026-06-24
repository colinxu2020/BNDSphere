"""Add club membership verification requests.

Revision ID: c3d9f1a2b7e4
Revises: d2f6b1a9c8e0
Create Date: 2026-06-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d9f1a2b7e4"
down_revision: str | Sequence[str] | None = "d2f6b1a9c8e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "club_membership_requests",
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="verificationstatusenum",
            ),
            nullable=False,
        ),
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
            name=op.f("fk_club_membership_requests_applicant_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["club_id"],
            ["app.clubs.id"],
            name=op.f("fk_club_membership_requests_club_id_clubs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verifier_id"],
            ["app.users.id"],
            name=op.f("fk_club_membership_requests_verifier_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_membership_requests")),
        schema="app",
    )
    op.create_index(
        "ix_single_pending_club_membership_request",
        "club_membership_requests",
        ["club_id", "applicant_id"],
        unique=True,
        schema="app",
        postgresql_where=sa.text("verification_status = 'pending'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_single_pending_club_membership_request",
        table_name="club_membership_requests",
        schema="app",
        postgresql_where=sa.text("verification_status = 'pending'"),
    )
    op.drop_table("club_membership_requests", schema="app")
    sa.Enum(name="verificationstatusenum").drop(op.get_bind(), checkfirst=False)
