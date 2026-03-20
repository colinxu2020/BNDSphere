import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        email=None,
        avatar_uri="https://files.seeusercontent.com/2026/03/20/S0pl/Text-2.png",
        description="这位用户还没有设置简介！",
        role=RoleEnum.user,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
    stmt = await db.execute(select(User).where(User.username == username))
    result = stmt.scalars().first()
    if not result or not verify_password(password, result.hashed_password):
        return None
    return result
