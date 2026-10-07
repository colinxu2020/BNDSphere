"""Merge cookie sessions with master and enforce email alias uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "d9f4b8c2a601"
down_revision = ("c7a2e5b8d3f1", "d5b8a2c7e940")
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE app.users IN SHARE ROW EXCLUSIVE MODE"))
    duplicate_ids = connection.execute(sa.text("""
        SELECT array_agg(id ORDER BY id) FROM app.users
        WHERE email IS NOT NULL GROUP BY lower(email) HAVING count(*) > 1
    """)).scalars().all()
    if duplicate_ids:
        raise RuntimeError(
            f"Email aliases belong to multiple accounts: {duplicate_ids}. "
            "Resolve those addresses manually and retry the migration."
        )
    op.create_index(
        "uq_users_email_lower", "users", [sa.text("lower(email)")],
        unique=True, schema="app",
    )


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users", schema="app")
