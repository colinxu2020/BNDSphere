from typing import cast

import pytest

from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum, User
from app.repositories.club import ClubRepository
from app.repositories.star_level import StarLevelRepository
from app.schemas.star_level import StarLevelApplicationReview
from app.services.errors import StarLevelApplicationUpdateDeniedError
from app.services.star_level import StarLevelService
from app.services.star_rating import StarRatingService


class TransactionlessSession:
    def __init__(self) -> None:
        self.info: dict[str, object] = {}

    def in_transaction(self) -> bool:
        return False


class ExistingApplicationRepository:
    def __init__(self, application: StarLevelApplication) -> None:
        self.db = TransactionlessSession()
        self.application = application

    async def get_with_lock(self, application_id: int) -> StarLevelApplication | None:
        if application_id == self.application.id:
            return self.application
        return None

    async def update_review(
        self,
        application: StarLevelApplication,
        review: StarLevelApplicationReview,
    ) -> StarLevelApplication:
        raise ReachedUpdateError


class ReachedUpdateError(Exception):
    """The review got past the status guard and tried to write."""


def _service_for(
    existing_status: AuditStatusEnum,
) -> tuple[StarLevelService, StarLevelApplication]:
    application = StarLevelApplication(
        id=7,
        club_id=3,
        academic_term_id=1,
        audit_status=existing_status,
    )
    repository = ExistingApplicationRepository(application)
    service = StarLevelService(
        cast("StarLevelRepository", repository),
        club_repository=cast("ClubRepository", object()),
        star_rating_service=cast("StarRatingService", object()),
    )
    return service, application


REVIEW = StarLevelApplicationReview(audit_status=AuditStatusEnum.approved)
AUDITOR = User(id=11, username="reviewer", hashed_password="unused")  # noqa: S106


async def test_an_approved_application_cannot_be_reviewed_again() -> None:
    # The approval already set the club's star level; a second review would
    # silently rewrite it.
    service, application = _service_for(AuditStatusEnum.approved)
    with pytest.raises(StarLevelApplicationUpdateDeniedError):
        await service.review(application.id, REVIEW, AUDITOR)


@pytest.mark.parametrize(
    "existing_status",
    [AuditStatusEnum.pending, AuditStatusEnum.rejected],
)
async def test_pending_and_rejected_applications_stay_reviewable(
    existing_status: AuditStatusEnum,
) -> None:
    # Rejected is how a resubmission arrives: the president edits it in place,
    # because the per-term uniqueness constraint forbids a second application.
    service, application = _service_for(existing_status)
    with pytest.raises(ReachedUpdateError):
        await service.review(application.id, REVIEW, AUDITOR)
