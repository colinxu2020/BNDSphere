from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSession(Base):
    """One logged-in session, addressed by an opaque token the client holds.

    Server-side state is the whole point. The token carries no claims, so
    signing out takes effect on the very next request, whereas the
    self-contained JWT this replaced stayed valid until its own expiry no
    matter what the server thought.

    Revocation is a ``DELETE``, not a tombstone column: nothing reads the
    history of ended sessions, and a row that is gone cannot be resurrected by
    a bug that forgets to filter on it.
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    # SHA-256 of the token the client holds, never the token itself, so a dump
    # of this table cannot be replayed as a set of live logins. Hex-encoded
    # SHA-256 is exactly 64 characters.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Python-side default for the same reason as ``login_attempts.created_at``:
    # the server default is the transaction timestamp, identical for every row
    # written in one transaction.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Serves the retention sweep, which deletes every session past its expiry.
    __table_args__ = (Index("ix_user_sessions_expires_at", "expires_at"),)
