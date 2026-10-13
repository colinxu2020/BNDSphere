"""Unify general activity and star level reviews with VerificationMixin.

Revision ID: a9d6e3f2b8c1
Revises: f1c5a9e2b403
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a9d6e3f2b8c1"
down_revision: str | Sequence[str] | None = "f1c5a9e2b403"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("club_general_activity_records", "star_level_applications")
_AUDIT_STATUS = postgresql.ENUM(
    "pending", "approved", "rejected", name="auditstatusenum", schema="app",
    create_type=False,
)
_VERIFICATION_STATUS = postgresql.ENUM(
    "pending", "approved", "rejected", name="verificationstatusenum", schema="app",
    create_type=False,
)


def upgrade() -> None:
    for table in _TABLES:
        op.alter_column(
            table,
            "audit_status",
            new_column_name="verification_status",
            existing_type=_AUDIT_STATUS,
            type_=_VERIFICATION_STATUS,
            postgresql_using="audit_status::text::app.verificationstatusenum",
            existing_nullable=False,
            schema="app",
        )
        op.alter_column(
            table, "auditor_id", new_column_name="verifier_id", schema="app",
        )
        op.execute(
            f"ALTER TABLE app.{table} RENAME CONSTRAINT "
            f"fk_{table}_auditor_id_users TO fk_{table}_verifier_id_users",
        )
        # AuditMixin never tracked review times; don't invent historical dates.
        op.add_column(
            table, sa.Column("verify_at", sa.DateTime(timezone=True), nullable=True),
            schema="app",
        )
    _AUDIT_STATUS.drop(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    _AUDIT_STATUS.create(op.get_bind(), checkfirst=False)
    for table in _TABLES:
        op.drop_column(table, "verify_at", schema="app")
        op.execute(
            f"ALTER TABLE app.{table} RENAME CONSTRAINT "
            f"fk_{table}_verifier_id_users TO fk_{table}_auditor_id_users",
        )
        op.alter_column(
            table, "verifier_id", new_column_name="auditor_id", schema="app",
        )
        op.alter_column(
            table,
            "verification_status",
            new_column_name="audit_status",
            existing_type=_VERIFICATION_STATUS,
            type_=_AUDIT_STATUS,
            postgresql_using="verification_status::text::app.auditstatusenum",
            existing_nullable=False,
            schema="app",
        )
