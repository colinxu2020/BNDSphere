from typing import Final

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase

from .settings import settings

engine: Final[AsyncEngine] = create_async_engine(settings.database_url)
SessionLocal: Final[async_sessionmaker[AsyncSession]] = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass
