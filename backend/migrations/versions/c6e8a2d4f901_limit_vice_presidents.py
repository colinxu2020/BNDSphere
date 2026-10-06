"""Limit each club to two vice presidents.

Revision ID: c6e8a2d4f901
Revises: b7e2d4a9c3f1
"""

import sqlalchemy as sa

from alembic import op

revision = "c6e8a2d4f901"
down_revision = "b7e2d4a9c3f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Keep validation and trigger installation atomic with respect to writers.
    conn.execute(sa.text("LOCK TABLE app.club_members IN SHARE ROW EXCLUSIVE MODE"))
    offending = conn.execute(sa.text(
        "SELECT club_id FROM app.club_members WHERE membership = 'vice_president' "
        "GROUP BY club_id HAVING count(*) > 2 ORDER BY club_id"
    )).scalars().all()
    if offending:
        raise RuntimeError(
            f"Cannot enforce vice president limit; clubs with more than two: {list(offending)}. "
            "Fix memberships manually and retry the migration."
        )
    # Freeze the limit in the migration; importing live constants would change
    # the meaning of this historical migration on a future deployment.
    op.execute("""
        CREATE FUNCTION app.enforce_vice_president_limit() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.membership <> 'vice_president' THEN
                RETURN NEW;
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.membership = 'vice_president' AND OLD.club_id = NEW.club_id THEN
                    RETURN NEW;
                END IF;
            END IF;
            -- Serialize capacity increases on the club row. A no-op update
            -- also creates a write conflict under repeatable-read snapshots,
            -- where a lock alone would leave the count using stale data.
            UPDATE app.clubs SET id = id WHERE id = NEW.club_id;
            IF (SELECT count(*) FROM app.club_members
                WHERE club_id = NEW.club_id AND membership = 'vice_president'
                  AND id IS DISTINCT FROM NEW.id) >= 2 THEN
                RAISE EXCEPTION 'vice_president_limit: club % already has two vice presidents', NEW.club_id
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_club_members_vice_president_limit';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER enforce_vice_president_limit
        BEFORE INSERT OR UPDATE OF membership, club_id ON app.club_members
        FOR EACH ROW EXECUTE FUNCTION app.enforce_vice_president_limit()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER enforce_vice_president_limit ON app.club_members")
    op.execute("DROP FUNCTION app.enforce_vice_president_limit()")
