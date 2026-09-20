"""Bind verification codes to a purpose.

Adds ``verification_codes.purpose`` so a code minted to confirm an address
cannot be redeemed to reset a password. Existing rows are all binding codes,
which is what the server default backfills them as.

Revision ID: e5b9c1d7a3f2
Revises: c7a2e5b8d3f1
Create Date: 2026-09-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5b9c1d7a3f2"
down_revision: str | Sequence[str] | None = "c7a2e5b8d3f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

verification_purpose_enum = sa.Enum(
    "bind",
    "password_reset",
    name="verificationpurposeenum",
)


def upgrade() -> None:
    verification_purpose_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "verification_codes",
        sa.Column(
            "purpose",
            verification_purpose_enum,
            nullable=False,
            # Only here to fill the existing rows; dropped straight after so
            # the application stays the one thing that decides a purpose.
            server_default="bind",
        ),
        schema="app",
    )
    op.alter_column(
        "verification_codes",
        "purpose",
        server_default=None,
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("verification_codes", "purpose", schema="app")
    verification_purpose_enum.drop(op.get_bind(), checkfirst=True)
