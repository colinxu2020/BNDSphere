from datetime import date
from typing import cast

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubCategoryEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
    ParticipationTypeEnum,
)
from app.models.user import AuditStatusEnum, User
from app.repositories.general_activities import ClubGeneralActivityRepository
from app.schemas.general_activities import FederationRecordUpdate
from app.services.errors import ResourceForbiddenError, ResourceNotFoundError
from app.services.general_activities import ClubGeneralActivityService


class TransactionlessSession:
    def __init__(self) -> None:
        self.info: dict[str, object] = {}

    def in_transaction(self) -> bool:
        return False


class ExistingRecordRepository:
    def __init__(self, record: ClubGeneralActivityRecord) -> None:
        self.db = TransactionlessSession()
        self.record = record

    async def get(self, record_id: int) -> ClubGeneralActivityRecord | None:
        if record_id == self.record.id:
            return self.record
        return None

    async def get_with_lock(self, record_id: int) -> ClubGeneralActivityRecord | None:
        assert self.db.info.get("unit_of_work_depth") == 1
        return await self.get(record_id)

    async def review_record(
        self,
        record: ClubGeneralActivityRecord,
        update: FederationRecordUpdate,
        auditor: User,
    ) -> ClubGeneralActivityRecord:
        raise AssertionError("an already-reviewed record must not be updated")


@pytest.mark.parametrize(
    "existing_status",
    [AuditStatusEnum.approved, AuditStatusEnum.rejected],
)
async def test_review_rejects_a_record_that_was_already_reviewed(
    existing_status: AuditStatusEnum,
) -> None:
    record = ClubGeneralActivityRecord(
        id=13,
        club_id=3,
        activity_id=5,
        participation_type=ParticipationTypeEnum.participate_only,
        requested_score=1,
        proof_files=[],
        audit_status=existing_status,
    )
    repository = ExistingRecordRepository(record)
    service = ClubGeneralActivityService(
        cast("ClubGeneralActivityRepository", repository),
    )
    update = FederationRecordUpdate(
        audit_status=AuditStatusEnum.approved,
        final_score=1,
    )
    auditor = User(
        id=11,
        username="reviewer",
        hashed_password="unused",  # noqa: S106
    )

    with pytest.raises(ResourceForbiddenError) as exc_info:
        await service.review_record(record.id, update, auditor)

    assert exc_info.value.error_code == "RECORD_REVIEWED"


async def test_review_preserves_the_public_not_found_error_code() -> None:
    record = ClubGeneralActivityRecord(
        id=13,
        club_id=3,
        activity_id=5,
        participation_type=ParticipationTypeEnum.participate_only,
        requested_score=1,
        proof_files=[],
        audit_status=AuditStatusEnum.pending,
    )
    repository = ExistingRecordRepository(record)
    service = ClubGeneralActivityService(
        cast("ClubGeneralActivityRepository", repository),
    )
    update = FederationRecordUpdate(
        audit_status=AuditStatusEnum.approved,
        final_score=1,
    )
    auditor = User(
        id=11,
        username="reviewer",
        hashed_password="unused",  # noqa: S106
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.review_record(99, update, auditor)

    assert exc_info.value.error_code == "CLUB_GENERAL_ACTIVITY_RECORD_NOT_FOUND"


async def test_review_reloads_status_after_a_prior_session_read(
    db_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)
    async with sessions() as seed:
        term = AcademicTerm(
            term_name="review-stale-status-term",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 1),
            is_current=False,
        )
        club = Club(
            name="review-stale-status-club",
            summary="Summary",
            description="Description",
            category=ClubCategoryEnum.natural_science,
        )
        reviewer = User(
            username="review-stale-status-user",
            hashed_password="unused",  # noqa: S106
        )
        seed.add_all([term, club, reviewer])
        await seed.flush()
        activity = GeneralActivity(
            name="review-stale-status-activity",
            description="Description",
            level=GeneralActivityLevelEnum.school,
            academic_term_id=term.id,
        )
        seed.add(activity)
        await seed.flush()
        record = ClubGeneralActivityRecord(
            club_id=club.id,
            activity_id=activity.id,
            participation_type=ParticipationTypeEnum.participate_only,
            requested_score=1,
            audit_status=AuditStatusEnum.pending,
            proof_files=[],
        )
        seed.add(record)
        await seed.commit()
        record_id, reviewer_id = record.id, reviewer.id

    async with sessions() as stale_session, sessions() as concurrent_session:
        earlier = await stale_session.scalar(
            select(ClubGeneralActivityRecord).where(
                ClubGeneralActivityRecord.id == record_id,
            ),
        )
        assert earlier is not None
        assert earlier.audit_status == AuditStatusEnum.pending
        await concurrent_session.execute(
            update(ClubGeneralActivityRecord)
            .where(ClubGeneralActivityRecord.id == record_id)
            .values(audit_status=AuditStatusEnum.rejected),
        )
        await concurrent_session.commit()

        service = ClubGeneralActivityService(
            ClubGeneralActivityRepository(stale_session),
        )
        auditor = await stale_session.get(User, reviewer_id)
        assert auditor is not None
        with pytest.raises(ResourceForbiddenError) as exc_info:
            await service.review_record(
                record_id,
                FederationRecordUpdate(
                    audit_status=AuditStatusEnum.approved,
                    final_score=1,
                ),
                auditor,
            )
        assert exc_info.value.error_code == "RECORD_REVIEWED"
        async with sessions() as verify:
            saved = await verify.get(ClubGeneralActivityRecord, record_id)
            assert saved is not None
            assert saved.audit_status == AuditStatusEnum.rejected
