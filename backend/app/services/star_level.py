from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select

from app.models import Club
from app.models.star_level import StarLevelApplication
from app.schemas.star_level import (
    StarLevelApplicationCreate,
    StarLevelApplicationUpdate,
)
from app.services.base import ServiceBase


class StarLevelService(
    ServiceBase[
        StarLevelApplication,
        StarLevelApplicationCreate,
        StarLevelApplicationUpdate,
    ],
):
    model = StarLevelApplication

    async def list_by_club(self, club: Club) -> Page[StarLevelApplication]:
        return await apaginate(
            self.db,
            select(self.model)
            .where(self.model.club_id == club.id)
            .order_by(self.model.created_at.desc()),
        )
