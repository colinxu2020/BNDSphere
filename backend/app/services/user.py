from typing import override

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import ServiceBase
from app.services.errors import DuplicateEmailError, DuplicateUsernameError


class UserService(ServiceBase[User, UserCreate, UserUpdate]):
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
        except IntegrityError as exc:
            raise DuplicateUsernameError from exc
        else:
            return db_obj

    @override
    async def update(self, db_obj: User, obj_in: UserUpdate) -> User:
        try:
            return await super().update(db_obj, obj_in)
        except IntegrityError as exc:
            raise DuplicateEmailError from exc
