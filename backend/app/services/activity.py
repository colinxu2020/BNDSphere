from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Club
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.schemas.generic import PageResponse
from app.services.base import ServiceBase


class ActivityService(ServiceBase[Activity, ActivityCreate, ActivityUpdate]):
    model = Activity

    async def get_club_activities(
        self,
        club: Club,
        offset: int,
        limit: int,
    ) -> PageResponse[Sequence[Activity]]:
        result = await self.db.execute(
            select(func.count())
            .select_from(Activity)
            .where(Activity.club_id == club.id),
        )
        count = result.scalar_one()
        result = await self.db.execute(
            select(Activity)
            .where(Activity.club_id == club.id)
            .offset(offset)
            .limit(limit)
            .order_by(Activity.start_time.desc(), Activity.id.desc())
            .options(selectinload(Activity.participators)),
        )
        return PageResponse(total=count, items=result.scalars().all())

    async def create_club_activity(
        self,
        club_id: int,
        obj_in: ActivityCreate,
    ) -> Activity:
        db_activity = Activity(**obj_in.model_dump(), club_id=club_id)
        self.db.add(db_activity)
        await self.db.commit()
        return db_activity
