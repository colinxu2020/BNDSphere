from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User


class ModerationStatusEnum(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class ModerationMixin:
    @declared_attr
    @classmethod
    def moderation_status(cls) -> Mapped[ModerationStatusEnum]:
        return mapped_column(
            default=ModerationStatusEnum.pending,
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


class RequestorMixin:
    @declared_attr
    @classmethod
    def requestor_id(cls) -> Mapped[int]:
        return mapped_column(
            ForeignKey("users.id"),
        )

    @declared_attr
    @classmethod
    def requestor(cls) -> Mapped[User]:
        return relationship("User", foreign_keys=[cls.requestor_id])

    @declared_attr
    @classmethod
    def request_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
        )
