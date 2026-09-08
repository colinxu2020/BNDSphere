"""Add club activity check-ins.

Replaces the never-wired ``club_activity_participants`` M2M table (no
endpoint ever wrote to it) with a proper association object that records how
and when each member checked in, per issue #72.

Revision ID: 7d3e9f1c2b6a
Revises: 6f5b2c1d9a04
Create Date: 2026-09-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7d3e9f1c2b6a"
down_revision: str | Sequence[str] | None = "6f5b2c1d9a04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

check_in_method = sa.Enum("manual", "qrcode", name="checkinmethodenum")


def upgrade() -> None:
    op.drop_table("club_activity_participants", schema="app")

    op.create_table(
        "club_activity_check_ins",
        sa.Column("club_activity_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("method", check_in_method, nullable=False),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["club_activity_id"],
            ["app.club_activities.id"],
            name=op.f(
                "fk_club_activity_check_ins_club_activity_id_club_activities",
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["app.users.id"],
            name=op.f("fk_club_activity_check_ins_recorded_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_club_activity_check_ins_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_activity_check_ins")),
        schema="app",
    )
    for column in ("club_activity_id", "user_id"):
        op.create_index(
            op.f(f"ix_club_activity_check_ins_{column}"),
            "club_activity_check_ins",
            [column],
            unique=False,
            schema="app",
        )
    op.create_index(
        "ix_unique_club_activity_check_in_user",
        "club_activity_check_ins",
        ["club_activity_id", "user_id"],
        unique=True,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_unique_club_activity_check_in_user",
        table_name="club_activity_check_ins",
        schema="app",
    )
    for column in ("user_id", "club_activity_id"):
        op.drop_index(
            op.f(f"ix_club_activity_check_ins_{column}"),
            table_name="club_activity_check_ins",
            schema="app",
        )
    op.drop_table("club_activity_check_ins", schema="app")
    check_in_method.drop(op.get_bind(), checkfirst=False)

    op.create_table(
        "club_activity_participants",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("club_activity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["club_activity_id"],
            ["app.club_activities.id"],
            name=op.f(
                "fk_club_activity_participants_club_activity_id_club_activities",
            ),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_club_activity_participants_user_id_users"),
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            "club_activity_id",
            name=op.f("pk_club_activity_participants"),
        ),
        schema="app",
    )
