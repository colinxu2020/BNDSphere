"""Drop SMS verification: phone columns and the channel dimension.

Phone numbers were only ever set by answering an SMS code, so with the SMS
channel gone the ``users.phone``/``users.phone_verified_at`` columns have no
writer left. With email the only remaining channel, ``verification_codes``
loses its ``channel`` column and the single-value enum behind it, and the
channel-qualified budget indexes collapse to their email equivalents.

Revision ID: f1c5a9e2b403
Revises: e8d3c4b5a602
Create Date: 2026-10-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1c5a9e2b403"
down_revision: str | Sequence[str] | None = "e8d3c4b5a602"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

verification_channel_enum = sa.Enum(
    "email",
    "sms",
    name="verificationchannelenum",
)


def upgrade() -> None:
    op.drop_constraint(op.f("uq_users_phone"), "users", schema="app", type_="unique")
    op.drop_column("users", "phone_verified_at", schema="app")
    op.drop_column("users", "phone", schema="app")

    # Remove SMS rows while the channel value is still available: with the
    # discriminator gone they would be read as email records, letting a
    # recent SMS throttle email sends or supersede a live email code.
    op.execute("DELETE FROM app.verification_codes WHERE channel = 'sms'")
    op.drop_index(
        "ix_verification_codes_user_id_channel_created_at",
        table_name="verification_codes",
        schema="app",
    )
    op.drop_index(
        "ix_verification_codes_channel_created_at",
        table_name="verification_codes",
        schema="app",
    )
    op.drop_column("verification_codes", "channel", schema="app")
    # Nothing references the type any more; drop it so a downgrade+upgrade
    # cycle does not fail on "type already exists".
    verification_channel_enum.drop(op.get_bind(), checkfirst=True)
    op.create_index(
        "ix_verification_codes_user_id_created_at",
        "verification_codes",
        ["user_id", "created_at"],
        unique=False,
        schema="app",
    )
    # prune_before() deletes by created_at alone; the dropped channel-prefixed
    # index was its only usable access path.
    op.create_index(
        "ix_verification_codes_created_at",
        "verification_codes",
        ["created_at"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_verification_codes_created_at",
        table_name="verification_codes",
        schema="app",
    )
    op.drop_index(
        "ix_verification_codes_user_id_created_at",
        table_name="verification_codes",
        schema="app",
    )
    # The type was dropped on upgrade with no remaining users; recreate it
    # before the column that depends on it.
    verification_channel_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "verification_codes",
        sa.Column("channel", verification_channel_enum, nullable=True),
        schema="app",
    )
    # Only email rows survive the upgrade; SMS rows are not recoverable.
    op.execute("UPDATE app.verification_codes SET channel = 'email'")
    op.alter_column("verification_codes", "channel", nullable=False, schema="app")
    op.create_index(
        "ix_verification_codes_channel_created_at",
        "verification_codes",
        ["channel", "created_at"],
        unique=False,
        schema="app",
    )
    op.create_index(
        "ix_verification_codes_user_id_channel_created_at",
        "verification_codes",
        ["user_id", "channel", "created_at"],
        unique=False,
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
