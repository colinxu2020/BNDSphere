from typing import override

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models import Club
from app.models.club import ClubStatusEnum
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
from app.services.club_access import get_locked_normal_club
from app.services.errors import (
    DuplicateResourceError,
    StarLevelApplicationUpdateDeniedError,
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

    async def get_public(self, application_id: int) -> StarLevelApplication:
        application = await self.repository.get_public(application_id)
        if application is None:
            raise StarLevelNotFoundError(application_id) from None
        return application

    async def list_by_club(self, club: Club) -> Page[StarLevelApplication]:
        return await self.repository.list_by_club(club)

    @override
    async def create(
        self,
        obj_in: StarLevelApplicationCreate,
        **kwargs: object,
    ) -> StarLevelApplication:
        try:
            club_id = kwargs.get("club_id")
            if not isinstance(club_id, int):
                raise TypeError("club_id is required")
            async with self.transaction():
                await get_locked_normal_club(self.club_repository, club_id)
                return await self.repository.create(obj_in, **kwargs)
        except IntegrityError:
            raise DuplicateResourceError(
                message_key="error.star_level.duplicate_application",
                error_code="DUPLICATE_STAR_LEVEL_APPLICATION",
                details={"club_id": kwargs.get("club_id")},
            ) from None

    @override
    async def update(
        self,
        db_obj: StarLevelApplication,
        obj_in: StarLevelApplicationUpdate,
    ) -> StarLevelApplication:
        async with self.transaction():
            await get_locked_normal_club(self.club_repository, db_obj.club_id)
            application = await self._get_with_lock(db_obj.id)
            if application is None or application.club_id != db_obj.club_id:
                raise StarLevelNotFoundError(db_obj.id) from None
            if application.audit_status == AuditStatusEnum.approved:
                raise StarLevelApplicationUpdateDeniedError(db_obj.id) from None
            return await self.repository.update(application, obj_in)

    async def review(
        self,
        application_id: int,
        review: StarLevelApplicationReview,
        auditor: User,
    ) -> StarLevelApplication:
        async with self.transaction():
            application = await self.repository.get(application_id)
            if application is None:
                raise StarLevelNotFoundError(application_id) from None
            club = await get_locked_normal_club(
                self.club_repository,
                application.club_id,
            )
            application = await self._get_with_lock(application_id)
            if application is None:
                raise StarLevelNotFoundError(application_id) from None
            # Only an approval is final: it has already written the club's
            # star level. A rejection is not — the president may edit the
            # application (``update_application`` refuses approved ones only),
            # and the term's uniqueness constraint means that edit is the only
            # way to resubmit, so it has to stay reviewable.
            if application.audit_status == AuditStatusEnum.approved:
                raise StarLevelApplicationUpdateDeniedError(application_id) from None

            application = await self.repository.update_review(
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
        *,
        include_archived: bool = False,
    ) -> StarLevelApplicationReviewPreview:
        application = await self.repository.get(application_id)
        if application is None:
            raise StarLevelNotFoundError(application_id) from None
        if (
            not include_archived
            and await self.club_repository.get_status(application.club_id)
            != ClubStatusEnum.normal
        ):
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
