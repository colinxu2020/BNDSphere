from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoginAttempt(Base):
    """One username/password login attempt, successful or not.

    Rows back two things: the per-account failed-login throttle (count
    failures since the last success) and a short-lived audit trail of who
    tried to log in from where. ``username`` is the *submitted* string, not a
    foreign key, so attempts against nonexistent accounts are recorded too —
    otherwise the throttle would leak which usernames exist.
    """

    __tablename__ = "login_attempts"

    # (username, created_at) covers both the "failures since last success for
    # this username" lookup and its ordering, so no standalone username index.
    username: Mapped[str] = mapped_column(Text)
    # IPv6 addresses are at most 45 characters; the value is client-controlled
    # in tests and behind Caddy's X-Real-IP in production, so it is nullable
    # (an unknown peer must not reject the attempt).
    ip: Mapped[str | None] = mapped_column(String(45), default=None)
    successful: Mapped[bool] = mapped_column(default=False)
    # A Python-side default so each row carries the real insert time. The
    # server default is PostgreSQL's transaction timestamp, which is identical
    # for every row in one transaction — fine for a creation marker, but wrong
    # for ordering attempts within a request/test.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_login_attempts_username_created_at", "username", "created_at"),
        Index("ix_login_attempts_created_at", "created_at"),
    )
