from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User


class ModerateStateEnum(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ModerateMixin:
    @declared_attr
    @classmethod
    def moderate_status(cls) -> Mapped[ModerateStateEnum]:
        return mapped_column(
            default=ModerateStateEnum.pending,
        )

    @declared_attr
    @classmethod
    def moderator_id(cls) -> Mapped[int | None]:
        return mapped_column(
            ForeignKey("users.id"),
            default=None,
        )

    @declared_attr
    @classmethod
    def moderator(cls) -> Mapped[User | None]:
        return relationship("User", foreign_keys=[cls.moderator_id])

    @declared_attr
    @classmethod
    def moderate_at(cls) -> Mapped[datetime | None]:
        return mapped_column(
            DateTime(timezone=True),
            default=None,
        )
