from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.user import User


class ClubMembershipEnum(StrEnum):
    pending = "pending"
    member = "member"
    president = "president"
    vice_president = "vice_president"
    left = "left"


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
    user: Mapped[User] = relationship(
        back_populates="club_memberships",
        lazy="selectin",
    )
    club: Mapped[Club] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("club_id", "user_id", name="uix_club_id_user_id"),
        # A club has at most one president (see CONTEXT.md). Enforced here so a
        # service-layer bug can never yield two; the name comes from the
        # metadata naming convention (``ix_club_members_club_id``).
        Index(
            None,
            "club_id",
            unique=True,
            postgresql_where=(membership == ClubMembershipEnum.president.value),
        ),
    )
