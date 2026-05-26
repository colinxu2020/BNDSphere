from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import constants
from app.core.database import Base
from app.models.academic_term import AcademicTermMixin
from app.models.club_activity_participant import club_activity_participant_table

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.user import User


class ClubActivity(Base, AcademicTermMixin):
    __tablename__ = "club_activities"

    name: Mapped[str] = mapped_column(
        String(constants.ACTIVITY_MAX_NAME_LENGTH),
        index=True,
    )
    description: Mapped[str] = mapped_column(Text)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    club: Mapped[Club] = relationship(back_populates="club_activities")
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    location: Mapped[str] = mapped_column(Text)
    picture_urls: Mapped[list[str]] = mapped_column(JSON, default=list)

    participants: Mapped[list[User]] = relationship(
        back_populates="participated_club_activities",
        secondary=club_activity_participant_table,
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_start_end_time"),
    )
