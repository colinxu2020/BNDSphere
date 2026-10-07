from datetime import datetime

from sqlalchemy import delete, select

from app.models.user_session import UserSession
from app.repositories.base import RepositoryBase
from app.schemas.user_session import UserSessionCreate


class UserSessionRepository(
    RepositoryBase[UserSession, UserSessionCreate, UserSessionCreate],
):
    model = UserSession

    async def retain_newest_for_user(
        self, user_id: int, now: datetime, keep: int
    ) -> None:
        """Prune expired and excess sessions while the caller holds the user lock."""
        retained = (
            select(UserSession.id)
            .where(UserSession.user_id == user_id, UserSession.expires_at > now)
            .order_by(UserSession.created_at.desc(), UserSession.id.desc())
            .limit(keep)
        )
        await self.db.execute(
            delete(UserSession).where(
                UserSession.user_id == user_id, UserSession.id.not_in(retained)
            )
        )

    async def get_active_by_token_hash(
        self,
        token_hash: str,
        now: datetime,
    ) -> UserSession | None:
        """Look up a session that exists and has not expired.

        Expiry is filtered here rather than left to the retention sweep: the
        sweep runs daily, so between runs an expired row is still present and
        would otherwise authenticate.
        """
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.expires_at > now,
            ),
        )
        return result.scalars().first()

    async def prune_expired(self, now: datetime) -> None:
        await self.db.execute(delete(UserSession).where(UserSession.expires_at <= now))
        await self.db.flush()
