from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserCreateHashed, UserUpdate
from app.services.base import ServiceBase


class UserService(ServiceBase[User, UserCreateHashed, UserUpdate]):
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

    async def register(self, user: UserCreate) -> User:
        hashed_password = get_password_hash(user.password)
        return await self.create(
            UserCreateHashed(username=user.username, hashed_password=hashed_password),
        )
