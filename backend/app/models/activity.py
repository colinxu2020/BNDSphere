from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import constants
from app.core.database import Base
from app.models import AcademicTerm

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
        String(constants.ACTIVITY_MAX_NAME_LENGTH),
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
    location: Mapped[str] = mapped_column(Text)
    picture_urls: Mapped[list[str]] = mapped_column(JSON, default=list)

    participators: Mapped[list[User]] = relationship(
        back_populates="participated_activities",
        secondary="activity_participators",
    )

    academic_term_id: Mapped[int] = mapped_column(
        ForeignKey("academic_term.id", name="fk_club_gen_act_records_academic_term_id"),
        default=select(AcademicTerm.id)
        .where(AcademicTerm.is_current.is_(True))
        .scalar_subquery(),
    )

    academic_term: Mapped[AcademicTerm] = relationship(lazy="selectin")

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_start_end_time"),
    )
