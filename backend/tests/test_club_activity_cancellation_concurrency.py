"""Real PostgreSQL row-lock races for club activity cancellation."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models import (
    AcademicTerm,
    Club,
    ClubActivity,
    ClubActivityCheckIn,
    ClubMember,
    User,
)
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.moderations.club_activity import ClubActivityUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.repositories.club_activity import (
    ClubActivityRepository,
    ClubActivityUpdateRequestRepository,
)
from app.repositories.club_activity_check_in import ClubActivityCheckInRepository
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.services.club_activity import (
    ClubActivityService,
    ClubActivityUpdateRequestService,
)
from app.services.club_activity_check_in import ClubActivityCheckInService
from app.services.errors import ClubActivityCancelledError, ResourceForbiddenError


class PausingActivityRepository(ClubActivityRepository):
    def __init__(
        self,
        db: AsyncSession,
        acquired: asyncio.Event,
        release: asyncio.Event,
    ) -> None:
        super().__init__(db)
        self.acquired = acquired
        self.release = release

    async def get_with_lock(self, id_: int) -> ClubActivity | None:
        activity = await super().get_with_lock(id_)
        self.acquired.set()
        await self.release.wait()
        return activity


class SignallingActivityRepository(ClubActivityRepository):
    def __init__(self, db: AsyncSession, attempting: asyncio.Event) -> None:
        super().__init__(db)
        self.attempting = attempting

    async def get_with_lock(self, id_: int) -> ClubActivity | None:
        self.attempting.set()
        return await super().get_with_lock(id_)


@pytest_asyncio.fixture
async def committed_activity(
    db_engine: AsyncEngine,
) -> AsyncGenerator[tuple[async_sessionmaker[AsyncSession], dict[str, int]]]:
    maker = async_sessionmaker(db_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        now = datetime.now(UTC)
        term = AcademicTerm(
            term_name="cancel-race-term",
            start_date=now.date() - timedelta(days=1),
            end_date=now.date() + timedelta(days=30),
        )
        club = Club(
            name="Cancellation race club",
            summary="summary",
            description="description",
            category=ClubCategoryEnum.natural_science,
            status=ClubStatusEnum.normal,
        )
        member = User(
            username="cancellation-race-member",
            hashed_password=uuid4().hex,
        )
        moderator = User(
            username="cancellation-race-moderator",
            hashed_password=uuid4().hex,
        )
        session.add_all([term, club, member, moderator])
        await session.flush()
        activity = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Original name",
            description="description",
            location="location",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        session.add_all(
            [
                ClubMember(
                    club_id=club.id,
                    user_id=member.id,
                    membership=ClubMembershipEnum.member,
                ),
                activity,
            ],
        )
        await session.flush()
        request = ClubActivityUpdateRequest(
            club_activity_id=activity.id,
            requestor_id=member.id,
            name="Proposed name",
            update_fields=["name"],
        )
        session.add(request)
        await session.flush()
        ids = {
            "term": term.id,
            "club": club.id,
            "member": member.id,
            "moderator": moderator.id,
            "activity": activity.id,
            "request": request.id,
        }

    try:
        yield maker, ids
    finally:
        async with maker() as session, session.begin():
            await session.execute(
                delete(ClubActivityCheckIn).where(
                    ClubActivityCheckIn.club_activity_id == ids["activity"],
                ),
            )
            await session.execute(
                delete(ClubActivityUpdateRequest).where(
                    ClubActivityUpdateRequest.id == ids["request"],
                ),
            )
            await session.execute(
                delete(ClubMember).where(ClubMember.club_id == ids["club"]),
            )
            await session.execute(
                delete(ClubActivity).where(ClubActivity.id == ids["activity"]),
            )
            await session.execute(delete(Club).where(Club.id == ids["club"]))
            await session.execute(
                delete(AcademicTerm).where(AcademicTerm.id == ids["term"]),
            )
            await session.execute(
                delete(User).where(User.id.in_([ids["member"], ids["moderator"]])),
            )


async def test_cancel_wins_over_queued_update_approval(
    committed_activity: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_activity
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as cancel_session, maker() as review_session:
        cancellation = ClubActivityService(
            PausingActivityRepository(cancel_session, acquired, release),
        )
        review = ClubActivityUpdateRequestService(
            ClubActivityUpdateRequestRepository(review_session),
            SignallingActivityRepository(review_session, attempting),
        )
        moderator = await review_session.get(User, ids["moderator"])
        assert moderator is not None
        cancel_task = asyncio.create_task(
            cancellation.cancel_club_activity(ids["club"], ids["activity"]),
        )
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            review_task = asyncio.create_task(
                review.approve_club_activity_update_request(
                    ids["request"],
                    RequestModeratePublic(
                        moderation_status=ModerationStatusEnum.approved
                    ),
                    moderator,
                ),
            )
            await asyncio.wait_for(attempting.wait(), timeout=5)
        finally:
            release.set()
        await asyncio.wait_for(cancel_task, timeout=5)
        try:
            await asyncio.wait_for(review_task, timeout=5)
        except ResourceForbiddenError:
            pass
        else:
            raise AssertionError("a superseded request was approved")

    async with maker() as session:
        activity = await session.get(ClubActivity, ids["activity"])
        request = await session.get(ClubActivityUpdateRequest, ids["request"])
        assert activity is not None
        assert activity.cancelled_at is not None
        assert activity.name == "Original name"
        assert request is not None
        assert request.moderation_status == ModerationStatusEnum.superseded


async def test_cancel_wins_over_queued_manual_check_in(
    committed_activity: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_activity
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as cancel_session, maker() as checkin_session:
        cancellation = ClubActivityService(
            PausingActivityRepository(cancel_session, acquired, release),
        )
        checkin = ClubActivityCheckInService(
            ClubActivityCheckInRepository(checkin_session),
            SignallingActivityRepository(checkin_session, attempting),
        )
        recorder = await checkin_session.get(User, ids["moderator"])
        assert recorder is not None
        cancel_task = asyncio.create_task(
            cancellation.cancel_club_activity(ids["club"], ids["activity"]),
        )
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            checkin_task = asyncio.create_task(
                checkin.check_in_manual(
                    ids["club"],
                    ids["activity"],
                    [ids["member"]],
                    recorder,
                ),
            )
            await asyncio.wait_for(attempting.wait(), timeout=5)
        finally:
            release.set()
        await asyncio.wait_for(cancel_task, timeout=5)
        try:
            await asyncio.wait_for(checkin_task, timeout=5)
        except ClubActivityCancelledError:
            pass
        else:
            raise AssertionError("a check-in was inserted after cancellation")

    async with maker() as session:
        rows = await session.scalars(
            select(ClubActivityCheckIn).where(
                ClubActivityCheckIn.club_activity_id == ids["activity"],
            ),
        )
        assert rows.all() == []
