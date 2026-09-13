from fastapi_pagination import Page

from app.models.resource_file import ResourceFile
from app.repositories.resource_file import ResourceFileRepository
from app.schemas.resource_files import ResourceFileCreate, ResourceFileUpdate
from app.services.base import ServiceBase


class ResourceFileService(
    ServiceBase[ResourceFile, ResourceFileCreate, ResourceFileUpdate],
):
    repository: ResourceFileRepository

    async def get_multi(self, search: str | None = None) -> Page[ResourceFile]:
        return await self.repository.get_multi(search)

    async def get_by_object_key(self, object_key: str) -> ResourceFile | None:
        return await self.repository.get_by_object_key(object_key)
