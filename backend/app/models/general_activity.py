from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import constants
from app.core.database import Base
from app.models.academic_term import AcademicTermMixin
from app.models.user import AuditMixin

if TYPE_CHECKING:
    from app.models import Club


class GeneralActivityLevelEnum(StrEnum):
    school = "school"
    large = "large"
    club_federation = "club_federation"


class ParticipationTypeEnum(StrEnum):
    participate_only = "participate_only"
    organize = "organize"


class GeneralActivity(Base, AcademicTermMixin):
    __tablename__ = "general_activities"

    name: Mapped[str] = mapped_column(
        String(constants.GENERAL_ACTIVITY_MAX_NAME_LENGTH),
        index=True,
    )
    description: Mapped[str] = mapped_column(Text)
    level: Mapped[GeneralActivityLevelEnum] = mapped_column()
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        index=True,
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        index=True,
    )
    poster_uri: Mapped[str | None] = mapped_column(Text, default=None)
    article_url: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    club_records: Mapped[list[ClubGeneralActivityRecord]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ClubGeneralActivityRecord(Base, AuditMixin):
    __tablename__ = "club_general_activity_records"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        index=True,
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("general_activities.id", ondelete="CASCADE"),
        index=True,
    )

    participation_type: Mapped[ParticipationTypeEnum] = mapped_column()
    requested_score: Mapped[int] = mapped_column(default=0)
    final_score: Mapped[int] = mapped_column(default=0)

    proof_files: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    club: Mapped[Club] = relationship(back_populates="general_activity_records")
    activity: Mapped[GeneralActivity] = relationship(back_populates="club_records")

    met_conditions: Mapped[list[RecordConditionDetail]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_unique_club_activity_record", "club_id", "activity_id", unique=True),
    )


class ActivityCondition(Base):
    __tablename__ = "activity_conditions"

    description: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean)

    details: Mapped[list[RecordConditionDetail]] = relationship(
        back_populates="condition",
    )


class RecordConditionDetail(Base):
    __tablename__ = "record_condition_details"

    record_id: Mapped[int] = mapped_column(
        ForeignKey("club_general_activity_records.id", ondelete="CASCADE"),
        index=True,
    )
    condition_id: Mapped[int] = mapped_column(
        ForeignKey("activity_conditions.id", ondelete="RESTRICT"),
        index=True,
    )
    is_met: Mapped[bool] = mapped_column(Boolean)

    record: Mapped[ClubGeneralActivityRecord] = relationship(
        back_populates="met_conditions",
    )
    condition: Mapped[ActivityCondition] = relationship(back_populates="details")
