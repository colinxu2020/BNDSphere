from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User


class VerificationStatusEnum(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class VerificationMixin:
    @declared_attr
    @classmethod
    def verification_status(cls) -> Mapped[VerificationStatusEnum]:
        return mapped_column(
            default=VerificationStatusEnum.pending,
        )

    @declared_attr
    @classmethod
    def verifier_id(cls) -> Mapped[int | None]:
        return mapped_column(
            ForeignKey("users.id"),
            default=None,
        )

    @declared_attr
    @classmethod
    def verifier(cls) -> Mapped[User | None]:
        return relationship("User", foreign_keys=[cls.verifier_id])

    @declared_attr
    @classmethod
    def verify_at(cls) -> Mapped[datetime | None]:
        return mapped_column(
            DateTime(timezone=True),
            default=None,
        )


class ApplicantMixin:
    @declared_attr
    @classmethod
    def applicant_id(cls) -> Mapped[int]:
        return mapped_column(
            ForeignKey("users.id"),
        )

    @declared_attr
    @classmethod
    def applicant(cls) -> Mapped[User]:
        return relationship("User", foreign_keys=[cls.applicant_id])

    @declared_attr
    @classmethod
    def apply_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
        )
