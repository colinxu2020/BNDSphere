from datetime import UTC, datetime
from typing import override

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash, verify_password
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.moderations.user_update_request import UserUpdateRequest
from app.models.user import User
from app.repositories.user import UserRepository, UserUpdateRequestRepository
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.schemas.moderations.user_update_request import (
    UserUpdateRequestCreate,
)
from app.schemas.user import AdminUserUpdate, UserCreate
from app.services.base import ServiceBase
from app.services.errors import (
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


class UserService(
    ServiceBase[User, UserCreate, AdminUserUpdate],
):
    repository: UserRepository

    async def get_by_email(self, email: str) -> User | None:
        return await self.repository.get_by_email(email)

    async def get_by_username(self, username: str) -> User | None:
        return await self.repository.get_by_username(username)

    async def authenticate(self, username: str, password: str) -> User | None:
        result = await self.get_by_username(username)
        if not result or not verify_password(password, result.hashed_password):
            return None
        return result

    @override
    async def create(self, obj_in: UserCreate, **kwargs: object) -> User:
        hashed_password = get_password_hash(obj_in.password)
        try:
            async with self.transaction():
                return await self.repository.create_with_hashed_password(
                    obj_in.username,
                    hashed_password,
                    **kwargs,
                )
        except IntegrityError:
            raise DuplicateResourceError(
                message_key="error.user.duplicate_username",
                error_code="DUPLICATE_USERNAME",
                details={"username": obj_in.username},
            ) from None

    @override
    async def update(self, db_obj: User, obj_in: AdminUserUpdate) -> User:
        try:
            return await super().update(db_obj, obj_in)
        except IntegrityError:
            raise DuplicateResourceError(
                message_key="error.user.duplicate_email",
                error_code="DUPLICATE_EMAIL",
                details={"email": obj_in.email},
            ) from None


class UserUpdateRequestService(
    ServiceBase[
        UserUpdateRequest,
        UserUpdateRequestCreate,
        RequestModerate,
    ],
):
    repository: UserUpdateRequestRepository

    def __init__(
        self,
        repository: UserUpdateRequestRepository,
        user_repository: UserRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.user_repository = user_repository or UserRepository(repository.db)

    async def get_pending_requests(self) -> Page[UserUpdateRequest]:
        return await self.repository.get_pending_requests()

    async def moderate_request(
        self,
        request: UserUpdateRequest,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> UserUpdateRequest:
        return await self.update(
            request,
            RequestModerate(
                **moderation.model_dump(),
                moderator_id=moderator.id,
                moderate_at=datetime.now(tz=UTC),
            ),
        )

    async def request_profile_update(
        self,
        obj_in: UserUpdateRequestCreate,
        user: User,
    ) -> UserUpdateRequest:
        try:
            async with self.transaction():
                await self.repository.supersede_pending_requests_by_user(user.id)
                return await self.create(
                    obj_in.model_copy(
                        update={"update_fields": requested_update_fields(obj_in)},
                    ),
                    user_id=user.id,
                )
        except IntegrityError:
            raise DuplicatePendingRequestError from None

    async def approve_user_update_request(
        self,
        request_id: int,
        moderation: RequestModeratePublic,
        moderator: User,
    ) -> UserUpdateRequest:
        async with self.transaction():
            request = await self._get_with_lock(request_id)
            if request is None:
                raise ResourceNotFoundError(
                    "error.user_update_request.not_found",
                    "USER_UPDATE_REQUEST_NOT_FOUND",
                ) from None
            if request.moderation_status != ModerationStatusEnum.pending:
                raise ResourceForbiddenError(
                    "error.user_update_request.moderated",
                    "USER_UPDATE_REQUEST_MODERATED",
                ) from None

            request_user = await self.user_repository.get(request.user_id)
            if request_user is None:
                raise UserNotFoundError(request.user_id) from None

            if moderation.moderation_status == ModerationStatusEnum.approved:
                await self.user_repository.update(
                    request_user,
                    build_update_payload(request, AdminUserUpdate),
                )

            return await self.moderate_request(request, moderation, moderator)

    async def supersede_pending_requests_by_user(self, user_id: int) -> None:
        try:
            async with self.transaction():
                await self.repository.supersede_pending_requests_by_user(user_id)
        except IntegrityError:
            raise DuplicatePendingRequestError from None
