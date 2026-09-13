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

    async def get_multi(self, search: str | None = None) -> Page[ResourceFile]:
        stmt = select(self.model).order_by(
            ResourceFile.created_at.desc(),
            ResourceFile.id.desc(),
        )
        if search is not None:
            stmt = stmt.where(self.model.filename.ilike(f"%{search}%"))
        return cast("Page[ResourceFile]", await apaginate(self.db, stmt))

    async def get_by_object_key(self, object_key: str) -> ResourceFile | None:
        result = await self.db.execute(
            select(self.model).where(self.model.object_key == object_key),
        )
        return result.scalars().first()
