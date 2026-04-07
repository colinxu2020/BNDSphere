import operator
from collections.abc import Sequence
from functools import reduce
from typing import Any

from sqlalchemy import Column, Insert, func, or_
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

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


def apply_fulltext_search(
    stmt: Select,
    dialect: str,
    search: str,
    search_fields: dict,
    default_order_by: Any,  # noqa: ANN401
) -> Select:
    if dialect == "postgresql":
        score_func = reduce(
            operator.add,
            [
                func.similarity(col, search) * weight
                for col, weight in search_fields.items()
            ],
        )
        conditions = or_(*(col.bool_op("%")(search) for col in search_fields))
        return stmt.where(conditions).order_by(score_func.desc())

    if dialect == "mysql":
        score_func = reduce(
            operator.add,
            [
                func.match(col).op("against")(search) * weight
                for col, weight in search_fields.items()
            ],
        )
        conditions = or_(*(col.match(search) for col in search_fields))
        return stmt.where(conditions).order_by(score_func.desc())

    conditions = or_(*(col.contains(search) for col in search_fields))
    return stmt.where(conditions).order_by(default_order_by)
