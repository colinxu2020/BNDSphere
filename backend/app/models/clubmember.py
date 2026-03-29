from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.user import User


class ClubMembershipEnum(StrEnum):
    none = "none"
    pending = "pending"
    member = "member"
    president = "president"
    vice = "vice president"


class ClubMember(Base):
    __tablename__ = "club_members"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    membership: Mapped[ClubMembershipEnum] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    user: Mapped[User] = relationship(back_populates="club_memberships")
    club: Mapped[Club] = relationship(back_populates="members")
