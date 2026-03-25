from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.clubmember import ClubMember


class RoleEnum(StrEnum):
    ban = "ban"
    user = "user"
    union_of_associations = "union of associations"
    admin = "admin"
    dev = "dev"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        Text,
        unique=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_uri: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    real_name: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[RoleEnum] = mapped_column()
    wecom_userid: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    club_memberships: Mapped[list[ClubMember]] = relationship(back_populates="user")
