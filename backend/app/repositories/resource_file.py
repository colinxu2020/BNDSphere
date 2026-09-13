from collections.abc import Sequence
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select

from app.models.resource_file import ResourceFile
from app.repositories.base import RepositoryBase
from app.schemas.resource_files import ResourceFileCreate, ResourceFileUpdate


class ResourceFileRepository(
    RepositoryBase[ResourceFile, ResourceFileCreate, ResourceFileUpdate],
):
    model = ResourceFile

    async def get(self, id_: int) -> ResourceFile | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == id_,
                self.model.deletion_requested_at.is_(None),
            ),
        )
        return result.scalars().first()

    async def get_multi(self, search: str | None = None) -> Page[ResourceFile]:
        stmt = (
            select(self.model)
            .where(self.model.deletion_requested_at.is_(None))
            .order_by(
                ResourceFile.created_at.desc(),
                ResourceFile.id.desc(),
            )
        )
        if search is not None:
            stmt = stmt.where(self.model.filename.ilike(f"%{search}%"))
        return cast("Page[ResourceFile]", await apaginate(self.db, stmt))

    async def get_pending_deletions(self) -> Sequence[ResourceFile]:
        stmt = (
            select(self.model)
            .where(self.model.deletion_requested_at.is_not(None))
            .order_by(
                ResourceFile.deletion_requested_at.asc(),
                ResourceFile.id.asc(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_object_key(self, object_key: str) -> ResourceFile | None:
        result = await self.db.execute(
            select(self.model).where(self.model.object_key == object_key),
        )
        return result.scalars().first()
