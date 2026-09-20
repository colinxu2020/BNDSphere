from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from collections.abc import Mapping

    from app.models.user import User


class LegalDocumentEnum(StrEnum):
    privacy_policy = "privacy_policy"
    user_agreement = "user_agreement"
    cross_border_transfer_consent = "cross_border_transfer_consent"


CURRENT_LEGAL_DOCUMENT_VERSIONS: Final[Mapping[LegalDocumentEnum, date]] = (
    MappingProxyType(
        {
            LegalDocumentEnum.privacy_policy: date(2026, 9, 20),
            LegalDocumentEnum.user_agreement: date(2026, 9, 15),
            LegalDocumentEnum.cross_border_transfer_consent: date(2026, 9, 15),
        },
    )
)


class LegalConsent(Base):
    __tablename__ = "legal_consents"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    document: Mapped[LegalDocumentEnum] = mapped_column(
        Enum(LegalDocumentEnum, name="legaldocumentenum"),
    )
    document_version: Mapped[date] = mapped_column(Date)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="legal_consents")

    __table_args__ = (
        UniqueConstraint("user_id", "document", "document_version"),
        Index(
            "ix_legal_consents_document_document_version",
            "document",
            "document_version",
        ),
    )
