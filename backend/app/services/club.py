from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import User
from app.repositories.club import (
    ClubMemberRepository,
    ClubRepository,
    ClubUpdateRequestRepository,
)
from app.schemas.club import (
    AdminClubUpdate,
    ClubCreate,
    ClubMemberUpdate,
    ClubSummaryInfo,
)
from app.schemas.moderations.club import (
    ClubUpdateRequestCreate,
    ClubUpdateRequestCreatePublic,
)
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.services.base import ServiceBase
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicatePendingRequestError,
    DuplicateResourceError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)
from app.services.moderation_payload import (
    build_update_payload,
    requested_update_fields,
)


class ClubService(ServiceBase[Club, ClubCreate, AdminClubUpdate]):
    repository: ClubRepository

    def __init__(
        self,
        repository: ClubRepository,
        member_repository: ClubMemberRepository | None = None,
        update_request_repository: ClubUpdateRequestRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.member_repository = member_repository or ClubMemberRepository(
            repository.db,
        )
        self.update_request_repository = (
            update_request_repository or ClubUpdateRequestRepository(repository.db)
        )

    async def create(self, obj_in: ClubCreate, **kwargs: object) -> Club:
        try:
            return await super().create(obj_in, **kwargs)
        except IntegrityError as exc:
            raise DuplicateClubNameError from exc

    async def create_club(self, obj_in: ClubCreate, president: User) -> Club:
        async with self.transaction():
            club = await self.create(obj_in)
            await self.member_repository.set_relationship(
                club,
                president,
                ClubMembershipEnum.president,
            )
            return club

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

    async def get_multi_summary(
        self,
        search: str | None = None,
        category: ClubCategoryEnum | None = None,
        status: ClubStatusEnum | None = None,
    ) -> Page[ClubSummaryInfo]:
        """Card/list view of clubs, with member counts computed in SQL."""
        return await self.repository.get_multi_summary(search, category, status)

    async def request_club_update(
        self,
        club_id: int,
        obj_in: ClubUpdateRequestCreatePublic,
        requestor: User,
    ) -> ClubUpdateRequest:
        try:
            async with self.transaction():
                await self.ensure_club_normal(club_id)
                await self.update_request_repository.supersede_pending_requests_by_club(
                    club_id,
                )
                return await self.update_request_repository.create(
                    ClubUpdateRequestCreate(
                        **obj_in.model_dump(exclude_unset=True),
                        club_id=club_id,
                        requestor_id=requestor.id,
                        update_fields=requested_update_fields(obj_in),
                    ),
                )
        except IntegrityError:
            raise DuplicatePendingRequestError from None

    async def join_club(self, club_id: int, user: User) -> ClubMember:
        async with self.transaction():
            club = await self.ensure_club_normal(club_id)
            relationship = await self.member_repository.get_by_club_user(club, user)
            if relationship and relationship.membership != ClubMembershipEnum.left:
                raise DuplicateResourceError(
                    message_key="error.club.duplicate_join_request",
                    error_code="DUPLICATE_JOIN_REQUEST",
                ) from None

            return await self.member_repository.set_relationship(
                club,
                user,
                ClubMembershipEnum.pending,
            )

    async def leave_club(self, club_id: int, user: User) -> None:
        async with self.transaction():
            club = await self.ensure_club_normal(club_id)
            relationship = await self.member_repository.get_by_club_user(club, user)
            if (
                relationship is None
                or relationship.membership == ClubMembershipEnum.left
            ):
                raise ResourceNotFoundError(
                    message_key="error.club.is_not_member",
                    error_code="IS_NOT_MEMBER",
                ) from None
            if relationship.membership in {
                ClubMembershipEnum.vice_president,
                ClubMembershipEnum.president,
            }:
                raise ResourceForbiddenError(
                    message_key="error.club.not_allowed_leave",
                    error_code="NOT_ALLOWED_LEAVE_CLUB",
                ) from None

            await self.member_repository.set_relationship(
                club,
                user,
                ClubMembershipEnum.left,
            )


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
        async with self.transaction():
            return await self.repository.set_relationship(club, user, membership)


class ClubUpdateRequestService(
    ServiceBase[
        ClubUpdateRequest,
        ClubUpdateRequestCreate,
        RequestModerate,
    ],
):
    repository: ClubUpdateRequestRepository

    def __init__(
        self,
        repository: ClubUpdateRequestRepository,
        club_repository: ClubRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.club_repository = club_repository or ClubRepository(repository.db)

    async def get_pending_requests(self) -> Page[ClubUpdateRequest]:
        return await self.repository.get_pending_requests()

    async def count_pending_requests(self) -> int:
        return await self.repository.count_pending()

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

    async def approve_club_update_request(
        self,
        request_id: int,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> ClubUpdateRequest:
        async with self.transaction():
            request = await self._get_with_lock(request_id)
            if request is None:
                raise ResourceNotFoundError(
                    "error.club_update_request.not_found",
                    "CLUB_UPDATE_REQUEST_NOT_FOUND",
                ) from None
            if request.moderation_status != ModerationStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.club_update_request.moderated",
                    "CLUB_UPDATE_REQUEST_MODERATED",
                ) from None

            club = await self.club_repository.get(request.club_id)
            if club is None or club.status != ClubStatusEnum.normal:
                raise ClubNotFoundError(request.club_id) from None

            if moderation.moderation_status == ModerationStatusEnum.approved:
                await self.club_repository.update(
                    club,
                    build_update_payload(request, AdminClubUpdate),
                )

            return await self.moderate_request(request, moderation, moderator)

    async def supersede_pending_requests_by_club(self, club_id: int) -> None:
        try:
            async with self.transaction():
                await self.repository.supersede_pending_requests_by_club(club_id)
        except IntegrityError:
            raise DuplicatePendingRequestError from None
