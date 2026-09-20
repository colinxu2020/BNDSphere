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
        raise AssertionError("an already-reviewed application must not be updated")


@pytest.mark.parametrize(
    "existing_status",
    [AuditStatusEnum.approved, AuditStatusEnum.rejected],
)
async def test_review_rejects_an_application_that_was_already_reviewed(
    existing_status: AuditStatusEnum,
) -> None:
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
    review = StarLevelApplicationReview(audit_status=AuditStatusEnum.approved)
    auditor = User(
        id=11,
        username="reviewer",
        hashed_password="unused",  # noqa: S106
    )

    with pytest.raises(StarLevelApplicationUpdateDeniedError):
        await service.review(application.id, review, auditor)
