from typing import cast

import pytest

from app.models.general_activity import (
    ClubGeneralActivityRecord,
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
