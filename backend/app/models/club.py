from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.settings import settings

if TYPE_CHECKING:
    from app.models.clubmember import ClubMember


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


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(settings.club_max_name_length),
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    logo_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    status: Mapped[ClubStatusEnum] = mapped_column()
    star_level: Mapped[ClubStarLevelEnum] = mapped_column()
    members: Mapped[list[ClubMember]] = relationship(back_populates="club")
