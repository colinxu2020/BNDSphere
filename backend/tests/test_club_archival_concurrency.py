"""Independent PostgreSQL sessions pin the archive/moderation lock order."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import create_check_in_token
from app.models import (
    AcademicTerm,
    Club,
    ClubActivity,
    ClubActivityCheckIn,
    ClubMember,
    GeneralActivity,
    JointActivity,
    User,
)
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivityLevelEnum,
    ParticipationTypeEnum,
)
from app.models.moderations.club_activity import ClubActivityCreateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum
from app.models.verifications.club_membership import ClubMembershipRequest
from app.repositories.club import ClubRepository
from app.repositories.club_activity import (
    ClubActivityCreateRequestRepository,
    ClubActivityRepository,
)
from app.repositories.club_activity_check_in import ClubActivityCheckInRepository
from app.repositories.general_activities import ClubGeneralActivityRepository
from app.repositories.joint_activities import JointActivityRepository
from app.repositories.star_level import StarLevelRepository
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityUpdate,
    FederationRecordUpdate,
)
from app.schemas.joint_activities import JointActivityCreate, JointActivityUpdate
from app.schemas.moderations.club_activity import ClubActivityCreateRequestCreatePublic
from app.schemas.moderations.joint_activity import JointActivityPreliminaryModeration
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.schemas.star_level import (
    StarLevelApplicationCreate,
    StarLevelApplicationReview,
    StarLevelApplicationUpdate,
)
from app.schemas.verifications.club_membership import ClubMembershipRequestCreatePublic
from app.services.club import ClubService
from app.services.club_activity import (
    ClubActivityCreateRequestService,
    ClubActivityService,
)
from app.services.club_activity_check_in import ClubActivityCheckInService
from app.services.errors import ResourceForbiddenError
from app.services.general_activities import ClubGeneralActivityService
from app.services.joint_activities import JointActivityService
from app.services.star_level import StarLevelService


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

    async def get_status(self, club_id: int) -> ClubStatusEnum | None:
        self.attempting.set()
        return await super().get_status(club_id)


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
        activity = ClubActivity(
            club_id=club.id,
            academic_term_id=term.id,
            name="Existing activity",
            description="description",
            location="room",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        session.add(activity)
        general_activity = GeneralActivity(
            name="Archive race general activity",
            description="description",
            level=GeneralActivityLevelEnum.school,
            academic_term_id=term.id,
        )
        session.add(general_activity)
        await session.flush()
        ids = {
            "club": club.id,
            "request": request.id,
            "president": president.id,
            "moderator": moderator.id,
            "term": term.id,
            "activity": activity.id,
            "general_activity": general_activity.id,
        }

    try:
        yield maker, ids
    finally:
        async with maker() as session, session.begin():
            await session.execute(
                delete(StarLevelApplication).where(
                    StarLevelApplication.club_id == ids["club"],
                ),
            )
            await session.execute(
                delete(ClubGeneralActivityRecord).where(
                    ClubGeneralActivityRecord.club_id == ids["club"],
                ),
            )
            await session.execute(
                delete(JointActivity).where(
                    JointActivity.initiator_club_id == ids["club"],
                ),
            )
            await session.execute(
                delete(ClubActivityCheckIn).where(
                    ClubActivityCheckIn.club_activity_id == ids["activity"],
                ),
            )
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
                delete(GeneralActivity).where(
                    GeneralActivity.id == ids["general_activity"],
                ),
            )
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
        assert count == 1


async def test_archive_wins_over_queued_membership_request(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_club_request
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as archive_session, maker() as join_session:
        president = await archive_session.get(User, ids["president"])
        applicant = await join_session.get(User, ids["moderator"])
        assert president is not None
        assert applicant is not None
        archival = ClubService(
            PausingClubRepository(archive_session, acquired, release),
        )
        # The app's normal state check initially calls get(), not get_with_lock().
        join = ClubService(SignallingClubRepository(join_session, attempting))
        archive_task = asyncio.create_task(
            archival.archive_club(ids["club"], president),
        )
        join_task = None
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            join_task = asyncio.create_task(
                join.request_join_club(
                    ids["club"],
                    applicant,
                    ClubMembershipRequestCreatePublic(message="join after archive"),
                ),
            )
            await asyncio.wait_for(attempting.wait(), timeout=5)
            release.set()
            await asyncio.wait_for(archive_task, timeout=5)
            try:
                await asyncio.wait_for(join_task, timeout=5)
            except ResourceForbiddenError:
                pass
            else:
                raise AssertionError("membership request created after archival")
        finally:
            release.set()
            for task in (archive_task, join_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (archive_task, join_task) if task is not None),
                return_exceptions=True,
            )

    async with maker() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ClubMembershipRequest)
            .where(ClubMembershipRequest.club_id == ids["club"]),
        )
        assert count == 0


async def test_archived_club_cannot_create_related_records(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_club_request
    async with maker() as session:
        president = await session.get(User, ids["president"])
        assert president is not None
        await ClubService(ClubRepository(session)).archive_club(ids["club"], president)

    async with maker() as session:
        general = ClubGeneralActivityService(ClubGeneralActivityRepository(session))
        with pytest.raises(ResourceForbiddenError):
            await general.create_club_general_activity(
                ClubGeneralActivityCreate(
                    activity_id=ids["general_activity"],
                    participation_type=ParticipationTypeEnum.participate_only,
                    requested_score=0,
                ),
                ids["club"],
            )
        joint = JointActivityService(JointActivityRepository(session))
        with pytest.raises(ResourceForbiddenError):
            await joint.create_for_club(
                JointActivityCreate(
                    name="Too late",
                    description="description",
                    location="room",
                    starts_at=datetime.now(UTC) + timedelta(days=1),
                    ends_at=datetime.now(UTC) + timedelta(days=2),
                ),
                club_id=ids["club"],
                user_id=ids["president"],
            )
        with pytest.raises(ResourceForbiddenError):
            await StarLevelService(StarLevelRepository(session)).create(
                StarLevelApplicationCreate(),
                club_id=ids["club"],
            )


async def test_archived_related_records_are_immutable(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_club_request
    async with maker() as session, session.begin():
        record = ClubGeneralActivityRecord(
            club_id=ids["club"],
            activity_id=ids["general_activity"],
            participation_type=ParticipationTypeEnum.participate_only,
            requested_score=0,
            proof_files=[],
        )
        application = StarLevelApplication(
            club_id=ids["club"],
            academic_term_id=ids["term"],
        )
        joint = JointActivity(
            initiator_club_id=ids["club"],
            created_by_user_id=ids["president"],
            academic_term_id=ids["term"],
            name="Original",
            description="description",
            location="room",
            starts_at=datetime.now(UTC) + timedelta(days=1),
            ends_at=datetime.now(UTC) + timedelta(days=2),
        )
        session.add_all([record, application, joint])
        await session.flush()
        record_id, application_id, joint_id = record.id, application.id, joint.id

    async with maker() as session:
        president = await session.get(User, ids["president"])
        assert president is not None
        await ClubService(ClubRepository(session)).archive_club(ids["club"], president)

    async with maker() as session:
        record = await session.get(ClubGeneralActivityRecord, record_id)
        application = await session.get(StarLevelApplication, application_id)
        moderator = await session.get(User, ids["moderator"])
        assert record is not None
        assert application is not None
        assert moderator is not None
        general = ClubGeneralActivityService(ClubGeneralActivityRepository(session))
        update = ClubGeneralActivityUpdate(
            activity_id=ids["general_activity"],
            participation_type=ParticipationTypeEnum.participate_only,
            requested_score=1,
        )
        with pytest.raises(ResourceForbiddenError):
            await general.update(record, update)
        with pytest.raises(ResourceForbiddenError):
            await general.review_record(
                record_id,
                FederationRecordUpdate(audit_status=AuditStatusEnum.approved),
                moderator,
            )
        star = StarLevelService(StarLevelRepository(session))
        await session.refresh(application)
        with pytest.raises(ResourceForbiddenError):
            await star.update(
                application,
                StarLevelApplicationUpdate(uniqueness_statement="changed"),
            )
        with pytest.raises(ResourceForbiddenError):
            await star.review(
                application_id,
                StarLevelApplicationReview(audit_status=AuditStatusEnum.rejected),
                moderator,
            )
        joints = JointActivityService(JointActivityRepository(session))
        with pytest.raises(ResourceForbiddenError):
            await joints.update_for_initiator(
                joint_id,
                ids["club"],
                JointActivityUpdate(name="changed"),
            )
        with pytest.raises(ResourceForbiddenError):
            await joints.preliminary_review(
                joint_id,
                JointActivityPreliminaryModeration(
                    moderation_status=ModerationStatusEnum.approved,
                ),
                moderator,
            )


@pytest.mark.parametrize("record_kind", ["general", "joint", "star"])
async def test_archive_wins_over_queued_related_creation(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
    record_kind: str,
) -> None:
    maker, ids = committed_club_request
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as archive_session, maker() as creation_session:
        president = await archive_session.get(User, ids["president"])
        assert president is not None
        archival = ClubService(
            PausingClubRepository(archive_session, acquired, release),
        )
        club_repository = SignallingClubRepository(creation_session, attempting)
        if record_kind == "general":
            service = ClubGeneralActivityService(
                ClubGeneralActivityRepository(creation_session),
                club_repository=club_repository,
            )
            creation = service.create_club_general_activity(
                ClubGeneralActivityCreate(
                    activity_id=ids["general_activity"],
                    participation_type=ParticipationTypeEnum.participate_only,
                    requested_score=0,
                ),
                ids["club"],
            )
        elif record_kind == "joint":
            joint = JointActivityService(
                JointActivityRepository(creation_session),
                club_repository=club_repository,
            )
            creation = joint.create_for_club(
                JointActivityCreate(
                    name="Too late",
                    description="description",
                    location="room",
                    starts_at=datetime.now(UTC) + timedelta(days=1),
                    ends_at=datetime.now(UTC) + timedelta(days=2),
                ),
                club_id=ids["club"],
                user_id=ids["president"],
            )
        else:
            star = StarLevelService(
                StarLevelRepository(creation_session),
                club_repository=club_repository,
            )
            creation = star.create(
                StarLevelApplicationCreate(),
                club_id=ids["club"],
            )

        archive_task = asyncio.create_task(
            archival.archive_club(ids["club"], president),
        )
        creation_task = None
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            creation_task = asyncio.create_task(creation)
            await asyncio.wait_for(attempting.wait(), timeout=5)
            release.set()
            await asyncio.wait_for(archive_task, timeout=5)
            with pytest.raises(ResourceForbiddenError):
                await asyncio.wait_for(creation_task, timeout=5)
        finally:
            release.set()
            for task in (archive_task, creation_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (archive_task, creation_task) if task is not None),
                return_exceptions=True,
            )


async def test_archive_wins_over_queued_activity_create_request(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
) -> None:
    maker, ids = committed_club_request
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as archive_session, maker() as activity_session:
        president = await archive_session.get(User, ids["president"])
        requestor = await activity_session.get(User, ids["president"])
        assert president is not None
        assert requestor is not None
        archival = ClubService(
            PausingClubRepository(archive_session, acquired, release),
        )
        activities = ClubActivityService(
            ClubActivityRepository(activity_session),
            club_repository=SignallingClubRepository(activity_session, attempting),
        )
        archive_task = asyncio.create_task(
            archival.archive_club(ids["club"], president),
        )
        request_task = None
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            now = datetime.now(UTC)
            request_task = asyncio.create_task(
                activities.request_club_activity_create(
                    ids["club"],
                    ClubActivityCreateRequestCreatePublic(
                        name="Too late",
                        description="description",
                        location="room",
                        start_time=now + timedelta(days=1),
                        end_time=now + timedelta(days=1, hours=1),
                    ),
                    requestor,
                ),
            )
            await asyncio.wait_for(attempting.wait(), timeout=5)
            release.set()
            await asyncio.wait_for(archive_task, timeout=5)
            try:
                await asyncio.wait_for(request_task, timeout=5)
            except ResourceForbiddenError:
                pass
            else:
                raise AssertionError("activity request created after archival")
        finally:
            release.set()
            for task in (archive_task, request_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (archive_task, request_task) if task is not None),
                return_exceptions=True,
            )

    async with maker() as session:
        requests = await session.scalars(
            select(ClubActivityCreateRequest).where(
                ClubActivityCreateRequest.club_id == ids["club"],
            ),
        )
        assert len(requests.all()) == 1


@pytest.mark.parametrize("method", ["manual", "qr"])
async def test_archive_wins_over_queued_check_in(
    committed_club_request: tuple[async_sessionmaker[AsyncSession], dict[str, int]],
    method: str,
) -> None:
    maker, ids = committed_club_request
    acquired, release, attempting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async with maker() as archive_session, maker() as check_in_session:
        president = await archive_session.get(User, ids["president"])
        recorder = await check_in_session.get(User, ids["president"])
        assert president is not None
        assert recorder is not None
        archival = ClubService(
            PausingClubRepository(archive_session, acquired, release),
        )
        check_ins = ClubActivityCheckInService(
            ClubActivityCheckInRepository(check_in_session),
            club_repository=SignallingClubRepository(check_in_session, attempting),
        )
        archive_task = asyncio.create_task(
            archival.archive_club(ids["club"], president),
        )
        check_in_task = None
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            if method == "manual":
                check_in = check_ins.check_in_manual(
                    ids["club"],
                    ids["activity"],
                    [ids["president"]],
                    recorder,
                )
            else:
                token = create_check_in_token(
                    ids["activity"],
                    datetime.now(UTC) + timedelta(hours=1),
                )
                check_in = check_ins.check_in_via_qr(
                    ids["club"],
                    ids["activity"],
                    token,
                    recorder,
                )
            check_in_task = asyncio.create_task(check_in)
            await asyncio.wait_for(attempting.wait(), timeout=5)
            release.set()
            await asyncio.wait_for(archive_task, timeout=5)
            try:
                await asyncio.wait_for(check_in_task, timeout=5)
            except ResourceForbiddenError:
                pass
            else:
                raise AssertionError(f"{method} check-in inserted after archival")
        finally:
            release.set()
            for task in (archive_task, check_in_task):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (archive_task, check_in_task) if task is not None),
                return_exceptions=True,
            )

    async with maker() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ClubActivityCheckIn)
            .where(ClubActivityCheckIn.club_activity_id == ids["activity"]),
        )
        assert count == 0
