"""Database-level membership invariants on ``club_members`` (issue #125).

The service layer already guards "one president per club"; these tests hit the
``db_session`` seam directly so a service bug can never produce a second
president — the partial unique index must reject it.
"""

from typing import ClassVar, TypedDict

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Club, ClubMember, User
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum


class ConfiguredUser(TypedDict):
    headers: dict[str, str]
    user: User


class PresidentFixture(TypedDict):
    club_id: int
    other_club_id: int
    user_ids: dict[str, int]


def _club(name: str) -> Club:
    return Club(
        name=name,
        summary=f"{name} summary",
        description=f"{name} description",
        category=ClubCategoryEnum.information_technology,
        status=ClubStatusEnum.normal,
    )


@pytest_asyncio.fixture(scope="class")
async def setup_president(
    request: pytest.FixtureRequest,
    db_session: AsyncSession,
    setup_class_users: None,
) -> PresidentFixture:
    configured_users: dict[str, ConfiguredUser] = request.cls.configured_users
    user_ids = {name: cu["user"].id for name, cu in configured_users.items()}

    club = _club("Single President Club")
    other_club = _club("Other Club")
    db_session.add_all([club, other_club])
    await db_session.flush()
    club_id, other_club_id = club.id, other_club.id

    db_session.add(
        ClubMember(
            user_id=user_ids["president"],
            club_id=club_id,
            membership=ClubMembershipEnum.president,
        ),
    )
    await db_session.flush()
    # Fold the seeded rows into the outer transaction so the IntegrityError
    # rollback below only rewinds the request-time savepoint.
    await db_session.commit()
    return {"club_id": club_id, "other_club_id": other_club_id, "user_ids": user_ids}


class TestSinglePresidentIndex:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "president", "password": "president-password"},
        {"username": "usurper", "password": "usurper-password"},
        {"username": "vp", "password": "vp-password"},
    ]

    async def test_second_president_in_same_club_is_rejected(
        self,
        db_session: AsyncSession,
        setup_president: PresidentFixture,
    ) -> None:
        db_session.add(
            ClubMember(
                user_id=setup_president["user_ids"]["usurper"],
                club_id=setup_president["club_id"],
                membership=ClubMembershipEnum.president,
            ),
        )

        try:
            with pytest.raises(IntegrityError, match="ix_club_members_club_id"):
                await db_session.flush()
        finally:
            await db_session.rollback()

    async def test_promoting_second_member_to_president_is_rejected(
        self,
        db_session: AsyncSession,
        setup_president: PresidentFixture,
    ) -> None:
        member = ClubMember(
            user_id=setup_president["user_ids"]["usurper"],
            club_id=setup_president["club_id"],
            membership=ClubMembershipEnum.member,
        )
        db_session.add(member)
        await db_session.flush()

        member.membership = ClubMembershipEnum.president
        try:
            with pytest.raises(IntegrityError, match="ix_club_members_club_id"):
                await db_session.flush()
        finally:
            await db_session.rollback()

    async def test_index_is_partial(
        self,
        db_session: AsyncSession,
        setup_president: PresidentFixture,
    ) -> None:
        """Only ``president`` rows are constrained: another club may have its own
        president, and the same club may hold further non-president rows."""
        db_session.add_all(
            [
                ClubMember(
                    user_id=setup_president["user_ids"]["usurper"],
                    club_id=setup_president["other_club_id"],
                    membership=ClubMembershipEnum.president,
                ),
                ClubMember(
                    user_id=setup_president["user_ids"]["vp"],
                    club_id=setup_president["club_id"],
                    membership=ClubMembershipEnum.vice_president,
                ),
            ],
        )
        try:
            await db_session.flush()
        finally:
            await db_session.rollback()
