from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, func, select
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
    relationship,
)

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
    def requestor_username(cls) -> Mapped[str | None]:
        # Load only the current label in the request query, without lazy I/O.
        return column_property(
            select(User.username)
            .where(User.id == cls.requestor_id)
            .correlate_except(User)
            .scalar_subquery(),
        )

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
