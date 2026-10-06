import importlib
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, select, update

from app.models import Club, ClubMember, User
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from tests.conftest import SUPERUSER_TEST_DB_URL


def test_migration_roundtrip_and_dirty_data_rejection() -> None:
    migration = importlib.import_module(
        "migrations.versions.c6e8a2d4f901_limit_vice_presidents"
    )
    engine = create_engine(
        SUPERUSER_TEST_DB_URL.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                    migration.upgrade()
                    migration.downgrade()
                    club_id = connection.scalar(
                        insert(Club)
                        .values(
                            name=f"Migration VP {uuid4().hex}",
                            summary="s",
                            description="d",
                            category=ClubCategoryEnum.natural_science,
                            status=ClubStatusEnum.normal,
                        )
                        .returning(Club.id)
                    )
                    member_ids = []
                    for _ in range(3):
                        user_id = connection.scalar(
                            insert(User)
                            .values(
                                username=uuid4().hex,
                                hashed_password=uuid4().hex,
                            )
                            .returning(User.id)
                        )
                        member_ids.append(
                            connection.scalar(
                                insert(ClubMember)
                                .values(
                                    club_id=club_id,
                                    user_id=user_id,
                                    membership=ClubMembershipEnum.vice_president,
                                )
                                .returning(ClubMember.id)
                            )
                        )
                    with pytest.raises(RuntimeError, match=str(club_id)):
                        migration.upgrade()
                    # Validation must not silently alter any memberships.
                    assert (
                        len(
                            connection.scalars(
                                select(ClubMember.id).where(
                                    ClubMember.club_id == club_id,
                                    ClubMember.membership
                                    == ClubMembershipEnum.vice_president,
                                )
                            ).all()
                        )
                        == 3
                    )
                    connection.execute(
                        update(ClubMember)
                        .where(ClubMember.id == member_ids[0])
                        .values(membership=ClubMembershipEnum.member)
                    )
                    migration.upgrade()
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
