from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core import constants
from app.core.database import Base
from app.models.moderations.moderation_common import (
    ModerateMixin,
    ModerateStatusEnum,
    RequestMixin,
)


class ClubActivityCreateRequest(Base, ModerateMixin, RequestMixin):
    __tablename__ = "club_activity_create_request"

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


class ClubActivityUpdateRequest(Base, ModerateMixin, RequestMixin):
    __tablename__ = "club_activity_update_request"

    club_activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
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

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index]:
        """定义数据库表的级联参数和索引."""
        return (
            Index(
                "ix_single_pending_club_activity_update_request",
                "club_activity_id",
                unique=True,
                postgresql_where=(
                    cls.moderate_status == ModerateStatusEnum.pending.value
                ),
            ),
        )
