from typing import override

from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import ServiceBase


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
    async def create(self, user: UserCreate) -> User:
        hashed_password = get_password_hash(user.password)
        db_obj = self.model(
            username=user.username,
            hashed_password=hashed_password,
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
