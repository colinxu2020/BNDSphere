from datetime import datetime
from hashlib import blake2b

from sqlalchemy import BigInteger, cast, delete, func, select

from app.models.verification_code import VerificationCode
from app.repositories.base import RepositoryBase
from app.schemas.verification_code import VerificationCodeCreate


def _advisory_key(namespace: str, value: str) -> int:
    """Map a string to the signed 64-bit key ``pg_advisory_xact_lock`` wants.

    Namespaced so a target address and an account id cannot collide into the
    same lock. A collision between two unrelated values only serializes them,
    which is harmless, so a short non-cryptographic digest is enough.
    """
    digest = blake2b(f"{namespace}:{value}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


class VerificationCodeRepository(
    RepositoryBase[VerificationCode, VerificationCodeCreate, VerificationCodeCreate],
):
    model = VerificationCode

    async def lock_send_budget(self, target: str) -> None:
        # All sends take the target lock first; confirm only takes the
        # account lock and never waits for a budget lock.
        await self.db.execute(
            select(
                func.pg_advisory_xact_lock(
                    cast(_advisory_key("verification-target", target), BigInteger)
                ),
            ),
        )

    async def lock_user(self, user_id: int) -> None:
        """Serialize send-budget check and insert for one account.

        The budgets are read and the new row inserted as separate statements,
        so without this two concurrent "resend" clicks both read the
        pre-insert count and both send. The lock is released when the
        transaction ends.
        """
        await self.db.execute(
            select(
                func.pg_advisory_xact_lock(
                    cast(_advisory_key("verification-user", str(user_id)), BigInteger),
                ),
            ),
        )

    async def get_active(
        self,
        user_id: int,
        target: str,
        now: datetime,
    ) -> VerificationCode | None:
        """Only the latest issuance not explicitly rejected can be answered.

        Filter validity after selecting it: consuming or expiring a newer
        code must not revive an older one, even for a different target.
        Definite delivery rejections still spend budget but do not replace
        the previously delivered code; unknown delivery outcomes do.
        """
        result = await self.db.execute(
            select(VerificationCode)
            .where(
                VerificationCode.user_id == user_id,
                VerificationCode.delivery_rejected.is_(False),
            )
            .order_by(VerificationCode.created_at.desc(), VerificationCode.id.desc())
            .limit(1)
            .execution_options(populate_existing=True),
        )
        record = result.scalars().first()
        if (
            record is None
            or record.target != target
            or record.consumed_at is not None
            or record.expires_at <= now
        ):
            return None
        return record

    async def mark_delivery_rejected(self, record_id: int) -> None:
        record = await self.db.get(VerificationCode, record_id)
        if record is not None:
            record.delivery_rejected = True
            await self.db.flush()

    async def budget_reset_at(
        self,
        since: datetime,
        limit: int,
        *,
        user_id: int | None = None,
        target: str | None = None,
    ) -> datetime | None:
        """Timestamp of the send that must leave the window to allow another.

        The limit-th newest send works even if a lowered limit leaves the
        window over budget. No row means the window still has capacity.
        """
        statement = select(VerificationCode.created_at).where(
            VerificationCode.created_at > since,
        )
        if user_id is not None:
            statement = statement.where(VerificationCode.user_id == user_id)
        if target is not None:
            statement = statement.where(VerificationCode.target == target)
        result = await self.db.execute(
            statement.order_by(VerificationCode.created_at.desc())
            .offset(limit - 1)
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def last_sent_at(
        self,
        user_id: int,
    ) -> datetime | None:
        """When this account last had a code sent.

        Keyed on the account, not the target, so switching the address being
        verified does not reset the resend cooldown.
        """
        result = await self.db.execute(
            select(func.max(VerificationCode.created_at)).where(
                VerificationCode.user_id == user_id,
            ),
        )
        return result.scalar_one_or_none()

    async def count_for_user_since(
        self,
        user_id: int,
        since: datetime,
    ) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.user_id == user_id,
                VerificationCode.created_at >= since,
            ),
        )
        return int(result.scalar_one())

    async def count_for_target_since(
        self,
        target: str,
        since: datetime,
    ) -> int:
        """Count sends to one address, across every account.

        Per-account budgets alone would let someone register a handful of
        accounts and point them all at the same address.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.target == target,
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
