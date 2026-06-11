from datetime import UTC, datetime

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models import Club, User
from app.models.club_activity import ClubActivity
from app.models.moderations.club_activity import (
    ClubActivityCreateRequest,
    ClubActivityUpdateRequest,
)
from app.repositories.club_activity import (
    ClubActivityCreateRequestRepository,
    ClubActivityRepository,
    ClubActivityUpdateRequestRepository,
)
from app.schemas.club_activity import ClubActivityCreate, ClubActivityUpdate
from app.schemas.moderations.club_activity import (
    ClubActivityCreateRequestCreate,
    ClubActivityUpdateRequestCreate,
)
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.services.base import ServiceBase
from app.services.errors import DuplicatePendingRequestError


class ClubActivityService(
    ServiceBase[
        ClubActivity,
        ClubActivityCreate,
        ClubActivityUpdate,
    ],
):
    repository: ClubActivityRepository

    async def get_club_activities(
        self,
        club: Club,
    ) -> Page[ClubActivity]:
        return await self.repository.get_club_activities(club)

    async def create_club_activity(
        self,
        club_id: int,
        obj_in: ClubActivityCreate,
    ) -> ClubActivity:
        return await self.repository.create_club_activity(club_id, obj_in)


class ClubActivityCreateRequestService(
    ServiceBase[
        ClubActivityCreateRequest,
        ClubActivityCreateRequestCreate,
        RequestModerate,
    ],
):
    repository: ClubActivityCreateRequestRepository

    async def get_pending_requests(self) -> Page[ClubActivityCreateRequest]:
        return await self.repository.get_pending_requests()

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


class ClubActivityUpdateRequestService(
    ServiceBase[
        ClubActivityUpdateRequest,
        ClubActivityUpdateRequestCreate,
        RequestModerate,
    ],
):
    repository: ClubActivityUpdateRequestRepository

    async def get_pending_requests(self) -> Page[ClubActivityUpdateRequest]:
        return await self.repository.get_pending_requests()

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

    async def supersede_pending_requests_by_activity(
        self,
        club_activity_id: int,
    ) -> None:
        try:
            await self.repository.supersede_pending_requests_by_activity(
                club_activity_id,
            )
        except IntegrityError:
            raise DuplicatePendingRequestError from None
