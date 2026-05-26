"""rename_enums

Revision ID: e70c1b0c1e5c
Revises: 0d0985e9223c
Create Date: 2026-05-25 13:13:05.866684

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e70c1b0c1e5c'
down_revision: Union[str, Sequence[str], None] = '0d0985e9223c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename enum labels to match updated Python enum definitions."""

    # RoleEnum: scf = "staff of club federation" → federation_staff = "federation_staff"
    # PG enum stores the member name 'scf', needs to become 'federation_staff'.
    op.execute(
        "ALTER TYPE app.roleenum RENAME VALUE 'scf' TO 'federation_staff'"
    )

    # ClubMembershipEnum: vice = "vice president" → vice_president = "vice_president"
    # PG enum stores the value 'vice president', needs to become 'vice_president'.
    op.execute(
        "ALTER TYPE app.clubmembershipenum RENAME VALUE 'vice president' TO 'vice_president'"
    )

    # GeneralActivityLevelEnum: federation = "club_federation" → club_federation = "club_federation"
    # PG enum already stores 'club_federation' — no change needed.


def downgrade() -> None:
    """Reverse enum label renames."""

    op.execute(
        "ALTER TYPE app.roleenum RENAME VALUE 'federation_staff' TO 'scf'"
    )

    op.execute(
        "ALTER TYPE app.clubmembershipenum RENAME VALUE 'vice_president' TO 'vice president'"
    )
