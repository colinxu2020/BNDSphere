from collections.abc import Callable
from typing import Final

from sqlalchemy import Constraint, Index, MetaData, Table
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.schema import ColumnCollectionConstraint

from .settings import settings

engine: Final[AsyncEngine] = create_async_engine(settings.database_url)
SessionLocal: Final[async_sessionmaker[AsyncSession]] = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def all_column_names(constraint: Constraint | Index, table: Table) -> str:
    column_names = []
    if isinstance(constraint, (Index, ColumnCollectionConstraint)):
        for col in constraint.columns:
            if hasattr(col, "name") and col.name:
                column_names.append(col.name)
            else:
                raise ValueError(
                    f"Naming convention execution failed for table '{table.name}':\n"
                    f"You MUST explicitly pass a 'name' parameter.",
                )
    return "_".join(column_names)


convention: Final[dict[str, str | Callable[[Constraint | Index, Table], str]]] = {
    "all_cols": all_column_names,
    "ix": "ix_%(table_name)s_%(all_cols)s",
    "uq": "uq_%(table_name)s_%(all_cols)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(all_cols)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
