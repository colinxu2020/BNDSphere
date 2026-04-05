from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.settings import settings

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.user import User


class ActivityStatusEnum(StrEnum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"


class Activity(Base):
    __tablename__ = "activities"

    name: Mapped[str] = mapped_column(
        String(settings.activity_max_name_length),
        index=True,
    )
    description: Mapped[str] = mapped_column(Text)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    club: Mapped[Club] = relationship(back_populates="activities")
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    status: Mapped[ActivityStatusEnum] = mapped_column(
        default=ActivityStatusEnum.upcoming,
    )
    location: Mapped[str] = mapped_column(Text)

    participators: Mapped[list[User]] = relationship(
        back_populates="participated_activities",
        secondary="activity_participators",
    )
