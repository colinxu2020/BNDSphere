from fastapi_pagination import Page

from app.models import Club
from app.models.star_level import StarLevelApplication
from app.repositories.star_level import StarLevelRepository
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
    repository: StarLevelRepository

    async def list_by_club(self, club: Club) -> Page[StarLevelApplication]:
        return await self.repository.list_by_club(club)
