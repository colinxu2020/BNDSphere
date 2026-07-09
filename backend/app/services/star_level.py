from typing import override

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models import Club
from app.models.star_level import StarLevelApplication
from app.models.user import AuditStatusEnum, User
from app.repositories.club import ClubRepository
from app.repositories.star_level import StarLevelRepository
from app.repositories.star_rating import StarRatingRepository
from app.schemas.star_level import (
    StarLevelApplicationCreate,
    StarLevelApplicationReview,
    StarLevelApplicationReviewPreview,
    StarLevelApplicationUpdate,
)
from app.services.base import ServiceBase
from app.services.errors import (
    ClubNotFoundError,
    DuplicateResourceError,
    StarLevelNotFoundError,
)
from app.services.star_rating import StarRatingService


class StarLevelService(
    ServiceBase[
        StarLevelApplication,
        StarLevelApplicationCreate,
        StarLevelApplicationUpdate,
    ],
):
    repository: StarLevelRepository

    def __init__(
        self,
        repository: StarLevelRepository,
        club_repository: ClubRepository | None = None,
        star_rating_service: StarRatingService | None = None,
    ) -> None:
        super().__init__(repository)
        self.club_repository = club_repository or ClubRepository(repository.db)
        self.star_rating_service = star_rating_service or StarRatingService(
            StarRatingRepository(repository.db),
        )

    async def list_public(self) -> Page[StarLevelApplication]:
        return await self.repository.list_public()

    async def list_by_club(self, club: Club) -> Page[StarLevelApplication]:
        return await self.repository.list_by_club(club)

    @override
    async def create(
        self,
        obj_in: StarLevelApplicationCreate,
        **kwargs: object,
    ) -> StarLevelApplication:
        try:
            return await super().create(obj_in, **kwargs)
        except IntegrityError:
            raise DuplicateResourceError(
                message_key="error.star_level.duplicate_application",
                error_code="DUPLICATE_STAR_LEVEL_APPLICATION",
                details={"club_id": kwargs.get("club_id")},
            ) from None

    async def review(
        self,
        application_id: int,
        review: StarLevelApplicationReview,
        auditor: User,
    ) -> StarLevelApplication:
        async with self.transaction():
            application = await self._get_with_lock(application_id)
            if application is None:
                raise StarLevelNotFoundError(application_id) from None

            application = await self.repository.update(
                application,
                review,
            )
            application.auditor_id = auditor.id
            application.auditor = auditor
            self.repository.db.add(application)

            if review.audit_status == AuditStatusEnum.approved:
                rating = (
                    await self.star_rating_service.calculate_application_review_score(
                        application,
                        review,
                    )
                )
                application.approved_score = rating.total_score
                application.approved_level = rating.star_level
                club = await self.club_repository.get(application.club_id)
                if club is None:
                    raise ClubNotFoundError(application.club_id) from None
                club.star_level = rating.star_level
                self.repository.db.add(club)
            else:
                application.approved_score = None
                application.approved_level = None

            self.repository.db.add(application)
            await self.repository.db.flush()

            return application

    async def preview_review(
        self,
        application_id: int,
        review: StarLevelApplicationReview,
    ) -> StarLevelApplicationReviewPreview:
        application = await self.repository.get(application_id)
        if application is None:
            raise StarLevelNotFoundError(application_id) from None

        if review.audit_status != AuditStatusEnum.approved:
            return StarLevelApplicationReviewPreview(
                approved_score=None,
                approved_level=None,
            )

        rating = await self.star_rating_service.calculate_application_review_score(
            application,
            review,
        )
        return StarLevelApplicationReviewPreview(
            approved_score=rating.total_score,
            approved_level=rating.star_level,
        )
