from datetime import datetime

from pydantic import HttpUrl
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.moderations.moderation_common import ModerateMixin
from app.utils.custom_types import HttpUrlType


class UserUpdateRequest(Base, ModerateMixin):
    __tablename__ = "user_update_request"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    username: Mapped[str | None] = mapped_column(Text, default=None)
    avatar_uri: Mapped[HttpUrl | None] = mapped_column(
        HttpUrlType,
        default=None,
    )
    description: Mapped[str | None] = mapped_column(Text, default=None)

    request_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
