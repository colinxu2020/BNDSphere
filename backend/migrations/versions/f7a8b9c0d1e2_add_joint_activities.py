"""Add joint activities.

Revision ID: f7a8b9c0d1e2
Revises: e1a4b6c8d0f2
Create Date: 2026-08-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "e1a4b6c8d0f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

audit_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="auditstatusenum",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "joint_activities",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initiator_club_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "preliminary_status",
            audit_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("preliminary_auditor_id", sa.Integer(), nullable=True),
        sa.Column(
            "preliminary_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("archive_text", sa.Text(), nullable=True),
        sa.Column(
            "archive_files",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("final_status", audit_status, nullable=True),
        sa.Column("final_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("final_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_auditor_id", sa.Integer(), nullable=True),
        sa.Column("final_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("academic_term_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["academic_term_id"],
            ["app.academic_terms.id"],
            name=op.f("fk_joint_activities_academic_term_id_academic_terms"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["app.users.id"],
            name=op.f("fk_joint_activities_created_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["final_auditor_id"],
            ["app.users.id"],
            name=op.f("fk_joint_activities_final_auditor_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["initiator_club_id"],
            ["app.clubs.id"],
            name=op.f("fk_joint_activities_initiator_club_id_clubs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["preliminary_auditor_id"],
            ["app.users.id"],
            name=op.f("fk_joint_activities_preliminary_auditor_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_joint_activities")),
        schema="app",
    )
    for column in (
        "created_by_user_id",
        "ends_at",
        "final_status",
        "initiator_club_id",
        "name",
        "preliminary_status",
        "starts_at",
    ):
        op.create_index(
            op.f(f"ix_joint_activities_{column}"),
            "joint_activities",
            [column],
            unique=False,
            schema="app",
        )

    op.create_table(
        "joint_activity_participations",
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), nullable=False),
        sa.Column("registered_by_user_id", sa.Integer(), nullable=False),
        sa.Column("is_initiator", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["app.joint_activities.id"],
            name=op.f(
                "fk_joint_activity_participations_activity_id_joint_activities",
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["club_id"],
            ["app.clubs.id"],
            name=op.f("fk_joint_activity_participations_club_id_clubs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["registered_by_user_id"],
            ["app.users.id"],
            name=op.f(
                "fk_joint_activity_participations_registered_by_user_id_users",
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_joint_activity_participations"),
        ),
        schema="app",
    )
    for column in ("activity_id", "club_id", "registered_by_user_id"):
        op.create_index(
            op.f(f"ix_joint_activity_participations_{column}"),
            "joint_activity_participations",
            [column],
            unique=False,
            schema="app",
        )
    op.create_index(
        "ix_unique_joint_activity_club_participation",
        "joint_activity_participations",
        ["activity_id", "club_id"],
        unique=True,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_unique_joint_activity_club_participation",
        table_name="joint_activity_participations",
        schema="app",
    )
    for column in ("registered_by_user_id", "club_id", "activity_id"):
        op.drop_index(
            op.f(f"ix_joint_activity_participations_{column}"),
            table_name="joint_activity_participations",
            schema="app",
        )
    op.drop_table("joint_activity_participations", schema="app")

    for column in (
        "starts_at",
        "preliminary_status",
        "name",
        "initiator_club_id",
        "final_status",
        "ends_at",
        "created_by_user_id",
    ):
        op.drop_index(
            op.f(f"ix_joint_activities_{column}"),
            table_name="joint_activities",
            schema="app",
        )
    op.drop_table("joint_activities", schema="app")
