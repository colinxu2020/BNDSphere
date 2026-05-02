from pydantic import HttpUrl
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.moderations.moderation_common import ModerateMixin, RequestMixin
from app.utils.custom_types import HttpUrlType


class ClubUpdateRequest(Base, ModerateMixin, RequestMixin):
    __tablename__ = "club_update_request"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
    )

    summary: Mapped[str | None] = mapped_column(Text, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    logo_uri: Mapped[HttpUrl | None] = mapped_column(HttpUrlType, default=None)
