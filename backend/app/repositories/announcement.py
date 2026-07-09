from datetime import datetime
from typing import cast

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select

from app.models.announcement import Announcement
from app.repositories.base import RepositoryBase
from app.schemas.announcements import AnnouncementCreate, AnnouncementUpdate


class AnnouncementRepository(
    RepositoryBase[Announcement, AnnouncementCreate, AnnouncementUpdate],
):
    model = Announcement

    async def get_multi(
        self,
        search: str | None = None,
        *,
        active_only: bool = False,
        at_time: datetime | None = None,
    ) -> Page[Announcement]:
        stmt = select(self.model).order_by(
            Announcement.created_at.desc(),
            Announcement.id.desc(),
        )
        if search is not None:
            stmt = stmt.where(self.model.title.ilike(f"%{search}%"))
        if active_only:
            stmt = stmt.where(self.model.is_active.is_(True))
        if at_time is not None:
            stmt = stmt.where(
                (self.model.starts_at.is_(None) | (self.model.starts_at <= at_time)),
                (self.model.ends_at.is_(None) | (self.model.ends_at >= at_time)),
            )
        return cast("Page[Announcement]", await apaginate(self.db, stmt))
