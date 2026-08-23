"""Split joint activity review statuses by workflow.

Revision ID: 6f5b2c1d9a04
Revises: f7a8b9c0d1e2
Create Date: 2026-08-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "6f5b2c1d9a04"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

audit_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="auditstatusenum",
    schema="app",
    create_type=False,
)
moderation_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "superseded",
    name="moderatestatusenum",
    schema="app",
    create_type=False,
)
verification_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="verificationstatusenum",
    schema="app",
    create_type=False,
)


def upgrade() -> None:
    op.alter_column(
        "joint_activities",
        "preliminary_status",
        schema="app",
        existing_type=audit_status,
        server_default=None,
    )
    op.alter_column(
        "joint_activities",
        "preliminary_status",
        schema="app",
        existing_type=audit_status,
        type_=moderation_status,
        postgresql_using=("preliminary_status::text::app.moderatestatusenum"),
        existing_nullable=False,
    )
    op.alter_column(
        "joint_activities",
        "preliminary_status",
        schema="app",
        existing_type=moderation_status,
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )
    op.alter_column(
        "joint_activities",
        "final_status",
        schema="app",
        existing_type=audit_status,
        type_=verification_status,
        postgresql_using="final_status::text::app.verificationstatusenum",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "joint_activities",
        "preliminary_status",
        schema="app",
        existing_type=moderation_status,
        server_default=None,
    )
    op.alter_column(
        "joint_activities",
        "preliminary_status",
        schema="app",
        existing_type=moderation_status,
        type_=audit_status,
        postgresql_using="preliminary_status::text::app.auditstatusenum",
        existing_nullable=False,
    )
    op.alter_column(
        "joint_activities",
        "preliminary_status",
        schema="app",
        existing_type=audit_status,
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )
    op.alter_column(
        "joint_activities",
        "final_status",
        schema="app",
        existing_type=verification_status,
        type_=audit_status,
        postgresql_using="final_status::text::app.auditstatusenum",
        existing_nullable=True,
    )
