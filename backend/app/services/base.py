from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


class ServiceBase[
    ModelType: Base,
    CreateSchemaType: BaseModel,
    UpdateSchemaType: BaseModel,
]:
    model: type[ModelType]
    db: AsyncSession

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id_: int) -> ModelType | None:
        result = await self.db.execute(select(self.model).filter(self.model.id == id_))
        return result.scalars().first()

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
