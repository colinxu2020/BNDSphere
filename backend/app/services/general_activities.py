from collections.abc import Sequence

from sqlalchemy import select

from app.models import GeneralActivity
from app.models.general_activity import GeneralActivityLevelEnum
from app.schemas.general_activities import GeneralActivityCreate, GeneralActivityUpdate
from app.services.base import ServiceBase


class GenericActivityService(
    ServiceBase[GeneralActivity, GeneralActivityCreate, GeneralActivityUpdate],
):
    model = GeneralActivity

    async def get_multi(
        self,
        search: str | None = None,
        level: GeneralActivityLevelEnum | None = None,
    ) -> Sequence[GeneralActivity]:
        stmt = select(self.model).order_by(GeneralActivity.created_at.desc())
        if level is not None:
            stmt = stmt.where(self.model.level == level)
        if search is not None:
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
        result = await self.db.execute(stmt)
        return result.scalars().all()
