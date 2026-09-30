from datetime import datetime

from sqlalchemy import delete, func, select

from app.models.recovery_code import RecoveryCode
from app.repositories.base import RepositoryBase
from app.schemas.two_factor import RecoveryCodeCreate


class RecoveryCodeRepository(
    RepositoryBase[RecoveryCode, RecoveryCodeCreate, RecoveryCodeCreate],
):
    model = RecoveryCode

    async def get_unconsumed(self, user_id: int, code_hash: str) -> RecoveryCode | None:
        """Find a live code for this account, locked for the caller's update.

        ``FOR UPDATE`` is what makes a code single-use under concurrency: two
        simultaneous submissions of the same code would otherwise both read it
        as unconsumed and both be let in.
        """
        result = await self.db.execute(
            select(RecoveryCode)
            .where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.code_hash == code_hash,
                RecoveryCode.consumed_at.is_(None),
            )
            .with_for_update(),
        )
        return result.scalars().first()

    async def count_unconsumed(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(RecoveryCode)
            .where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.consumed_at.is_(None),
            ),
        )
        return int(result.scalar_one())

    async def mark_consumed(self, code: RecoveryCode, now: datetime) -> None:
        code.consumed_at = now
        self.db.add(code)
        await self.db.flush()

    async def delete_for_user(self, user_id: int) -> None:
        """Drop every code for this account, consumed or not.

        Called when a fresh set is minted and when the last second factor is
        turned off. Consumed rows go too: they are only kept so a used code
        cannot come back, and once the whole set is replaced there is nothing
        left for them to guard.
        """
        await self.db.execute(
            delete(RecoveryCode).where(RecoveryCode.user_id == user_id),
        )
        await self.db.flush()
