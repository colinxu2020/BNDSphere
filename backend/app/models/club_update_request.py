from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import AuditMixin
from app.utils.custom_types import HttpUrlType

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.user import User


class ClubUpdateRequest(Base, AuditMixin):
    __tablename__ = "club_update_requests"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        index=True,
    )
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    logo_uri: Mapped[HttpUrl | None] = mapped_column(HttpUrlType, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    club: Mapped[Club] = relationship("Club")
    requester: Mapped[User] = relationship(
        "User",
        foreign_keys=[requester_id],
    )
