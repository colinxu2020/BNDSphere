from datetime import datetime
from hashlib import blake2b

from sqlalchemy import BigInteger, cast, delete, func, select

from app.models.verification_code import VerificationChannelEnum, VerificationCode
from app.repositories.base import RepositoryBase
from app.schemas.verification_code import VerificationCodeCreate


def _advisory_key(namespace: str, value: str) -> int:
    """Map a string to the signed 64-bit key ``pg_advisory_xact_lock`` wants.

    Namespaced so a phone number and an account id cannot collide into the
    same lock. A collision between two unrelated values only serializes them,
    which is harmless, so a short non-cryptographic digest is enough.
    """
    digest = blake2b(f"{namespace}:{value}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


class VerificationCodeRepository(
    RepositoryBase[VerificationCode, VerificationCodeCreate, VerificationCodeCreate],
):
    model = VerificationCode

    async def lock_user_channel(
        self,
        user_id: int,
        channel: VerificationChannelEnum,
    ) -> None:
        """Serialize send-budget check and insert for one account+channel.

        The budgets are read and the new row inserted as separate statements,
        so without this two concurrent "resend" clicks both read the
        pre-insert count and both send. For SMS that is a duplicate charge;
        held open, it is an unbounded one. The lock is released when the
        transaction ends.
        """
        await self.db.execute(
            select(
                func.pg_advisory_xact_lock(
                    cast(_advisory_key(channel.value, str(user_id)), BigInteger),
                ),
            ),
        )

    async def get_active(
        self,
        user_id: int,
        channel: VerificationChannelEnum,
        target: str,
        now: datetime,
    ) -> VerificationCode | None:
        """Newest unconsumed, unexpired code for this account/channel/target.

        Newest wins: requesting a fresh code has to make the previous one
        unusable, otherwise every resend would widen the set of codes that
        open the account rather than replace it.
        """
        result = await self.db.execute(
            select(VerificationCode)
            .where(
                VerificationCode.user_id == user_id,
                VerificationCode.channel == channel,
                VerificationCode.target == target,
                VerificationCode.consumed_at.is_(None),
                VerificationCode.expires_at > now,
            )
            .order_by(VerificationCode.created_at.desc())
            .limit(1),
        )
        return result.scalars().first()

    async def last_sent_at(
        self,
        user_id: int,
        channel: VerificationChannelEnum,
    ) -> datetime | None:
        """When this account last had a code sent on this channel.

        Keyed on the account, not the target, so switching the address being
        verified does not reset the resend cooldown.
        """
        result = await self.db.execute(
            select(func.max(VerificationCode.created_at)).where(
                VerificationCode.user_id == user_id,
                VerificationCode.channel == channel,
            ),
        )
        return result.scalar_one_or_none()

    async def count_for_user_since(
        self,
        user_id: int,
        channel: VerificationChannelEnum,
        since: datetime,
    ) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.user_id == user_id,
                VerificationCode.channel == channel,
                VerificationCode.created_at >= since,
            ),
        )
        return int(result.scalar_one())

    async def count_for_target_since(
        self,
        channel: VerificationChannelEnum,
        target: str,
        since: datetime,
    ) -> int:
        """Count sends to one address/number, across every account.

        Per-account budgets alone would let someone register a handful of
        accounts and point them all at the same phone number.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.channel == channel,
                VerificationCode.target == target,
                VerificationCode.created_at >= since,
            ),
        )
        return int(result.scalar_one())

    async def count_for_channel_since(
        self,
        channel: VerificationChannelEnum,
        since: datetime,
    ) -> int:
        """Every send on this channel, deployment-wide — the spend ceiling."""
        result = await self.db.execute(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.channel == channel,
                VerificationCode.created_at >= since,
            ),
        )
        return int(result.scalar_one())

    async def mark_consumed(self, code: VerificationCode, now: datetime) -> None:
        code.consumed_at = now
        self.db.add(code)
        await self.db.flush()

    async def record_attempt(self, code: VerificationCode) -> None:
        code.attempts += 1
        self.db.add(code)
        await self.db.flush()

    async def prune_before(self, cutoff: datetime) -> None:
        await self.db.execute(
            delete(VerificationCode).where(VerificationCode.created_at < cutoff),
        )
        await self.db.flush()
