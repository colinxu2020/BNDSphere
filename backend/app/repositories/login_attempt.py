from datetime import datetime

from sqlalchemy import delete, func, select

from app.models.login_attempt import LoginAttempt
from app.repositories.base import RepositoryBase
from app.schemas.login_attempt import LoginAttemptCreate


class LoginAttemptRepository(
    RepositoryBase[LoginAttempt, LoginAttemptCreate, LoginAttemptCreate],
):
    model = LoginAttempt

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
