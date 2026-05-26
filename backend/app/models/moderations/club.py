from pydantic import HttpUrl
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base
from app.models.moderations.moderation_common import (
    ModerationMixin,
    ModerationStatusEnum,
    RequestorMixin,
)
from app.utils.custom_types import HttpUrlType


class ClubUpdateRequest(Base, ModerationMixin, RequestorMixin):
    __tablename__ = "club_update_requests"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
    )

    summary: Mapped[str | None] = mapped_column(Text, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    logo_uri: Mapped[HttpUrl | None] = mapped_column(HttpUrlType, default=None)

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index]:
        """定义数据库表的级联参数和索引."""
        return (
            Index(
                "ix_single_pending_club_update_request",
                "club_id",
                unique=True,
                postgresql_where=(
                    cls.moderation_status == ModerationStatusEnum.pending.value
                ),
            ),
        )
