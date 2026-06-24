from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base
from app.models.verifications.verification_common import (
    ApplicantMixin,
    VerificationMixin,
    VerificationStatusEnum,
)


class ClubMembershipRequest(Base, VerificationMixin, ApplicantMixin):
    __tablename__ = "club_membership_requests"

    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
    )

    message: Mapped[str] = mapped_column(Text)

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index]:
        """定义数据库表的级联参数和索引."""
        return (
            Index(
                "ix_single_pending_club_membership_request",
                "club_id",
                "applicant_id",
                unique=True,
                postgresql_where=(
                    cls.verification_status == VerificationStatusEnum.pending.value
                ),
            ),
        )
