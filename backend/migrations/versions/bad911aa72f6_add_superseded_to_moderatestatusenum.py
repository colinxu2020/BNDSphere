"""add superseded to moderatestatusenum

Revision ID: bad911aa72f6
Revises: 09734045808e
Create Date: 2026-05-05 16:20:41.897219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bad911aa72f6'
down_revision: Union[str, Sequence[str], None] = '09734045808e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE moderatestatusenum ADD VALUE IF NOT EXISTS 'superseded'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
