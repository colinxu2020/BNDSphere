from collections.abc import Sequence

from sqlalchemy import select

from app.models.activity import Activity
from app.schemas.activity import ActivityCreate, ActivityUpdate
from app.schemas.generic import PageResponse
from app.services.base import ServiceBase


class ActivityService(ServiceBase[Activity, ActivityCreate, ActivityUpdate]):
    model = Activity

    async def get_club_activities(
        self,
        club_id: int,
        offset: int,
        limit: int,
    ) -> PageResponse[Sequence[Activity]]:
        result = await self.db.execute(
            select(Activity).where(Activity.club_id == club_id),
        )
        count = result.scalar_one()
        result = await self.db.execute(
            select(Activity)
            .where(Activity.club_id == club_id)
            .offset(offset)
            .limit(limit),
        )
        return PageResponse(total=count, items=result.scalars().all())

    async def create_club_activity(self, obj_in: ActivityCreate) -> Activity:
        return await super().create(obj_in)
