"""merge all heads

Revision ID: 50a930fe728d
Revises: 47bb575057ea, bad911aa72f6
Create Date: 2026-05-15 14:48:57.876361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50a930fe728d'
down_revision: Union[str, Sequence[str], None] = ('47bb575057ea', 'bad911aa72f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
