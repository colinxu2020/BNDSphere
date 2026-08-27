from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models.club import Club, ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMember, ClubMembershipEnum
from app.models.moderations.club import ClubUpdateRequest
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.user import User
from app.models.verifications.club_membership import ClubMembershipRequest
from app.models.verifications.verification_common import VerificationStatusEnum
from app.repositories.club import (
    ClubMemberRepository,
    ClubMembershipRequestRepository,
    ClubRepository,
    ClubUpdateRequestRepository,
)
from app.repositories.user import UserRepository
from app.schemas.club import (
    AdminClubUpdate,
    ClubCreate,
    ClubMemberRoleUpdate,
    ClubMemberUpdate,
    ClubUpdate,
)
from app.schemas.moderations.club import (
    ClubUpdateRequestCreate,
    ClubUpdateRequestCreatePublic,
)
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.schemas.verifications.club_membership import (
    ClubMembershipRequestCreate,
    ClubMembershipRequestCreatePublic,
)
from app.schemas.verifications.verification_common import (
    RequestVerify,
    RequestVerifyPublic,
)
from app.services.base import ServiceBase
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicatePendingRequestError,
    DuplicateResourceError,
    ResourceForbiddenError,
    ResourceNotFoundError,
    UserNotFoundError,
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
        membership_request_repository: ClubMembershipRequestRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.member_repository = member_repository or ClubMemberRepository(
            repository.db,
        )
        self.update_request_repository = (
            update_request_repository or ClubUpdateRequestRepository(repository.db)
        )
        self.membership_request_repository = (
            membership_request_repository
            or ClubMembershipRequestRepository(repository.db)
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

    async def get_managed_by_user(self, user: User) -> Page[Club]:
        return await self.repository.get_managed_by_user(user.id)

    async def get_manageable_club(self, club_id: int) -> Club:
        club = await self.get(club_id)
        if club is None:
            raise ClubNotFoundError(club_id) from None
        if club.status == ClubStatusEnum.archived:
            raise ResourceForbiddenError(
                "error.club.not_active",
                "CLUB_NOT_ACTIVE",
                {"club_id": club_id},
            ) from None
        return club

    async def update_unreviewed_club(
        self,
        club_id: int,
        obj_in: ClubUpdate,
    ) -> Club:
        async with self.transaction():
            club = await self.repository.get_with_lock(club_id)
            if club is None:
                raise ClubNotFoundError(club_id) from None
            if club.status != ClubStatusEnum.unreviewed:
                raise ResourceForbiddenError(
                    "error.club.update_requires_review",
                    "CLUB_UPDATE_REQUIRES_REVIEW",
                    {"club_id": club_id},
                ) from None
            return await self.repository.update_details(club, obj_in)

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

    async def request_join_club(
        self,
        club_id: int,
        user: User,
        obj_in: ClubMembershipRequestCreatePublic,
    ) -> ClubMembershipRequest:
        try:
            async with self.transaction():
                club = await self.ensure_club_normal(club_id)
                relationship = await self.member_repository.get_by_club_user(club, user)
                if relationship and relationship.membership != ClubMembershipEnum.left:
                    raise DuplicateResourceError(
                        message_key="error.club.duplicate_join_request",
                        error_code="DUPLICATE_JOIN_REQUEST",
                    ) from None

                return await self.membership_request_repository.create(
                    ClubMembershipRequestCreate(
                        **obj_in.model_dump(exclude_unset=True),
                        club_id=club_id,
                        applicant_id=user.id,
                    ),
                )
        except IntegrityError:
            raise DuplicatePendingRequestError from None

    async def leave_club(self, club_id: int, user: User) -> None:
        async with self.transaction():
            club = await self._get_locked_active_club(club_id)
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

    async def update_member_role(
        self,
        club_id: int,
        target_user_id: int,
        obj_in: ClubMemberRoleUpdate,
        president: User,
    ) -> ClubMember:
        async with self.transaction():
            club = await self._get_locked_active_club(club_id)
            president_membership = await self._ensure_president(club, president)
            target = await self._get_active_member(club, target_user_id)
            desired_membership = ClubMembershipEnum(obj_in.membership.value)

            if target.user_id == president.id:
                if desired_membership == ClubMembershipEnum.president:
                    return target
                raise ResourceForbiddenError(
                    "error.club.cannot_change_president_role",
                    "CANNOT_CHANGE_PRESIDENT_ROLE",
                    {"club_id": club_id},
                ) from None

            if desired_membership == ClubMembershipEnum.president:
                await self.member_repository.set_membership(
                    president_membership,
                    ClubMembershipEnum.member,
                )

            return await self.member_repository.set_membership(
                target,
                desired_membership,
            )

    async def remove_member(
        self,
        club_id: int,
        target_user_id: int,
        president: User,
    ) -> None:
        async with self.transaction():
            club = await self._get_locked_active_club(club_id)
            await self._ensure_president(club, president)
            target = await self._get_active_member(club, target_user_id)
            if target.membership == ClubMembershipEnum.president:
                raise ResourceForbiddenError(
                    "error.club.cannot_remove_president",
                    "CANNOT_REMOVE_PRESIDENT",
                    {"club_id": club_id},
                ) from None
            await self.member_repository.set_membership(
                target,
                ClubMembershipEnum.left,
            )

    async def _get_locked_active_club(self, club_id: int) -> Club:
        club = await self.repository.get_with_lock(club_id)
        if club is None:
            raise ClubNotFoundError(club_id) from None
        if club.status != ClubStatusEnum.normal:
            raise ResourceForbiddenError(
                "error.club.not_active",
                "CLUB_NOT_ACTIVE",
                {"club_id": club_id},
            ) from None
        return club

    async def _ensure_president(self, club: Club, user: User) -> ClubMember:
        membership = await self.member_repository.get_by_club_user(club, user)
        if membership is None or membership.membership != ClubMembershipEnum.president:
            raise ResourceForbiddenError(
                "error.club.president_required",
                "CLUB_PRESIDENT_REQUIRED",
                {"club_id": club.id},
            ) from None
        return membership

    async def _get_active_member(self, club: Club, user_id: int) -> ClubMember:
        membership = await self.member_repository.get_by_club_user_id(
            club.id,
            user_id,
        )
        if membership is None or membership.membership not in {
            ClubMembershipEnum.member,
            ClubMembershipEnum.vice_president,
            ClubMembershipEnum.president,
        }:
            raise ResourceNotFoundError(
                "error.club.member_not_found",
                "CLUB_MEMBER_NOT_FOUND",
                {"club_id": club.id, "user_id": user_id},
            ) from None
        return membership


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


class ClubMembershipRequestService(
    ServiceBase[
        ClubMembershipRequest,
        ClubMembershipRequestCreate,
        RequestVerify,
    ],
):
    repository: ClubMembershipRequestRepository

    def __init__(
        self,
        repository: ClubMembershipRequestRepository,
        club_repository: ClubRepository | None = None,
        member_repository: ClubMemberRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.club_repository = club_repository or ClubRepository(repository.db)
        self.member_repository = member_repository or ClubMemberRepository(
            repository.db,
        )
        self.user_repository = user_repository or UserRepository(repository.db)

    async def get_pending_requests(
        self,
        club_id: int,
    ) -> Page[ClubMembershipRequest]:
        return await self.repository.get_pending_requests(club_id)

    async def verify_request(
        self,
        request: ClubMembershipRequest,
        verification: RequestVerifyPublic,
        verifier: User,
    ) -> ClubMembershipRequest:
        return await self.update(
            request,
            RequestVerify(
                **verification.model_dump(),
                verifier_id=verifier.id,
                verify_at=datetime.now(tz=UTC),
            ),
        )

    async def verify_membership_request(
        self,
        club_id: int,
        request_id: int,
        verification: RequestVerifyPublic,
        verifier: User,
    ) -> ClubMembershipRequest:
        async with self.transaction():
            request = await self._get_with_lock(request_id)
            if request is None or request.club_id != club_id:
                raise ResourceNotFoundError(
                    "error.club_membership_request.not_found",
                    "CLUB_MEMBERSHIP_REQUEST_NOT_FOUND",
                ) from None
            if request.verification_status != VerificationStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.club_membership_request.verified",
                    "CLUB_MEMBERSHIP_REQUEST_VERIFIED",
                ) from None

            club = await self.club_repository.get(request.club_id)
            if club is None:
                raise ClubNotFoundError(request.club_id) from None
            if club.status != ClubStatusEnum.normal:
                raise ResourceForbiddenError(
                    "error.club.not_active",
                    "CLUB_NOT_ACTIVE",
                    {"club_id": request.club_id},
                ) from None

            if verification.verification_status == VerificationStatusEnum.approved:
                applicant = await self.user_repository.get(request.applicant_id)
                if applicant is None:
                    raise UserNotFoundError(request.applicant_id) from None
                await self.member_repository.set_relationship(
                    club,
                    applicant,
                    ClubMembershipEnum.member,
                )

            return await self.verify_request(request, verification, verifier)
