from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecoveryCode(Base):
    """One single-use code that answers a second-factor challenge.

    The way back in when the phone holding the authenticator is lost, which is
    the failure mode that otherwise turns 2FA into a way to lose an account.

    Consumed rows are kept rather than deleted so "you have 3 codes left" is
    answerable and so a used code cannot quietly come back; the whole set is
    replaced when codes are regenerated.
    """

    __tablename__ = "recovery_codes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    # SHA-256 of the normalized code. Unlike a verification code this is 64
    # bits of CSPRNG, so the hash is a real barrier rather than a formality.
    code_hash: Mapped[str] = mapped_column(String(64))
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
    )

    __table_args__ = (Index("ix_recovery_codes_user_id", "user_id"),)
