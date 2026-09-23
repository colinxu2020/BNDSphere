import asyncio
from typing import ClassVar
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import Club, ClubMember, User
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from tests.test_auth import ConfiguredUser


@pytest.mark.parametrize("isolation", ["READ COMMITTED", "REPEATABLE READ"])
async def test_concurrent_capacity_increases(
    db_engine: AsyncEngine, isolation: str
) -> None:
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        club = Club(
            name=f"Concurrent VP {uuid4().hex}",
            summary="s",
            description="d",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        users = [
            User(username=uuid4().hex, hashed_password=uuid4().hex) for _ in range(3)
        ]
        session.add_all([club, *users])
        await session.flush()
        club_id, user_ids = club.id, [user.id for user in users]
        session.add(
            ClubMember(
                club_id=club_id,
                user_id=user_ids[0],
                membership=ClubMembershipEnum.vice_president,
            )
        )
        await session.commit()
    try:
        async with db_engine.connect() as first, db_engine.connect() as second:
            await first.execution_options(isolation_level=isolation)
            await second.execution_options(isolation_level=isolation)
            # Establish both snapshots before either transaction adds a VP.
            await first.execute(select(Club.id).where(Club.id == club_id))
            await second.execute(select(Club.id).where(Club.id == club_id))
            statement = insert(ClubMember).values(
                club_id=club_id, membership=ClubMembershipEnum.vice_president
            )
            await first.execute(statement.values(user_id=user_ids[1]))
            competing = asyncio.create_task(
                second.execute(statement.values(user_id=user_ids[2]))
            )
            await first.commit()
            try:
                with pytest.raises(DBAPIError) as exc_info:
                    await asyncio.wait_for(competing, timeout=10)
                assert getattr(exc_info.value.orig, "sqlstate", None) == (
                    "23514" if isolation == "READ COMMITTED" else "40001"
                )
            finally:
                await second.rollback()
            count = await first.scalar(
                select(func.count())
                .select_from(ClubMember)
                .where(
                    ClubMember.club_id == club_id,
                    ClubMember.membership == ClubMembershipEnum.vice_president,
                )
            )
            assert count == 2
    finally:
        async with db_engine.begin() as cleanup:
            await cleanup.execute(
                delete(ClubMember).where(ClubMember.club_id == club_id)
            )
            await cleanup.execute(delete(Club).where(Club.id == club_id))
            await cleanup.execute(delete(User).where(User.id.in_(user_ids)))


class TestVicePresidentLimit:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": name}
        for name in ("president", "vice1", "vice2", "member", "extra")
    ]
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    @pytest.fixture(scope="class")
    def user_ids(self, setup_class_users: None) -> dict[str, int]:
        return {name: value["user"].id for name, value in self.configured_users.items()}

    @pytest_asyncio.fixture
    async def club_id(self, db_session: AsyncSession, user_ids: dict[str, int]) -> int:
        club = Club(
            name=f"VP limit {uuid4().hex}",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        db_session.add(club)
        await db_session.flush()
        club_id = club.id
        for name, membership in [
            ("president", "president"),
            ("vice1", "vice_president"),
            ("vice2", "vice_president"),
            ("member", "member"),
        ]:
            db_session.add(
                ClubMember(
                    club_id=club_id,
                    user_id=user_ids[name],
                    membership=ClubMembershipEnum(membership),
                )
            )
        await db_session.commit()
        return club_id

    @pytest.mark.parametrize(
        ("name", "role", "status"),
        [
            ("member", "vice_president", 409),
            ("vice1", "vice_president", 200),
            ("vice1", "member", 200),
            ("vice1", "president", 200),
            ("member", "president", 200),
        ],
    )
    async def test_role_changes_at_capacity(
        self,
        client: AsyncClient,
        club_id: int,
        name: str,
        role: str,
        status: int,
        user_ids: dict[str, int],
    ) -> None:
        user_id = user_ids[name]
        response = await client.patch(
            f"/clubs/{club_id}/members/{user_id}",
            json={"membership": role},
            headers=self.configured_users["president"]["headers"],
        )
        assert response.status_code == status
        if status == 409:
            assert response.json()["error_code"] == "VICE_PRESIDENT_LIMIT_REACHED"
        else:
            assert response.json()["membership"] == role

    @pytest.mark.parametrize("insert", [True, False])
    async def test_database_rejects_third_vice_president(
        self,
        db_session: AsyncSession,
        club_id: int,
        user_ids: dict[str, int],
        *,
        insert: bool,
    ) -> None:
        extra_id = user_ids["extra"]
        member_id = user_ids["member"]
        with pytest.raises(IntegrityError, match="vice_president_limit"):  # noqa: PT012
            async with db_session.begin_nested():
                if insert:
                    db_session.add(
                        ClubMember(
                            club_id=club_id,
                            user_id=extra_id,
                            membership=ClubMembershipEnum.vice_president,
                        )
                    )
                    await db_session.flush()
                else:
                    await db_session.execute(
                        update(ClubMember)
                        .where(
                            ClubMember.club_id == club_id,
                            ClubMember.user_id == member_id,
                        )
                        .values(membership=ClubMembershipEnum.vice_president)
                    )

    async def test_demoting_frees_a_slot(
        self, client: AsyncClient, club_id: int, user_ids: dict[str, int]
    ) -> None:
        headers = self.configured_users["president"]["headers"]
        demoted = await client.patch(
            f"/clubs/{club_id}/members/{user_ids['vice1']}",
            json={"membership": "member"},
            headers=headers,
        )
        assert demoted.status_code == 200
        promoted = await client.patch(
            f"/clubs/{club_id}/members/{user_ids['member']}",
            json={"membership": "vice_president"},
            headers=headers,
        )
        assert promoted.status_code == 200
        assert promoted.json()["membership"] == "vice_president"

    async def test_moving_a_vice_president_to_full_club_is_rejected(
        self, db_session: AsyncSession, club_id: int, user_ids: dict[str, int]
    ) -> None:
        other = Club(
            name=f"Other VP {uuid4().hex}",
            summary="s",
            description="d",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        db_session.add(other)
        await db_session.flush()
        membership = ClubMember(
            club_id=other.id,
            user_id=user_ids["extra"],
            membership=ClubMembershipEnum.vice_president,
        )
        db_session.add(membership)
        await db_session.flush()
        with pytest.raises(IntegrityError, match="vice_president_limit"):
            async with db_session.begin_nested():
                await db_session.execute(
                    update(ClubMember)
                    .where(ClubMember.id == membership.id)
                    .values(club_id=club_id)
                )
