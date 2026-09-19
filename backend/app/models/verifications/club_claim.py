from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.core.database import Base
from app.models.verifications.verification_common import (
    ApplicantMixin,
    VerificationMixin,
    VerificationStatusEnum,
)

if TYPE_CHECKING:
    from app.models.club import Club


class ClubClaimRequest(Base, VerificationMixin, ApplicantMixin):
    __tablename__ = "club_claim_requests"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
    )
    message: Mapped[str] = mapped_column(Text)
    club: Mapped[Club] = relationship()

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index]:
        """Prevent duplicate pending claims from the same applicant."""
        return (
            Index(
                "ix_single_pending_club_claim_request",
                "club_id",
                "applicant_id",
                unique=True,
                postgresql_where=(
                    cls.verification_status == VerificationStatusEnum.pending.value
                ),
            ),
        )
