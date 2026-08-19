from datetime import UTC, datetime

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models import Club, User
from app.models.club import ClubStatusEnum
from app.models.club_activity import ClubActivity
from app.models.moderations.club_activity import (
    ClubActivityCreateRequest,
    ClubActivityUpdateRequest,
)
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.repositories.club import ClubRepository
from app.repositories.club_activity import (
    ClubActivityCreateRequestRepository,
    ClubActivityRepository,
    ClubActivityUpdateRequestRepository,
)
from app.schemas.club_activity import (
    ClubActivityCreate,
    ClubActivityUpdate,
    ensure_activity_time_range,
)
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreate,
    ClubActivityCreateRequestCreatePublic,
    ClubActivityUpdateRequestCreate,
    ClubActivityUpdateRequestCreatePublic,
)
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.services.base import ServiceBase
from app.services.errors import (
    BadRequestError,
    ClubActivityNotFoundError,
    ClubNotFoundError,
    DuplicatePendingRequestError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)
from app.services.moderation_payload import (
    build_update_payload,
    requested_update_fields,
)


def _ensure_complete_time_range(
    start_time: datetime | None,
    end_time: datetime | None,
) -> None:
    if start_time is None or end_time is None:
        raise BadRequestError(
            "error.club_activity.invalid_time_range",
            "CLUB_ACTIVITY_INVALID_TIME_RANGE",
        )
    ensure_activity_time_range(start_time, end_time)


