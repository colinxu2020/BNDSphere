from datetime import UTC, datetime
from typing import override

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash, verify_password
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

    async def supersede_pending_requests_by_user(self, user_id: int) -> None:
        try:
            await self.repository.supersede_pending_requests_by_user(user_id)
        except IntegrityError:
            raise DuplicatePendingRequestError from None
