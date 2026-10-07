"""Track definitive provider rejection without refunding send budgets."""

import sqlalchemy as sa
from alembic import op

revision = "e8d3c4b5a602"
down_revision = "d9f4b8c2a601"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verification_codes",
        sa.Column(
            "delivery_rejected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("verification_codes", "delivery_rejected", schema="app")
