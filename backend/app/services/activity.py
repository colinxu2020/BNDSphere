from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Club
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.services.base import ServiceBase


class ActivityService(ServiceBase[Activity, ActivityCreate, ActivityUpdate]):
    model = Activity

    async def get_club_activities(
        self,
        club: Club,
        offset: int,
        limit: int,
    ) -> Page[Activity]:
        stmt = (
            select(Activity)
            .where(Activity.club_id == club.id)
            .offset(offset)
            .limit(limit)
            .order_by(Activity.start_time.desc(), Activity.id.desc())
            .options(selectinload(Activity.participators))
        )
        return await apaginate(self.db, stmt)

    async def create_club_activity(
        self,
        club_id: int,
        obj_in: ActivityCreate,
    ) -> Activity:
        db_activity = Activity(**obj_in.model_dump(), club_id=club_id)
        self.db.add(db_activity)
        await self.db.flush()
        await self.db.refresh(db_activity)
        return db_activity
