from datetime import UTC, datetime
from typing import cast, override

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash, verify_password
from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.moderations.user_update_request import UserUpdateRequest
from app.models.user import User
from app.schemas.moderations.moderation_common import (
    RequestModerate,
    RequestModeratePublic,
)
from app.schemas.moderations.user_update_request import (
    UserUpdateUpdateRequestCreate,
)
from app.schemas.user import AdminUserUpdate, UserCreate
from app.services.base import ServiceBase
from app.services.errors import (
    DuplicatePendingRequestError,
    DuplicateResourceError,
)


class UserService(ServiceBase[User, UserCreate, AdminUserUpdate]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalars().first()

    async def authenticate(self, username: str, password: str) -> User | None:
        result = await self.get_by_username(username)
        if not result or not verify_password(password, result.hashed_password):
            return None
        return result

    @override
    async def create(self, obj_in: UserCreate, **kwargs: object) -> User:
        hashed_password = get_password_hash(obj_in.password)
        db_obj = self.model(
            username=obj_in.username,
            hashed_password=hashed_password,
            **kwargs,
        )
        try:
            self.db.add(db_obj)
            await self.db.flush()
            await self.db.refresh(db_obj)
        except IntegrityError:
            raise DuplicateResourceError(
                message_key="error.user.duplicate_username",
                error_code="DUPLICATE_USERNAME",
                details={"username": obj_in.username},
            ) from None
        else:
            return db_obj

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
        UserUpdateUpdateRequestCreate,
        RequestModerate,
    ],
):
    model = UserUpdateRequest

    async def get_pending_requests(self) -> Page[UserUpdateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[UserUpdateRequest]", await apaginate(self.db, stmt))

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
        stmt = (
            update(self.model)
            .where(
                self.model.moderation_status == ModerationStatusEnum.pending,
                self.model.user_id == user_id,
            )
            .values(moderate_status=ModerationStatusEnum.superseded)
        )
        try:
            await self.db.execute(stmt)
            await self.db.flush()
        except IntegrityError:
            raise DuplicatePendingRequestError from None
