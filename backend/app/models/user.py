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

    username: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        Text,
        unique=True,
        default=None,
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_uri: Mapped[str | None] = mapped_column(Text, default=None)
    description: Mapped[str] = mapped_column(Text, default="这位用户还没有设置简介")
    real_name: Mapped[str | None] = mapped_column(String(20), default=None)
    role: Mapped[RoleEnum] = mapped_column(default=RoleEnum.user)
    wecom_userid: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    club_memberships: Mapped[list[ClubMember]] = relationship(back_populates="user")
