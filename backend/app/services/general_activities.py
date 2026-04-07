from collections.abc import Sequence

from sqlalchemy import select

from app.models import Club, GeneralActivity
from app.models.general_activity import (
    ClubGeneralActivityRecord,
    GeneralActivityLevelEnum,
)
from app.schemas.general_activities import (
    ClubGeneralActivityCreate,
    ClubGeneralActivityUpdate,
    GeneralActivityCreate,
    GeneralActivityUpdate,
)
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


class ClubGenericActivityService(
    ServiceBase[
        ClubGeneralActivityRecord,
        ClubGeneralActivityCreate,
        ClubGeneralActivityUpdate,
    ],
):
    model = ClubGeneralActivityRecord

    async def create_club_general_activity(
        self,
        obj_in: ClubGeneralActivityCreate,
        club_id: int,
    ) -> ClubGeneralActivityRecord:
        db_obj = self.model(**obj_in.model_dump(), club_id=club_id)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def get_by_club(self, club: Club) -> Sequence[ClubGeneralActivityRecord]:
        stmt = select(self.model).where(self.model.club == club)
        result = await self.db.execute(stmt)
        return result.scalars().all()
