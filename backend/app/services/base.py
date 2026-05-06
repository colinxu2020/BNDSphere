from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


class ServiceBase[
    ModelType: Base,
    CreateSchemaType: BaseModel,
    UpdateSchemaType: BaseModel]:  # fmt: skip
    model: type[ModelType]
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id_: int) -> ModelType | None:
        result = await self.db.execute(select(self.model).filter(self.model.id == id_))
        return result.scalars().first()

    async def get_with_lock(self, id_: int) -> ModelType | None:
        """获取资源, 并在事务级别加排他锁."""
        result = await self.db.execute(
            select(self.model).filter(self.model.id == id_).with_for_update(),
        )
        return result.scalars().first()

    async def create(self, obj_in: CreateSchemaType, **kwargs: object) -> ModelType:
        db_obj = self.model(**obj_in.model_dump(), **kwargs)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        for field, value in obj_in.model_dump(
            exclude_unset=True,
            exclude_none=True,
        ).items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelType) -> None:
        await self.db.delete(db_obj)
        await self.db.flush()
