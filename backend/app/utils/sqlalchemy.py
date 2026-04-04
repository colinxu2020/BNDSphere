from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from sqlalchemy.dialects.postgresql import Insert as PGInsert
    from sqlalchemy.dialects.sqlite import Insert as SQLiteInsert


from app.core.database import Base


def get_upsert_insert(db: AsyncSession, model: type[Base]) -> PGInsert | SQLiteInsert:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(model)
    if dialect == "sqlite":
        return sqlite_insert(model)
    raise NotImplementedError(f"Upsert is not implemented for {dialect}")
