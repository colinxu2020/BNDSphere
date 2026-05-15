"""empty message

Revision ID: 47bb575057ea
Revises: d1549c8fd5a9
Create Date: 2026-05-15 14:10:19.003026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47bb575057ea'
down_revision: Union[str, Sequence[str], None] = 'd1549c8fd5a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "academic_term",
    "activities",
    "activity_conditions",
    "activity_participators",
    "club_general_activity_records",
    "club_members",
    "club_tags",
    "club_update_requests",
    "clubs",
    "general_activities",
    "record_condition_details",
    "star_level_applications",
    "tags",
    "users",
]

def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE SCHEMA IF NOT EXISTS app')

    for table in TABLES:
        op.execute(f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA app')


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(TABLES):
        op.execute(f'ALTER TABLE IF EXISTS app."{table}" SET SCHEMA public')
