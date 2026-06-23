from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select, update

from app.models.moderations.moderation_common import ModerationStatusEnum
from app.models.moderations.user_update_request import UserUpdateRequest
from app.models.user import User
from app.repositories.base import RepositoryBase
from app.schemas.moderations.moderation_common import RequestModerate
from app.schemas.moderations.user_update_request import UserUpdateRequestCreate
from app.schemas.user import AdminUserUpdate, UserCreate


class UserRepository(RepositoryBase[User, UserCreate, AdminUserUpdate]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalars().first()

    async def create_with_hashed_password(
        self,
        username: str,
        hashed_password: str,
        **kwargs: object,
    ) -> User:
        db_obj = self.model(
            username=username,
            hashed_password=hashed_password,
            **kwargs,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj


class UserUpdateRequestRepository(
    RepositoryBase[
        UserUpdateRequest,
        UserUpdateRequestCreate,
        RequestModerate,
    ],
):
    model = UserUpdateRequest

    async def get_pending_requests(self) -> Page[UserUpdateRequest]:
        stmt = select(self.model).where(
            self.model.moderation_status == ModerationStatusEnum.pending,
        )
        return cast("Page[UserUpdateRequest]", await apaginate(self.db, stmt))

    async def supersede_pending_requests_by_user(self, user_id: int) -> None:
        stmt = (
            update(self.model)
            .where(
                self.model.moderation_status == ModerationStatusEnum.pending,
                self.model.user_id == user_id,
            )
            .values(moderation_status=ModerationStatusEnum.superseded)
        )
        await self.db.execute(stmt)
        await self.db.flush()
