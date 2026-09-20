from datetime import UTC, datetime, timedelta

from app.core.constants import SESSION_LIFETIME_DAYS
from app.core.security import generate_session_token, hash_session_token
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.user_session import UserSessionRepository
from app.schemas.user_session import UserSessionCreate
from app.services.base import ServiceBase


class UserSessionService(
    ServiceBase[UserSession, UserSessionCreate, UserSessionCreate],
):
    repository: UserSessionRepository

    async def issue(self, user: User) -> str:
        """Open a session for ``user`` and return the token the client keeps.

        The raw token is returned once and never stored; only its hash is
        persisted, so it cannot be recovered from the database afterwards.
        """
        token = generate_session_token()
        async with self.transaction():
            await self.repository.create(
                UserSessionCreate(
                    user_id=user.id,
                    token_hash=hash_session_token(token),
                    expires_at=datetime.now(UTC)
                    + timedelta(days=SESSION_LIFETIME_DAYS),
                ),
            )
        return token

    async def resolve(self, token: str) -> UserSession | None:
        return await self.repository.get_active_by_token_hash(
            hash_session_token(token),
            datetime.now(UTC),
        )

    async def revoke(self, token: str) -> None:
        """End the session named by ``token``, if it is still live.

        Silent when the token is unknown, expired or already revoked: signing
        out is idempotent, and a caller holding a dead token has nothing left
        to end.
        """
        session = await self.resolve(token)
        if session is not None:
            async with self.transaction():
                await self.repository.delete(session)

    async def revoke_all(self, user: User) -> None:
        """End every session for ``user``.

        What a password change is for: whoever has been riding a stolen
        session loses it, which is the whole point of changing the password
        and is not something revoking only the current one would achieve.
        """
        async with self.transaction():
            await self.repository.delete_for_user(user.id)
