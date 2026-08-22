from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import constants
from app.core.database import Base
from app.models.academic_term import AcademicTermMixin
from app.models.user import AuditStatusEnum

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.user import User


class JointActivity(Base, AcademicTermMixin):
    __tablename__ = "joint_activities"

    name: Mapped[str] = mapped_column(
        String(constants.JOINT_ACTIVITY_MAX_NAME_LENGTH),
        index=True,
    )
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(
        String(constants.JOINT_ACTIVITY_MAX_LOCATION_LENGTH),
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    initiator_club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    preliminary_status: Mapped[AuditStatusEnum] = mapped_column(
        default=AuditStatusEnum.pending,
        index=True,
    )
    preliminary_auditor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    preliminary_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )

    archive_text: Mapped[str | None] = mapped_column(Text, default=None)
    archive_files: Mapped[list[str]] = mapped_column(JSON, default=list)
    final_status: Mapped[AuditStatusEnum | None] = mapped_column(
        default=None,
        index=True,
    )
    final_score: Mapped[int] = mapped_column(default=0)
    final_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    final_auditor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    final_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    initiator_club: Mapped[Club] = relationship(
        back_populates="initiated_joint_activities",
        lazy="selectin",
    )
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_user_id])
    preliminary_auditor: Mapped[User | None] = relationship(
        foreign_keys=[preliminary_auditor_id],
    )
    final_auditor: Mapped[User | None] = relationship(
        foreign_keys=[final_auditor_id],
    )
    participations: Mapped[list[JointActivityParticipation]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JointActivityParticipation.created_at",
    )


class JointActivityParticipation(Base):
    __tablename__ = "joint_activity_participations"

    activity_id: Mapped[int] = mapped_column(
        ForeignKey("joint_activities.id", ondelete="CASCADE"),
        index=True,
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        index=True,
    )
    registered_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    is_initiator: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    activity: Mapped[JointActivity] = relationship(back_populates="participations")
    club: Mapped[Club] = relationship(
        back_populates="joint_activity_participations",
        lazy="selectin",
    )
    registered_by: Mapped[User] = relationship()

    __table_args__ = (
        Index(
            "ix_unique_joint_activity_club_participation",
            "activity_id",
            "club_id",
            unique=True,
        ),
    )
