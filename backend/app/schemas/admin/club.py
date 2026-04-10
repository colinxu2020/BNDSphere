from pydantic import Field

from app.models.club import ClubStarLevelEnum, ClubStatusEnum
from app.schemas.club import ClubUpdate


class AdminClubUpdate(ClubUpdate):
    status: ClubStatusEnum = Field(...)
    star_level: ClubStarLevelEnum = Field(...)
