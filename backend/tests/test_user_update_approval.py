from typing import cast

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.moderations.user_update_request import UserUpdateRequest
from app.models.user import User
from app.repositories.user import UserRepository, UserUpdateRequestRepository
from app.schemas.moderations.moderation_common import RequestModeratePublic
from app.schemas.user import AdminUserUpdate
from app.services.errors import DuplicateResourceError
from app.services.user import UserUpdateRequestService


class TransactionlessSession:
    def __init__(self) -> None:
        self.info: dict[str, object] = {}

    def in_transaction(self) -> bool:
        return False


class ExistingUpdateRequestRepository:
    def __init__(self, request: UserUpdateRequest) -> None:
        self.db = TransactionlessSession()
        self.request = request

    async def get_with_lock(self, request_id: int) -> UserUpdateRequest | None:
        if request_id == self.request.id:
            return self.request
        return None


class ConflictingUserRepository:
    def __init__(self, user: User) -> None:
        self.user = user

    async def get(self, user_id: int) -> User | None:
        if user_id == self.user.id:
            return self.user
        return None

    async def update(self, user: User, update: AdminUserUpdate) -> User:
        raise IntegrityError(
            "UPDATE users SET username = ...",
            {"username": update.username},
            Exception("duplicate key value violates unique constraint"),
        )


async def test_approval_translates_a_stale_username_collision() -> None:
    request = UserUpdateRequest(
        id=17,
        user_id=4,
        username="already-taken",
        update_fields=["username"],
        moderation_status=ModerationStatusEnum.pending,
    )
    request_repository = ExistingUpdateRequestRepository(request)
    user_repository = ConflictingUserRepository(
        User(
            id=4,
            username="old-name",
            hashed_password="unused",  # noqa: S106
        ),
    )
    service = UserUpdateRequestService(
        cast("UserUpdateRequestRepository", request_repository),
        user_repository=cast("UserRepository", user_repository),
    )
    moderation = RequestModeratePublic(moderation_status=ModerationStatusEnum.approved)
    moderator = User(
        id=11,
        username="reviewer",
        hashed_password="unused",  # noqa: S106
    )

    with pytest.raises(DuplicateResourceError) as exc_info:
        await service.approve_user_update_request(request.id, moderation, moderator)

    assert exc_info.value.error_code == "DUPLICATE_USERNAME"
    assert exc_info.value.details == {"username": "already-taken"}
