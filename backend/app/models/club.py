from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import DateTime, Index, String, Text, case, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import constants
from app.core.database import Base
from app.utils.custom_types import HttpUrlType

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.clubmember import ClubMember
    from app.models.general_activity import ClubGeneralActivityRecord
    from app.models.tag import Tag


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
        String(constants.CLUB_MAX_NAME_LENGTH),
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
    members: Mapped[list[ClubMember]] = relationship(
        back_populates="club",
        lazy="selectin",
    )
    tags: Mapped[list[Tag]] = relationship(
        back_populates="clubs",
        secondary="club_tags",
    )
    activities: Mapped[list[Activity]] = relationship(
        back_populates="club",
        lazy="selectin",
    )
    general_activity_records: Mapped[list[ClubGeneralActivityRecord]] = relationship(
        back_populates="club",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_unique_active_club_name",
            case(
                (status != ClubStatusEnum.archived.value, name),
                else_=None,
            ),
            unique=True,
        ),
        Index(
            "ix_clubs_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_clubs_summary_trgm",
            "summary",
            postgresql_using="gin",
            postgresql_ops={"summary": "gin_trgm_ops"},
        ),
        Index(
            "ix_clubs_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )
