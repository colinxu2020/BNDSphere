from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VerificationCode(Base):
    """One one-time code sent to an email address.

    Unlike ``user_sessions``, a consumed code is *kept* rather than deleted:
    the send budgets in ``VerificationCodeRepository`` count how many codes
    went out to an account and to a target. Deleting on use would reset those
    counters and hand an attacker a free refill every time they completed one
    verification. ``consumed_at`` is what stops a code being replayed;
    retention pruning is what stops the table growing.

    ``target`` is stored per row rather than read off ``users``: the whole
    point is to confirm an address the account does not have yet, so until
    the code is confirmed there is nowhere else the value could live.
    """

    __tablename__ = "verification_codes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    # Normalized destination: a lowercased email address. Normalization
    # happens before the row is written so the send budgets cannot be dodged
    # by re-casing an address.
    target: Mapped[str] = mapped_column(Text)
    # SHA-256 of the six-digit code. Six digits is only ~20 bits, so this is
    # not a serious brute-force barrier against an attacker holding the table
    # — the short TTL and the attempt cap are. It is here so a leaked backup
    # or a replicated row does not hand over codes that are still live.
    code_hash: Mapped[str] = mapped_column(String(64))
    # Wrong submissions against this code. At
    # ``VERIFICATION_CODE_MAX_ATTEMPTS`` the code is burned, which is what
    # keeps those 20 bits out of reach.
    attempts: Mapped[int] = mapped_column(default=0)
    # Rejected provider requests spend budget but never supersede a delivered
    # code. Ambiguous transport errors keep this false: delivery may have occurred.
    delivery_rejected: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    # Python-side default so rows inserted in one transaction still order
    # correctly; PostgreSQL's ``now()`` is the transaction timestamp and would
    # be identical for all of them. Same reasoning as ``login_attempts``.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        # Latest live code for an account, and the per-account send budget.
        Index(
            "ix_verification_codes_user_id_created_at",
            "user_id",
            "created_at",
        ),
        # Per-target send budget: one address cannot be bombed through a
        # series of throwaway accounts.
        Index("ix_verification_codes_target_created_at", "target", "created_at"),
        # The retention sweep deletes by created_at alone.
        Index("ix_verification_codes_created_at", "created_at"),
    )
