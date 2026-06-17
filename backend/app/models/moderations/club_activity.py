from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core import constants
from app.core.database import Base
from app.models.moderations.moderation_common import (
    ModerationMixin,
    ModerationStatusEnum,
    RequestorMixin,
)


class ClubActivityCreateRequest(Base, ModerationMixin, RequestorMixin):
    __tablename__ = "club_activity_create_requests"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
    )

    name: Mapped[str] = mapped_column(
        String(constants.ACTIVITY_MAX_NAME_LENGTH),
    )
    description: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    location: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_start_end_time"),
    )


class ClubActivityUpdateRequest(Base, ModerationMixin, RequestorMixin):
    __tablename__ = "club_activity_update_requests"

    club_activity_id: Mapped[int] = mapped_column(
        ForeignKey("club_activities.id", ondelete="CASCADE"),
    )

    name: Mapped[str | None] = mapped_column(
        String(constants.ACTIVITY_MAX_NAME_LENGTH),
        default=None,
    )
    description: Mapped[str | None] = mapped_column(Text, default=None)
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    location: Mapped[str | None] = mapped_column(Text, default=None)

    picture_urls: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    update_fields: Mapped[list[str]] = mapped_column(JSON, default=list)

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index | CheckConstraint, ...]:
        """定义数据库表的级联参数和索引."""
        return (
            CheckConstraint(
                "end_time IS NULL OR start_time IS NULL OR end_time > start_time",
                name="check_start_end_time",
            ),
            Index(
                "ix_single_pending_club_activity_update_request",
                "club_activity_id",
                unique=True,
                postgresql_where=(
                    cls.moderation_status == ModerationStatusEnum.pending.value
                ),
            ),
        )
