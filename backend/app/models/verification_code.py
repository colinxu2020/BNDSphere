from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VerificationChannelEnum(StrEnum):
    email = "email"
    sms = "sms"


class VerificationPurposeEnum(StrEnum):
    """What answering the code is allowed to do.

    Codes are bound to a purpose so one cannot be redeemed as the other. The
    attack this closes is social: "confirm your email address, here is your
    code" is a far easier thing to talk someone into reading aloud than
    "reset your password", and without this column the two are the same
    six digits.
    """

    bind = "bind"
    password_reset = "password_reset"  # noqa: S105 - a purpose, not a secret
    two_factor = "two_factor"


class VerificationCode(Base):
    """One one-time code sent to an email address or a phone number.

    Unlike ``user_sessions``, a consumed code is *kept* rather than deleted:
    the send budgets in ``VerificationCodeRepository`` count how many codes
    went out to an account, to a target and — for SMS, which costs money —
    across the whole deployment. Deleting on use would reset those counters
    and hand an attacker a free refill every time they completed one
    verification. ``consumed_at`` is what stops a code being replayed;
    retention pruning is what stops the table growing.

    ``target`` is stored per row rather than read off ``users``: the whole
    point is to confirm an address the account does not have yet, so until
    the code is confirmed there is nowhere else the value could live.

    The send budgets ignore ``purpose`` on purpose — total spend per account
    and per number is what costs money, and counting each purpose separately
    would let a caller double the real ceiling by alternating between them.
    Only redemption is purpose-scoped.
    """

    __tablename__ = "verification_codes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    channel: Mapped[VerificationChannelEnum] = mapped_column()
    purpose: Mapped[VerificationPurposeEnum] = mapped_column(
        default=VerificationPurposeEnum.bind,
    )
    # Normalized destination: a lowercased email address, or an E.164 phone
    # number. Normalization happens before the row is written so the send
    # budgets cannot be dodged by re-casing an address or dropping a "+86".
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
        # Latest live code for an account on one channel, and the per-account
        # send budget.
        Index(
            "ix_verification_codes_user_id_channel_created_at",
            "user_id",
            "channel",
            "created_at",
        ),
        # Per-target send budget: one phone number cannot be used to bill the
        # deployment through a series of throwaway accounts.
        Index("ix_verification_codes_target_created_at", "target", "created_at"),
        # Deployment-wide daily SMS budget, and the retention sweep.
        Index("ix_verification_codes_channel_created_at", "channel", "created_at"),
    )
