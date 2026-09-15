from datetime import datetime
from hashlib import blake2b

from sqlalchemy import BigInteger, cast, delete, func, select

from app.models.login_attempt import LoginAttempt
from app.repositories.base import RepositoryBase
from app.schemas.login_attempt import LoginAttemptCreate


def _advisory_key(username: str) -> int:
    """Map a username to the signed 64-bit key ``pg_advisory_xact_lock`` wants.

    A collision only serializes two unrelated logins, which is harmless, so a
    cheap non-cryptographic-strength hash is fine.
    """
    digest = blake2b(username.encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


class LoginAttemptRepository(
    RepositoryBase[LoginAttempt, LoginAttemptCreate, LoginAttemptCreate],
):
    model = LoginAttempt

    async def lock_username(self, username: str) -> None:
        """Serialize the check-and-record for one username in this transaction.

        The failure count is read and the attempt inserted in separate
        statements, so concurrent requests for the same username would all read
        the same count and slip a burst of password checks past the threshold.
        An advisory lock (released automatically at commit/rollback) makes the
        pair atomic; it works for nonexistent usernames too, which a row lock
        could not cover.
        """
        await self.db.execute(
            select(
                func.pg_advisory_xact_lock(cast(_advisory_key(username), BigInteger)),
            ),
        )

    async def count_failures_since(self, username: str, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.username == username,
                LoginAttempt.successful.is_(False),
                LoginAttempt.created_at >= since,
            ),
        )
        return int(result.scalar_one())

    async def last_success_at(self, username: str) -> datetime | None:
        result = await self.db.execute(
            select(func.max(LoginAttempt.created_at)).where(
                LoginAttempt.username == username,
                LoginAttempt.successful.is_(True),
            ),
        )
        return result.scalar_one_or_none()

    async def prune_before(self, cutoff: datetime) -> None:
        await self.db.execute(
            delete(LoginAttempt).where(LoginAttempt.created_at < cutoff),
        )
        await self.db.flush()