class ClubActivityService(
    ServiceBase[
        ClubActivity,
        ClubActivityCreate,
        ClubActivityUpdate,
    ],
):
    repository: ClubActivityRepository

    def __init__(
        self,
        repository: ClubActivityRepository,
        club_repository: ClubRepository | None = None,
        create_request_repository: ClubActivityCreateRequestRepository | None = None,
        update_request_repository: ClubActivityUpdateRequestRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.club_repository = club_repository or ClubRepository(repository.db)
        self.create_request_repository = (
            create_request_repository
            or ClubActivityCreateRequestRepository(repository.db)
        )
        self.update_request_repository = (
            update_request_repository
            or ClubActivityUpdateRequestRepository(repository.db)
        )

    async def get_club_activities(
        self,
        club: Club,
    ) -> Page[ClubActivity]:
        return await self.repository.get_club_activities(club)

    async def get_club_activities_by_club_id(
        self,
        club_id: int,
    ) -> Page[ClubActivity]:
        club = await self.club_repository.get(club_id)
        if club is None:
            raise ClubNotFoundError(club_id) from None
        return await self.get_club_activities(club)

    async def create_club_activity(
        self,
        club_id: int,
        obj_in: ClubActivityCreate,
    ) -> ClubActivity:
        async with self.transaction():
            return await self.repository.create_club_activity(club_id, obj_in)

    async def request_club_activity_create(
        self,
        club_id: int,
        obj_in: ClubActivityCreateRequestCreatePublic,
        requestor: User,
    ) -> ClubActivityCreateRequest:
        async with self.transaction():
            await self._ensure_club_normal(club_id)
            return await self.create_request_repository.create(
                ClubActivityCreateRequestCreate(
                    **obj_in.model_dump(),
                    club_id=club_id,
                    requestor_id=requestor.id,
                ),
            )

    async def request_club_activity_update(
        self,
        club_id: int,
        activity_id: int,
        obj_in: ClubActivityUpdateRequestCreatePublic,
        requestor: User,
    ) -> ClubActivityUpdateRequest:
        try:
            async with self.transaction():
                await self._ensure_club_normal(club_id)
                activity = await self.get(activity_id)
                if activity is None:
                    raise ClubActivityNotFoundError(activity_id) from None
                if activity.club_id != club_id:
                    raise ResourceForbiddenError(
                        "error.club_activity.wrong_belong",
                        "CLUB_ACTIVITY_WRONG_BELONG",
                    ) from None

                update_fields = requested_update_fields(obj_in)
                start_time = (
                    obj_in.start_time
                    if "start_time" in update_fields
                    else activity.start_time
                )
                end_time = (
                    obj_in.end_time
                    if "end_time" in update_fields
                    else activity.end_time
                )
                _ensure_complete_time_range(start_time, end_time)

                update_request_repository = self.update_request_repository
                await update_request_repository.supersede_pending_requests_by_activity(
                    activity_id,
                )
                return await self.update_request_repository.create(
                    ClubActivityUpdateRequestCreate(
                        **obj_in.model_dump(exclude_unset=True),
                        club_activity_id=activity_id,
                        requestor_id=requestor.id,
                        update_fields=update_fields,
                    ),
                )
        except IntegrityError:
            raise DuplicatePendingRequestError from None

    async def _ensure_club_normal(self, club_id: int) -> Club:
        club = await self.club_repository.get(club_id)
        if club is None:
            raise ClubNotFoundError(club_id) from None
        if club.status != ClubStatusEnum.normal:
            raise ResourceForbiddenError(
                "error.club.not_active",
                "CLUB_NOT_ACTIVE",
                {"club_id": club_id},
            ) from None
        return club


class ClubActivityCreateRequestService(
    ServiceBase[
        ClubActivityCreateRequest,
        ClubActivityCreateRequestCreate,
        RequestModerate,
    ],
):
    repository: ClubActivityCreateRequestRepository

    def __init__(
        self,
        repository: ClubActivityCreateRequestRepository,
        club_repository: ClubRepository | None = None,
        activity_repository: ClubActivityRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.club_repository = club_repository or ClubRepository(repository.db)
        self.activity_repository = activity_repository or ClubActivityRepository(
            repository.db,
        )

    async def get_pending_requests(self) -> Page[ClubActivityCreateRequest]:
        return await self.repository.get_pending_requests()

    async def count_pending_requests(self) -> int:
        return await self.repository.count_pending()

    async def moderate_request(
        self,
        request: ClubActivityCreateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubActivityCreateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )

    async def approve_club_activity_create_request(
        self,
        request_id: int,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubActivityCreateRequest:
        async with self.transaction():
            request = await self._get_with_lock(request_id)
            if request is None:
                raise ResourceNotFoundError(
                    "error.club_activity_create_request.not_found",
                    "CLUB_ACTIVITY_CREATE_REQUEST_NOT_FOUND",
                ) from None
            if request.moderation_status != ModerationStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.club_activity_create_request.moderated",
                    "CLUB_ACTIVITY_CREATE_REQUEST_MODERATED",
                ) from None

            club = await self.club_repository.get(request.club_id)
            if club is None:
                raise ClubNotFoundError(request.club_id) from None

            if moderation.moderation_status == ModerationStatusEnum.approved:
                await self.activity_repository.create_club_activity(
                    club.id,
                    ClubActivityCreate.model_validate(
                        {
                            field: getattr(request, field)
                            for field in ClubActivityCreate.model_fields
                        },
                    ),
                )

            return await self.moderate_request(request, moderation, moderator)


class ClubActivityUpdateRequestService(
    ServiceBase[
        ClubActivityUpdateRequest,
        ClubActivityUpdateRequestCreate,
        RequestModerate,
    ],
):
    repository: ClubActivityUpdateRequestRepository

    def __init__(
        self,
        repository: ClubActivityUpdateRequestRepository,
        activity_repository: ClubActivityRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.activity_repository = activity_repository or ClubActivityRepository(
            repository.db,
        )

    async def get_pending_requests(self) -> Page[ClubActivityUpdateRequest]:
        return await self.repository.get_pending_requests()

    async def count_pending_requests(self) -> int:
        return await self.repository.count_pending()

    async def moderate_request(
        self,
        request: ClubActivityUpdateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubActivityUpdateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )

    async def approve_club_activity_update_request(
        self,
        request_id: int,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubActivityUpdateRequest:
        async with self.transaction():
            request = await self._get_with_lock(request_id)
            if request is None:
                raise ResourceNotFoundError(
                    "error.club_activity_update_request.not_found",
                    "CLUB_ACTIVITY_UPDATE_REQUEST_NOT_FOUND",
                ) from None
            if request.moderation_status != ModerationStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.club_activity_update_request.moderated",
                    "CLUB_ACTIVITY_UPDATE_REQUEST_MODERATED",
                ) from None

            activity = await self.activity_repository.get(request.club_activity_id)
            if activity is None:
                raise ClubActivityNotFoundError(request.club_activity_id) from None

            if moderation.moderation_status == ModerationStatusEnum.approved:
                update = build_update_payload(request, ClubActivityUpdate)
                start_time = (
                    update.start_time
                    if "start_time" in update.model_fields_set
                    else activity.start_time
                )
                end_time = (
                    update.end_time
                    if "end_time" in update.model_fields_set
                    else activity.end_time
                )
                _ensure_complete_time_range(start_time, end_time)
                await self.activity_repository.update(activity, update)

            return await self.moderate_request(request, moderation, moderator)

    async def supersede_pending_requests_by_activity(
        self,
        club_activity_id: int,
    ) -> None:
        try:
            async with self.transaction():
                await self.repository.supersede_pending_requests_by_activity(
                    club_activity_id,
                )
        except IntegrityError:
            raise DuplicatePendingRequestError from None
