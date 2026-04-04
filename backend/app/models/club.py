from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.settings import settings
from app.utils.pydantic import HttpUrlType

if TYPE_CHECKING:
    from app.models.clubmember import ClubMember
    from app.models.tag import Tag
    from app.models.activity import Activity


class ClubStatusEnum(StrEnum):
    unreviewed = "unreviewed"
    normal = "normal"
    archived = "archived"


class ClubStarLevelEnum(StrEnum):
    none = "none"
    one_star = "one_star"
    two_star = "two_star"
    three_star = "three_star"
    four_star = "four_star"
    five_star = "five_star"
    honorary = "honorary"


class ClubCategoryEnum(StrEnum):
    sports = "sports"
    humanity = "humanity"
    arts = "arts"
    science = "science"
    charity = "charity"
    business = "business"
    campus = "campus"
    other = "other"


class Club(Base):
    __tablename__ = "clubs"

    name: Mapped[str] = mapped_column(
        String(settings.club_max_name_length),
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    logo_uri: Mapped[HttpUrl | None] = mapped_column(HttpUrlType, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    status: Mapped[ClubStatusEnum] = mapped_column(default=ClubStatusEnum.unreviewed)
    star_level: Mapped[ClubStarLevelEnum] = mapped_column(
        default=ClubStarLevelEnum.none,
    )
    category: Mapped[ClubCategoryEnum] = mapped_column()
    members: Mapped[list[ClubMember]] = relationship(back_populates="club")
    tags: Mapped[list[Tag]] = relationship(
        back_populates="clubs",
        secondary="club_tags",
    )
    activities: Mapped[list[Activity]] = relationship(back_populates="club")

    __table_args__ = (
        Index(
            "ix_unique_active_club_name",
            "name",
            unique=True,
            postgresql_where=status != ClubStatusEnum.archived.value,
            sqlite_where=status != ClubStatusEnum.archived.value,
        ),
    )
