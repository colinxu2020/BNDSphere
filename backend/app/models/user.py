from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import HttpUrl
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.core.database import Base
from app.models.club_activity_participant import club_activity_participant_table
from app.utils.custom_types import HttpUrlType

if TYPE_CHECKING:
    from app.models.club_activity import ClubActivity
    from app.models.clubmember import ClubMember


class RoleEnum(StrEnum):
    ban = "ban"
    user = "user"
    moderator = "moderator"
    federation_staff = "federation_staff"
    admin = "admin"
    dev = "dev"


_GRADE_LEVEL_MAP: dict[str, int] = {
    "grade_7": 7,
    "grade_8": 8,
    "grade_9": 9,
    "grade_10": 10,
    "grade_11": 11,
    "grade_12": 12,
    "inter_grade_9": 9,
    "inter_grade_10": 10,
    "inter_grade_11": 11,
    "inter_grade_12": 12,
}


class UserGradeEnum(StrEnum):
    grade_7 = "grade_7"
    grade_8 = "grade_8"
    grade_9 = "grade_9"
    grade_10 = "grade_10"
    grade_11 = "grade_11"
    grade_12 = "grade_12"
    inter_grade_9 = "inter_grade_9"
    inter_grade_10 = "inter_grade_10"
    inter_grade_11 = "inter_grade_11"
    inter_grade_12 = "inter_grade_12"

    @property
    def grade_level(self) -> int:
        return _GRADE_LEVEL_MAP[self.value]


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
    grade: Mapped[UserGradeEnum | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    club_memberships: Mapped[list[ClubMember]] = relationship(back_populates="user")
    participated_club_activities: Mapped[list[ClubActivity]] = relationship(
        back_populates="participants",
        secondary=club_activity_participant_table,
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
