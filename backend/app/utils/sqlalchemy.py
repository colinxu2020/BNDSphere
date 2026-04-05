from collections.abc import Sequence
from typing import Any

from sqlalchemy import Column, Insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


def get_dialect(db: AsyncSession) -> str:
    return db.bind.dialect.name


def get_upsert_insert(
    db: AsyncSession,
    model: type[Base],
    index_elements: Sequence[Column],
    update_map: dict[str, Any],
) -> Insert:
    dialect = get_dialect(db)
    if dialect == "postgresql":
        return pg_insert(model).on_conflict_do_update(
            index_elements=index_elements,
            set_=update_map,
        )
    if dialect == "sqlite":
        return sqlite_insert(model).on_conflict_do_update(
            index_elements=index_elements,
            set_=update_map,
        )
    if dialect == "mysql":
        return mysql_insert(model).on_duplicate_key_update(**update_map)
    raise NotImplementedError(f"Upsert is not implemented for {dialect}")
