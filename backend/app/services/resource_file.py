from collections.abc import Sequence
from datetime import UTC, datetime
from typing import override

from fastapi_pagination import Page
from sqlalchemy.exc import IntegrityError

from app.models.resource_file import ResourceFile
from app.repositories.resource_file import ResourceFileRepository
from app.schemas.resource_files import ResourceFileCreate, ResourceFileUpdate
from app.services.base import ServiceBase
from app.services.errors import DuplicateResourceError


class ResourceFileService(
    ServiceBase[ResourceFile, ResourceFileCreate, ResourceFileUpdate],
):
    repository: ResourceFileRepository

    async def get_multi(self, search: str | None = None) -> Page[ResourceFile]:
        return await self.repository.get_multi(search)

    async def get_pending_deletions(self) -> Sequence[ResourceFile]:
        return await self.repository.get_pending_deletions()

    async def get_by_object_key(self, object_key: str) -> ResourceFile | None:
        return await self.repository.get_by_object_key(object_key)

    @override
    async def create(
        self,
        obj_in: ResourceFileCreate,
        **kwargs: object,
    ) -> ResourceFile:
        try:
            return await super().create(obj_in, **kwargs)
        except IntegrityError:
            raise DuplicateResourceError(
                "error.resource_file.already_registered",
                "RESOURCE_FILE_ALREADY_REGISTERED",
                {"object_key": obj_in.object_key},
            ) from None

    async def prepare_deletion(self, resource_id: int) -> ResourceFile | None:
        """Hide a resource durably before its object is removed."""
        async with self.transaction():
            resource_file = await self._get_with_lock(resource_id)
            if (
                resource_file is not None
                and resource_file.deletion_requested_at is None
            ):
                resource_file.deletion_requested_at = datetime.now(tz=UTC)
                await self.repository.db.flush()
            return resource_file

    async def finish_deletion(self, resource_id: int) -> None:
        """Remove a resource record after object deletion succeeds."""
        async with self.transaction():
            resource_file = await self._get_with_lock(resource_id)
            if resource_file is not None:
                await self.repository.delete(resource_file)
