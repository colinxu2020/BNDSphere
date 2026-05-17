from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.core.database import Base
from app.models.activity_participator import activity_participator_table
from app.utils.custom_types import HttpUrlType

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.clubmember import ClubMember


class RoleEnum(StrEnum):
    ban = "ban"
    user = "user"
    moderator = "moderator"
    scf = "staff of club federation"
    admin = "admin"
    dev = "dev"


class AuditStatusEnum(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


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
    avatar_uri: Mapped[HttpUrl | None] = mapped_column(HttpUrlType, default=None)
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
    participated_activities: Mapped[list[Activity]] = relationship(
        back_populates="participators",
        secondary=activity_participator_table,
    )


class AuditMixin:
    @declared_attr
    @classmethod
    def audit_status(cls) -> Mapped[AuditStatusEnum]:
        return mapped_column(
            default=AuditStatusEnum.pending,
        )

    @declared_attr
    @classmethod
    def auditor_id(cls) -> Mapped[int | None]:
        return mapped_column(
            ForeignKey("users.id"),
            default=None,
        )

    @declared_attr
    @classmethod
    def auditor(cls) -> Mapped[User | None]:
        return relationship("User", foreign_keys=[cls.auditor_id])
