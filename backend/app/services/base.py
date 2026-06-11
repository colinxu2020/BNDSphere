from pydantic import BaseModel

from app.core.database import Base
from app.repositories.base import RepositoryBase


class ServiceBase[
    ModelType: Base,
    CreateSchemaType: BaseModel,
    UpdateSchemaType: BaseModel,
]:  # fmt: skip
    repository: RepositoryBase[ModelType, CreateSchemaType, UpdateSchemaType]

    def __init__(
        self,
        repository: RepositoryBase[ModelType, CreateSchemaType, UpdateSchemaType],
    ) -> None:
        self.repository = repository

    async def get(self, id_: int) -> ModelType | None:
        return await self.repository.get(id_)

    async def get_with_lock(self, id_: int) -> ModelType | None:
        """获取资源, 并在事务级别加排他锁."""
        return await self.repository.get_with_lock(id_)

    async def create(self, obj_in: CreateSchemaType, **kwargs: object) -> ModelType:
        return await self.repository.create(obj_in, **kwargs)

    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        return await self.repository.update(db_obj, obj_in)

    async def delete(self, db_obj: ModelType) -> None:
        await self.repository.delete(db_obj)
