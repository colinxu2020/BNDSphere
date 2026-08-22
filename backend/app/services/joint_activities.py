from datetime import UTC, datetime

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models import JointActivity
from app.models.user import AuditStatusEnum, User
from app.repositories.joint_activities import JointActivityRepository
from app.schemas.joint_activities import (
    JointActivityArchiveUpdate,
    JointActivityCreate,
    JointActivityFinalReview,
    JointActivityPreliminaryReview,
    JointActivityUpdate,
)
from app.services.base import ServiceBase
from app.services.errors import (
    BadRequestError,
    DuplicateResourceError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)


def _not_found(activity_id: int) -> ResourceNotFoundError:
    return ResourceNotFoundError(
        "error.joint_activity.not_found",
        "JOINT_ACTIVITY_NOT_FOUND",
        {"joint_activity_id": activity_id},
    )


class JointActivityService(
    ServiceBase[JointActivity, JointActivityCreate, JointActivityUpdate],
):
    repository: JointActivityRepository

    async def get_public(self, activity_id: int) -> JointActivity:
        activity = await self.get(activity_id)
        if activity is None or activity.preliminary_status != AuditStatusEnum.approved:
            raise _not_found(activity_id)
        return activity

    async def list_public(
        self,
        search: str | None = None,
    ) -> Page[JointActivity]:
        return await self.repository.get_multi(public_only=True, search=search)

    async def list_for_federation(
        self,
        search: str | None = None,
    ) -> Page[JointActivity]:
        return await self.repository.get_multi(public_only=False, search=search)

    async def list_for_club(self, club_id: int) -> Page[JointActivity]:
        return await self.repository.get_multi(
            public_only=False,
            club_id=club_id,
        )

    async def create_for_club(
        self,
        obj_in: JointActivityCreate,
        *,
        club_id: int,
        user_id: int,
    ) -> JointActivity:
        async with self.transaction():
            activity = await self.repository.create_with_initiator(
                obj_in,
                club_id=club_id,
                user_id=user_id,
            )
        result = await self.get(activity.id)
        if result is None:
            raise _not_found(activity.id)
        return result

    async def update_for_initiator(
        self,
        activity_id: int,
        club_id: int,
        obj_in: JointActivityUpdate,
    ) -> JointActivity:
        async with self.transaction():
            activity = await self._get_with_lock(activity_id)
            if activity is None:
                raise _not_found(activity_id)
            self._ensure_initiator(activity, club_id)
            if activity.preliminary_status == AuditStatusEnum.approved:
                raise ResourceForbiddenError(
                    "error.joint_activity.preliminary_approved",
                    "JOINT_ACTIVITY_PRELIMINARY_APPROVED",
                    {"joint_activity_id": activity_id},
                )

            starts_at = obj_in.starts_at or activity.starts_at
            ends_at = obj_in.ends_at or activity.ends_at
            if ends_at <= starts_at:
                raise BadRequestError(
                    "error.joint_activity.invalid_time_range",
                    "JOINT_ACTIVITY_INVALID_TIME_RANGE",
                )

            activity = await self.repository.update(activity, obj_in)
            activity.preliminary_status = AuditStatusEnum.pending
            activity.preliminary_auditor_id = None
            activity.preliminary_reviewed_at = None
            await self.repository.db.flush()
            return activity

    async def register_participation(
        self,
        activity_id: int,
        *,
        club_id: int,
        user_id: int,
    ) -> JointActivity:
        try:
            async with self.transaction():
                activity = await self._get_with_lock(activity_id)
                if activity is None:
                    raise _not_found(activity_id)
                if activity.preliminary_status != AuditStatusEnum.approved:
                    raise ResourceForbiddenError(
                        "error.joint_activity.not_public",
                        "JOINT_ACTIVITY_NOT_PUBLIC",
                    )
                if datetime.now(tz=UTC) >= activity.ends_at:
                    raise BadRequestError(
                        "error.joint_activity.registration_closed",
                        "JOINT_ACTIVITY_REGISTRATION_CLOSED",
                    )
                existing = await self.repository.get_participation(
                    activity_id,
                    club_id,
                )
                if existing is not None:
                    raise DuplicateResourceError(
                        "error.joint_activity.club_registered",
                        "JOINT_ACTIVITY_CLUB_REGISTERED",
                        {"joint_activity_id": activity_id, "club_id": club_id},
                    )
                await self.repository.add_participation(
                    activity_id=activity_id,
                    club_id=club_id,
                    user_id=user_id,
                )
        except IntegrityError:
            raise DuplicateResourceError(
                "error.joint_activity.club_registered",
                "JOINT_ACTIVITY_CLUB_REGISTERED",
                {"joint_activity_id": activity_id, "club_id": club_id},
            ) from None

        result = await self.get(activity_id)
        if result is None:
            raise _not_found(activity_id)
        return result

    async def update_archive(
        self,
        activity_id: int,
        club_id: int,
        obj_in: JointActivityArchiveUpdate,
    ) -> JointActivity:
        async with self.transaction():
            activity = await self._get_with_lock(activity_id)
            if activity is None:
                raise _not_found(activity_id)
            self._ensure_initiator(activity, club_id)
            self._ensure_archivable(activity)
            if activity.final_status in (
                AuditStatusEnum.pending,
                AuditStatusEnum.approved,
            ):
                raise ResourceForbiddenError(
                    "error.joint_activity.final_review_locked",
                    "JOINT_ACTIVITY_FINAL_REVIEW_LOCKED",
                )
            activity.archive_text = (
                obj_in.archive_text.strip() if obj_in.archive_text else None
            )
            activity.archive_files = obj_in.archive_files
            self.repository.db.add(activity)
            await self.repository.db.flush()
            await self.repository.db.refresh(activity)
            return activity

    async def submit_final_review(
        self,
        activity_id: int,
        club_id: int,
    ) -> JointActivity:
        async with self.transaction():
            activity = await self._get_with_lock(activity_id)
            if activity is None:
                raise _not_found(activity_id)
            self._ensure_initiator(activity, club_id)
            self._ensure_archivable(activity)
            if activity.final_status in (
                AuditStatusEnum.pending,
                AuditStatusEnum.approved,
            ):
                raise ResourceForbiddenError(
                    "error.joint_activity.final_review_locked",
                    "JOINT_ACTIVITY_FINAL_REVIEW_LOCKED",
                )
            if not activity.archive_text and not activity.archive_files:
                raise BadRequestError(
                    "error.joint_activity.archive_required",
                    "JOINT_ACTIVITY_ARCHIVE_REQUIRED",
                )
            activity.final_status = AuditStatusEnum.pending
            activity.final_submitted_at = datetime.now(tz=UTC)
            activity.final_auditor_id = None
            activity.final_reviewed_at = None
            activity.final_score = 0
            self.repository.db.add(activity)
            await self.repository.db.flush()
            await self.repository.db.refresh(activity)
            return activity

    async def preliminary_review(
        self,
        activity_id: int,
        review: JointActivityPreliminaryReview,
        auditor: User,
    ) -> JointActivity:
        async with self.transaction():
            activity = await self._get_with_lock(activity_id)
            if activity is None:
                raise _not_found(activity_id)
            if activity.preliminary_status != AuditStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.joint_activity.preliminary_reviewed",
                    "JOINT_ACTIVITY_PRELIMINARY_REVIEWED",
                )
            return await self.repository.preliminary_review(
                activity,
                status=review.status,
                auditor=auditor,
                reviewed_at=datetime.now(tz=UTC),
            )

    async def final_review(
        self,
        activity_id: int,
        review: JointActivityFinalReview,
        auditor: User,
    ) -> JointActivity:
        async with self.transaction():
            activity = await self._get_with_lock(activity_id)
            if activity is None:
                raise _not_found(activity_id)
            if activity.final_status != AuditStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.joint_activity.final_review_not_pending",
                    "JOINT_ACTIVITY_FINAL_REVIEW_NOT_PENDING",
                )
            return await self.repository.final_review(
                activity,
                review,
                auditor=auditor,
                reviewed_at=datetime.now(tz=UTC),
            )

    @staticmethod
    def _ensure_initiator(activity: JointActivity, club_id: int) -> None:
        if activity.initiator_club_id != club_id:
            raise ResourceForbiddenError(
                "error.joint_activity.initiator_required",
                "JOINT_ACTIVITY_INITIATOR_REQUIRED",
                {"joint_activity_id": activity.id, "club_id": club_id},
            )

    @staticmethod
    def _ensure_archivable(activity: JointActivity) -> None:
        if activity.preliminary_status != AuditStatusEnum.approved:
            raise ResourceForbiddenError(
                "error.joint_activity.not_public",
                "JOINT_ACTIVITY_NOT_PUBLIC",
            )
        if datetime.now(tz=UTC) < activity.ends_at:
            raise BadRequestError(
                "error.joint_activity.not_ended",
                "JOINT_ACTIVITY_NOT_ENDED",
            )
