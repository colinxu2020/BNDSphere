from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.club_activity import ClubActivity
    from app.models.user import User


class CheckInMethodEnum(StrEnum):
    manual = "manual"
    qrcode = "qrcode"


class ClubActivityCheckIn(Base):
    __tablename__ = "club_activity_check_ins"

    # No index=True here — ix_unique_club_activity_check_in_user below is a
    # composite (club_activity_id, user_id) index, and its leftmost prefix
    # already serves plain club_activity_id lookups, so a standalone index
    # on it would just be redundant.
    club_activity_id: Mapped[int] = mapped_column(
        ForeignKey("club_activities.id", ondelete="CASCADE"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    method: Mapped[CheckInMethodEnum]
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    # Who recorded this row: the president/vice-president for a manual entry,
    # or the checking-in user themself for a QR self-check-in.
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    activity: Mapped[ClubActivity] = relationship(back_populates="check_ins")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    recorded_by: Mapped[User] = relationship(foreign_keys=[recorded_by_user_id])

    __table_args__ = (
        Index(
            "ix_unique_club_activity_check_in_user",
            "club_activity_id",
            "user_id",
            unique=True,
        ),
    )
