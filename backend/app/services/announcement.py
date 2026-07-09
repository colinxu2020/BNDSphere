from datetime import datetime

from fastapi_pagination import Page

from app.models.announcement import Announcement
from app.repositories.announcement import AnnouncementRepository
from app.schemas.announcements import AnnouncementCreate, AnnouncementUpdate
from app.services.base import ServiceBase


class AnnouncementService(
    ServiceBase[Announcement, AnnouncementCreate, AnnouncementUpdate],
):
    repository: AnnouncementRepository

    async def get_multi(
        self,
        search: str | None = None,
        *,
        active_only: bool = False,
        at_time: datetime | None = None,
    ) -> Page[Announcement]:
        return await self.repository.get_multi(
            search,
            active_only=active_only,
            at_time=at_time,
        )
