import importlib
from datetime import date
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import MetaData, Table, create_engine, insert, select, text

from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubCategoryEnum
from app.models.general_activity import GeneralActivity, GeneralActivityLevelEnum
from app.models.user import User
from tests.conftest import SUPERUSER_TEST_DB_URL


def test_verification_migration_preserves_reviews_and_roundtrips() -> None:
    migration = importlib.import_module(
        "migrations.versions.a9d6e3f2b8c1_unify_audit_with_verification",
    )
    engine = create_engine(
        SUPERUSER_TEST_DB_URL.replace("postgresql://", "postgresql+psycopg://"),
    )
    try:
        with engine.connect() as connection, connection.begin():
            # A SAVEPOINT keeps DDL and seeded rows local to this test.
            savepoint = connection.begin_nested()
            try:
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                    verifier_id = connection.scalar(
                        insert(User)
                        .values(
                            username=uuid4().hex,
                            hashed_password=uuid4().hex,
                        )
                        .returning(User.id),
                    )
                    club_ids = []
                    term_id = connection.scalar(
                        insert(AcademicTerm)
                        .values(
                            term_name=uuid4().hex,
                            start_date=date(2026, 9, 1),
                            end_date=date(2027, 1, 1),
                            is_current=False,
                        )
                        .returning(AcademicTerm.id),
                    )
                    for status in ("pending", "approved", "rejected"):
                        club_id = connection.scalar(
                            insert(Club)
                            .values(
                                name=uuid4().hex,
                                summary="s",
                                description="d",
                                category=ClubCategoryEnum.natural_science,
                            )
                            .returning(Club.id),
                        )
                        club_ids.append(club_id)
                        activity_id = connection.scalar(
                            insert(GeneralActivity)
                            .values(
                                name=uuid4().hex,
                                description="d",
                                level=GeneralActivityLevelEnum.school,
                                academic_term_id=term_id,
                            )
                            .returning(GeneralActivity.id),
                        )
                        values = {
                            "club_id": club_id,
                            "activity_id": activity_id,
                            "term_id": term_id,
                            "status": status,
                            "verifier_id": None if status == "pending" else verifier_id,
                        }
                        connection.execute(
                            text(
                                "INSERT INTO app.club_general_activity_records "
                                "(club_id, activity_id, participation_type, "
                                "requested_score, final_score, proof_files, "
                                "audit_status, auditor_id) VALUES "
                                "(:club_id, :activity_id, 'participate_only', "
                                "5, 5, '[]', "
                                ":status, :verifier_id)",
                            ),
                            values,
                        )
                        connection.execute(
                            text(
                                "INSERT INTO app.star_level_applications "
                                "(club_id, academic_term_id, audit_status, auditor_id) "
                                "VALUES (:club_id, :term_id, :status, :verifier_id)",
                            ),
                            values,
                        )
                    migration.upgrade()
                    for table in (
                        "club_general_activity_records",
                        "star_level_applications",
                    ):
                        reflected = Table(
                            table,
                            MetaData(),
                            schema="app",
                            autoload_with=connection,
                        )
                        rows = connection.execute(
                            select(
                                reflected.c.verification_status,
                                reflected.c.verifier_id,
                                reflected.c.verify_at,
                            )
                            .where(reflected.c.club_id.in_(club_ids))
                            .order_by(reflected.c.club_id),
                        ).all()
                        assert rows == [
                            ("pending", None, None),
                            ("approved", verifier_id, None),
                            ("rejected", verifier_id, None),
                        ]
                        assert (
                            connection.scalar(
                                text(
                                    "SELECT udt_name FROM information_schema.columns "
                                    "WHERE table_schema = 'app' "
                                    "AND table_name = :table "
                                    "AND column_name = 'verification_status'",
                                ),
                                {"table": table},
                            )
                            == "verificationstatusenum"
                        )
                    assert (
                        connection.scalar(
                            text(
                                "SELECT to_regtype('app.auditstatusenum')",
                            )
                        )
                        is None
                    )
                    migration.downgrade()
                    for table in (
                        "club_general_activity_records",
                        "star_level_applications",
                    ):
                        reflected = Table(
                            table,
                            MetaData(),
                            schema="app",
                            autoload_with=connection,
                        )
                        rows = connection.execute(
                            select(reflected.c.audit_status, reflected.c.auditor_id)
                            .where(reflected.c.club_id.in_(club_ids))
                            .order_by(reflected.c.club_id),
                        ).all()
                        assert rows == [
                            ("pending", None),
                            ("approved", verifier_id),
                            ("rejected", verifier_id),
                        ]
                    migration.upgrade()
            finally:
                savepoint.rollback()
    finally:
        engine.dispose()
