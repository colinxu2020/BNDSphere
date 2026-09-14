from datetime import UTC, datetime, timedelta
from typing import Final

from app.core.constants import (
    LOGIN_BACKOFF_BASE_SECONDS,
    LOGIN_BACKOFF_MAX_SECONDS,
    LOGIN_FAILURE_WINDOW_MINUTES,
    LOGIN_LOCKOUT_THRESHOLD,
)
from app.core.security import verify_password
from app.models.user import User
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user import UserRepository
from app.schemas.login_attempt import LoginAttemptCreate
from app.schemas.user import AdminUserUpdate, UserCreate
from app.services.base import ServiceBase
from app.services.errors import LoginThrottledError

# Window doubling is capped so an enormous failure count cannot build a
# multi-year ``Retry-After`` before the max cap is applied.
_MAX_BACKOFF_EXPONENT: Final[int] = 16


class AuthService(ServiceBase[User, UserCreate, AdminUserUpdate]):
    repository: UserRepository

    def __init__(
        self,
        repository: UserRepository,
        login_attempt_repository: LoginAttemptRepository,
    ) -> None:
        super().__init__(repository)
        self.login_attempt_repository = login_attempt_repository

    async def authenticate(
        self,
        username: str,
        password: str,
        *,
        ip: str | None,
    ) -> User | None:
        """Verify credentials, recording the attempt and enforcing lockout.

        Counts failures against the raw submitted username — existent or not —
        so the throttle cannot be used to probe which usernames exist. A
        successful login resets the count. The attempt row is committed before
        returning, so a failed login still leaves an audit record even though
        the request handler then raises.
        """
        failure_count = await self._recent_failure_count(username)
        if failure_count >= LOGIN_LOCKOUT_THRESHOLD:
            raise LoginThrottledError(self._backoff_seconds(failure_count))

        user = await self.repository.get_by_username(username)
        successful = user is not None and verify_password(
            password,
            user.hashed_password,
        )
        await self._record_attempt(username, ip, successful=successful)
        return user if successful else None

    async def _recent_failure_count(self, username: str) -> int:
        since = datetime.now(UTC) - timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)
        last_success = await self.login_attempt_repository.last_success_at(username)
        if last_success is not None and last_success > since:
            since = last_success
        return await self.login_attempt_repository.count_failures_since(
            username,
            since,
        )

    async def _record_attempt(
        self,
        username: str,
        ip: str | None,
        *,
        successful: bool,
    ) -> None:
        async with self.transaction():
            await self.login_attempt_repository.create(
                LoginAttemptCreate(username=username, ip=ip, successful=successful),
            )

    @staticmethod
    def _backoff_seconds(failure_count: int) -> int:
        exponent = min(failure_count - LOGIN_LOCKOUT_THRESHOLD, _MAX_BACKOFF_EXPONENT)
        # ``base << n`` is ``base * 2**n`` with an int type mypy keeps.
        return min(LOGIN_BACKOFF_BASE_SECONDS << exponent, LOGIN_BACKOFF_MAX_SECONDS)
