from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_term import AcademicTerm
from app.models.club import Club, ClubCategoryEnum
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivity,
    GeneralActivityLevelEnum,
    ParticipationTypeEnum,
)
from app.models.star_level import StarLevelApplication
from app.models.user import User
from app.models.verifications.verification_common import VerificationStatusEnum
from app.repositories.general_activities import ClubGeneralActivityRepository
from app.repositories.star_level import StarLevelRepository
from app.schemas.general_activities import (
    ClubGeneralActivityInfo,
    FederationRecordUpdate,
)
from app.schemas.star_level import StarLevelApplicationInfo, StarLevelApplicationReview
from app.services.general_activities import ClubGeneralActivityService
from app.services.star_level import StarLevelService


@pytest.mark.parametrize("kind", ["general_activity", "star_level"])
@pytest.mark.parametrize(
    "status",
    [VerificationStatusEnum.approved, VerificationStatusEnum.rejected],
)
async def test_review_persists_verifier_and_timestamp(
    db_session: AsyncSession,
    kind: str,
    status: VerificationStatusEnum,
) -> None:
    term = AcademicTerm(
        term_name=uuid4().hex,
        start_date=date(2026, 9, 1),
        end_date=date(2027, 1, 1),
        is_current=False,
    )
    club = Club(
        name=uuid4().hex,
        summary="Summary",
        description="Description",
        category=ClubCategoryEnum.natural_science,
    )
    verifier = User(username=uuid4().hex, hashed_password=uuid4().hex)
    db_session.add_all([term, club, verifier])
    await db_session.flush()

    if kind == "general_activity":
        activity = GeneralActivity(
            name=uuid4().hex,
            description="Description",
            level=GeneralActivityLevelEnum.school,
            academic_term_id=term.id,
        )
        db_session.add(activity)
        await db_session.flush()
        record = ClubGeneralActivityRecord(
            club_id=club.id,
            activity_id=activity.id,
            participation_type=ParticipationTypeEnum.participate_only,
            requested_score=5,
            proof_files=[],
        )
        db_session.add(record)
        await db_session.flush()
        assert record.verification_status == VerificationStatusEnum.pending
        assert record.verify_at is None
        before = datetime.now(UTC)
        reviewed = await ClubGeneralActivityService(
            ClubGeneralActivityRepository(db_session),
        ).review_record(
            record.id,
            FederationRecordUpdate(verification_status=status, final_score=5),
            verifier,
        )
        await db_session.refresh(reviewed, ["met_conditions"])
        info = ClubGeneralActivityInfo.model_validate(reviewed)
    else:
        application = StarLevelApplication(
            club_id=club.id,
            academic_term_id=term.id,
        )
        db_session.add(application)
        await db_session.flush()
        assert application.verification_status == VerificationStatusEnum.pending
        assert application.verify_at is None
        before = datetime.now(UTC)
        reviewed = await StarLevelService(StarLevelRepository(db_session)).review(
            application.id,
            StarLevelApplicationReview(verification_status=status),
            verifier,
        )
        await db_session.refresh(reviewed)
        info = StarLevelApplicationInfo.model_validate(reviewed)

    assert info.verification_status == status
    assert info.verifier_id == verifier.id
    assert info.verify_at is not None
    assert before <= info.verify_at <= datetime.now(UTC)
