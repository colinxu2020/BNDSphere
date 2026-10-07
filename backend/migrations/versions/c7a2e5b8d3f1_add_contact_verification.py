"""Add contact verification (email + SMS one-time codes).

Adds ``verification_codes``, plus the columns on ``users`` that a confirmed
code writes to: ``phone`` and the two ``*_verified_at`` timestamps. Email was
already stored but never confirmed, so ``email_verified_at`` starts NULL for
every existing row — which is accurate: nobody has proved one yet.

Revision ID: c7a2e5b8d3f1
Revises: b3f7d1c4a9e2
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7a2e5b8d3f1"
down_revision: str | Sequence[str] | None = "b3f7d1c4a9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

verification_channel_enum = sa.Enum(
    "email",
    "sms",
    name="verificationchannelenum",
)


def upgrade() -> None:
    op.create_table(
        "verification_codes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", verification_channel_enum, nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name=op.f("fk_verification_codes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_codes")),
        schema="app",
    )
    # Latest live code for an account on one channel, and the per-account
    # send budget.
    op.create_index(
        "ix_verification_codes_user_id_channel_created_at",
        "verification_codes",
        ["user_id", "channel", "created_at"],
        unique=False,
        schema="app",
    )
    # Per-target send budget, across accounts.
    op.create_index(
        "ix_verification_codes_target_created_at",
        "verification_codes",
        ["target", "created_at"],
        unique=False,
        schema="app",
    )
    # Deployment-wide daily SMS budget, and the retention sweep.
    op.create_index(
        "ix_verification_codes_channel_created_at",
        "verification_codes",
        ["channel", "created_at"],
        unique=False,
        schema="app",
    )

    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.add_column(
        "users",
        sa.Column("phone", sa.String(length=16), nullable=True),
        schema="app",
    )
    op.add_column(
        "users",
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="app",
    )
    op.create_unique_constraint(
        op.f("uq_users_phone"),
        "users",
        ["phone"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_users_phone"), "users", schema="app", type_="unique")
    op.drop_column("users", "phone_verified_at", schema="app")
    op.drop_column("users", "phone", schema="app")
    op.drop_column("users", "email_verified_at", schema="app")

    op.drop_index(
        "ix_verification_codes_channel_created_at",
        table_name="verification_codes",
        schema="app",
    )
    op.drop_index(
        "ix_verification_codes_target_created_at",
        table_name="verification_codes",
        schema="app",
    )
    op.drop_index(
        "ix_verification_codes_user_id_channel_created_at",
        table_name="verification_codes",
        schema="app",
    )
    op.drop_table("verification_codes", schema="app")
    # The table is gone, so nothing references the type any more; dropping it
    # keeps a downgrade+upgrade cycle from failing on "type already exists".
    verification_channel_enum.drop(op.get_bind(), checkfirst=True)
