"""Independent PostgreSQL sessions pin the archive/moderation lock order."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models import AcademicTerm, Club, ClubActivity, ClubMember, User
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.moderations.club_activity import ClubActivityCreateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.repositories.club import ClubRepository
from app.repositories.club_activity import (
    ClubActivityCreateRequestRepository,
    ClubActivityRepository,
)
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.services.club import ClubService
from app.services.club_activity import ClubActivityCreateRequestService
from app.services.errors import ResourceForbiddenError


class PausingClubRepository(ClubRepository):
    def __init__(
        self,
        db: AsyncSession,
        acquired: asyncio.Event,
        release: asyncio.Event,
    ) -> None:
        super().__init__(db)
        self.acquired = acquired
        self.release = release

    async def get_with_lock(self, id_: int) -> Club | None:
        club = await super().get_with_lock(id_)
        self.acquired.set()
        await self.release.wait()
        return club


class SignallingClubRepository(ClubRepository):
    def __init__(self, db: AsyncSession, attempting: asyncio.Event) -> None:
        super().__init__(db)
        self.attempting = attempting

    async def get(self, id_: int) -> Club | None:
        self.attempting.set()
        return await super().get(id_)

    async def get_with_lock(self, id_: int) -> Club | None:
        self.attempting.set()
        return await super().get_with_lock(id_)


@pytest_asyncio.fixture
async def committed_club_request(
    db_engine: AsyncEngine,
) -> AsyncGenerator[tuple[async_sessionmaker[AsyncSession], dict[str, int]]]:
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        now = datetime.now(UTC)
        term = AcademicTerm(
            term_name=f"archive-race-{uuid4().hex}",
            start_date=now.date() - timedelta(days=1),
            end_date=now.date() + timedelta(days=30),
            is_current=True,
        )
        club = Club(
            name=f"Archive race {uuid4().hex}",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        unused_hash = uuid4().hex
        president = User(
            username=f"archive-race-{uuid4().hex}",
            hashed_password=unused_hash,
        )
        moderator = User(
            username=f"archive-moderator-{uuid4().hex}",
            hashed_password=unused_hash,
        )
        session.add_all([term, club, president, moderator])
        await session.flush()
        member = ClubMember(
            club_id=club.id,
            user_id=president.id,
            membership=ClubMembershipEnum.president,
        )
        request = ClubActivityCreateRequest(
            club_id=club.id,
            requestor_id=president.id,
            name="Late activity",
            description="description",
            location="room",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        session.add_all([member, request])
        await session.flush()
        ids = {
            "club": club.id,
            "request": request.id,
            "president": president.id,
            "moderator": moderator.id,
            "term": term.id,
        }

    try:
        yield maker, ids
    finally:
        async with maker() as session, session.begin():
            await session.execute(
                delete(ClubActivity).where(ClubActivity.club_id == ids["club"]),
            )
            await session.execute(
                delete(ClubActivityCreateRequest).where(
                    ClubActivityCreateRequest.id == ids["request"],
                ),
            )
            await session.execute(
                delete(ClubMember).where(ClubMember.club_id == ids["club"]),
            )
            await session.execute(delete(Club).where(Club.id == ids["club"]))
            await session.execute(
                delete(AcademicTerm).where(AcademicTerm.id == ids["term"]),
            )
            await session.execute(
                delete(User).where(User.id.in_([ids["president"], ids["moderator"]])),
            )


async def test_archive_wins_over_queued_activity_creation_approval(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_club_request
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as archive_session, maker() as review_session:
        president = await archive_session.get(User, ids["president"])
        moderator = await review_session.get(User, ids["moderator"])
        assert president is not None
        assert moderator is not None
        archival = ClubService(
            PausingClubRepository(archive_session, acquired, release),
        )
        review = ClubActivityCreateRequestService(
            ClubActivityCreateRequestRepository(review_session),
            club_repository=SignallingClubRepository(review_session, attempting),
            activity_repository=ClubActivityRepository(review_session),
        )
        archive_task = asyncio.create_task(
            archival.archive_club(ids["club"], president),
        )
        review_task = None
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            review_task = asyncio.create_task(
                review.approve_club_activity_create_request(
                    ids["request"],
                    RequestModeratePublic(
                        moderation_status=ModerationStatusEnum.approved
                    ),
                    moderator,
                ),
            )
            await asyncio.wait_for(attempting.wait(), timeout=5)
            release.set()
            await asyncio.wait_for(archive_task, timeout=5)
            try:
                await asyncio.wait_for(review_task, timeout=5)
            except ResourceForbiddenError:
                pass
            else:
                raise AssertionError("activity approval succeeded after archival")
        finally:
            release.set()
            for task in (archive_task, review_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (archive_task, review_task) if task is not None),
                return_exceptions=True,
            )

    async with maker() as session:
        club = await session.get(Club, ids["club"])
        request = await session.get(ClubActivityCreateRequest, ids["request"])
        count = await session.scalar(
            select(func.count())
            .select_from(ClubActivity)
            .where(ClubActivity.club_id == ids["club"]),
        )
        assert club is not None
        assert club.status == ClubStatusEnum.archived
        assert request is not None
        assert request.moderation_status == ModerationStatusEnum.superseded
        assert count == 0
