from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.user import User
from app.repositories.club import (
    ClubMemberRepository,
    ClubRepository,
    ClubUpdateRequestRepository,
)
from app.schemas.club import AdminClubUpdate, ClubCreate, ClubMemberUpdate
from app.schemas.moderations.club import ClubUpdateRequestCreate
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.services.base import ServiceBase
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicatePendingRequestError,
    ResourceForbiddenError,
)


class ClubService(ServiceBase[Club, ClubCreate, AdminClubUpdate]):
    repository: ClubRepository

    async def create(self, obj_in: ClubCreate, **kwargs: object) -> Club:
        try:
            return await super().create(obj_in, **kwargs)
        except IntegrityError as exc:
            raise DuplicateClubNameError from exc

    async def ensure_club_normal(self, club_id: int) -> Club:
        club = await self.get(club_id)
        if club is None:
            raise ClubNotFoundError(club_id) from None
        if club.status != ClubStatusEnum.normal:
            raise ResourceForbiddenError(
                "error.club.not_active",
                "CLUB_NOT_ACTIVE",
                {"club_id": club_id},
            ) from None
        return club

    async def get_by_name(self, name: str) -> Sequence[Club]:
        return await self.repository.get_by_name(name)

    async def get_multi(
        self,
        search: str | None = None,
        category: ClubCategoryEnum | None = None,
        status: ClubStatusEnum | None = None,
    ) -> Page[Club]:
        return await self.repository.get_multi(search, category, status)


class ClubMemberService(
    ServiceBase[ClubMember, ClubMemberUpdate, ClubMemberUpdate],
):
    repository: ClubMemberRepository

    async def get_by_club_user(self, club: Club, user: User) -> ClubMember | None:
        return await self.repository.get_by_club_user(club, user)

    async def set_relationship(
        self,
        club: Club,
        user: User,
        membership: ClubMembershipEnum,
    ) -> ClubMember:
        return await self.repository.set_relationship(club, user, membership)


class ClubUpdateRequestService(
    ServiceBase[
        ClubUpdateRequest,
        ClubUpdateRequestCreate,
        RequestModerate,
    ],
):
    repository: ClubUpdateRequestRepository

    async def get_pending_requests(self) -> Page[ClubUpdateRequest]:
        return await self.repository.get_pending_requests()

    async def moderate_request(
        self,
        request: ClubUpdateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubUpdateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )

    async def supersede_pending_requests_by_club(self, club_id: int) -> None:
        try:
            await self.repository.supersede_pending_requests_by_club(club_id)
        except IntegrityError:
            raise DuplicatePendingRequestError from None
