from enum import Enum
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.settings import settings


class ClubStatusEnum(str, Enum):
    unreviewed = "unreviewed"
    normal = "normal"
    archived = "archived"


class ClubStarLevelEnum(str, Enum):
    none = "暂无星级"
    one_star = "1星级社团"
    two_star = "2星级社团"
    three_star = "3星级社团"
    four_star = "4星级社团"
    five_star = "5星级社团"
    honorary = "荣誉社团"


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(settings.club_max_name_length), unique=True, index=True
    )
    description: Mapped[str] = mapped_column(
        String(settings.club_max_description_length)
    )
    logo_uri: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[ClubStatusEnum] = mapped_column()
    star_level: Mapped[ClubStarLevelEnum] = mapped_column()
