from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select

from app.models.club_activity_check_in import ClubActivityCheckIn
from app.repositories.base import RepositoryBase
from app.schemas.club_activity_check_in import ClubActivityCheckInCreate


class ClubActivityCheckInRepository(
    RepositoryBase[
        ClubActivityCheckIn,
        ClubActivityCheckInCreate,
        ClubActivityCheckInCreate,
    ],
):
    model = ClubActivityCheckIn

    async def get_by_activity(
        self,
        club_activity_id: int,
    ) -> Page[ClubActivityCheckIn]:
        stmt = (
            select(ClubActivityCheckIn)
            .where(ClubActivityCheckIn.club_activity_id == club_activity_id)
            .order_by(ClubActivityCheckIn.checked_in_at.asc())
        )
        return cast("Page[ClubActivityCheckIn]", await apaginate(self.db, stmt))

    async def get_checked_in_user_ids(self, club_activity_id: int) -> set[int]:
        stmt = select(ClubActivityCheckIn.user_id).where(
            ClubActivityCheckIn.club_activity_id == club_activity_id,
        )
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def get_by_activity_user(
        self,
        club_activity_id: int,
        user_id: int,
    ) -> ClubActivityCheckIn | None:
        stmt = select(ClubActivityCheckIn).where(
            ClubActivityCheckIn.club_activity_id == club_activity_id,
            ClubActivityCheckIn.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
