from datetime import UTC, datetime, timedelta
from math import ceil

from app.core.constants import (
    LOGIN_FAILURE_WINDOW_MINUTES,
    LOGIN_LOCKOUT_THRESHOLD,
    USER_MAX_USERNAME_LENGTH,
)
from app.core.security import verify_password
from app.models.user import User
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user import UserRepository
from app.schemas.login_attempt import LoginAttemptCreate
from app.schemas.user import AdminUserUpdate, UserCreate
from app.services.base import ServiceBase
from app.services.errors import AuthenticationError, LoginThrottledError


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

        Counts failures against the submitted username — existent or not — so
        the throttle cannot be used to probe which usernames exist. A
        successful login resets the count. The whole check-and-record runs in
        one transaction under a per-username advisory lock, so concurrent
        attempts cannot all read the same count and race past the threshold.
        The attempt row is committed before returning, so a failed login still
        leaves an audit record even though the request handler then raises.

        The username is clamped to ``USER_MAX_USERNAME_LENGTH`` first: the login
        form (``OAuth2PasswordRequestForm``) puts no bound on it, unlike
        registration, and the value is hashed into the advisory-lock key,
        queried, and persisted into an indexed column. Without the clamp a
        caller could grow the audit table and its index for the whole retention
        window, or push a value past PostgreSQL's B-tree entry limit and turn a
        bad login into a 500.
        """
        username = username[:USER_MAX_USERNAME_LENGTH]
        async with self.transaction():
            await self.login_attempt_repository.lock_username(username)

            # Resolve the window once and thread it through: recomputing it for
            # the expiry boundary would use a later ``now`` (and run another
            # ``last_success_at`` query), which can shift the boundary by a row
            # at the window edge and disagree with the count it must match.
            since = await self._window_start(username)
            failure_count = await self._recent_failure_count(username, since)
            if failure_count >= LOGIN_LOCKOUT_THRESHOLD:
                raise LoginThrottledError(
                    await self._retry_after_seconds(username, failure_count, since),
                )

            user = await self.repository.get_by_username(username)
            successful = user is not None and verify_password(
                password,
                user.hashed_password,
            )
            await self._record_attempt(username, ip, successful=successful)
            return user if successful else None

    async def reauthenticate(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> None:
        """Re-check the password of an account that is already signed in.

        Routes that change *how* an account is reached — binding a new address
        or number — ask for it again, because the question they decide is
        whether a stolen session can point the account's recovery channel at
        someone else.

        Through ``authenticate`` rather than ``verify_password`` directly, so
        they cannot be used as an unthrottled password oracle that happens to
        need a session.
        """
        if await self.authenticate(user.username, password, ip=ip) is None:
            raise AuthenticationError(
                "error.auth.incorrect_user_passwd",
                "INCORRECT_USER_PASSWD",
            )

    async def _recent_failure_count(self, username: str, since: datetime) -> int:
        return await self.login_attempt_repository.count_failures_since(
            username,
            since,
        )

    async def _window_start(self, username: str) -> datetime:
        """Lower bound of the trailing failure window for ``username``.

        Failures are only counted since the last success, so a successful login
        empties the window.
        """
        since = datetime.now(UTC) - timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)
        last_success = await self.login_attempt_repository.last_success_at(username)
        if last_success is not None and last_success > since:
            since = last_success
        return since

    async def _retry_after_seconds(
        self,
        username: str,
        failure_count: int,
        since: datetime,
    ) -> int:
        """Seconds until enough old failures age out to lift the lockout.

        Blocked requests are not recorded, so ``failure_count`` never climbs
        past the threshold; the wait is therefore until the oldest in-window
        failures expire — at most the failure window, and never the fixed,
        misleading 30s the previous backoff always produced.

        ``since`` is the same bound ``failure_count`` was measured with, so the
        boundary row lines up with the count that triggered the lockout.
        """
        boundary = await self.login_attempt_repository.failure_expiry_boundary(
            username,
            since,
            failure_count - LOGIN_LOCKOUT_THRESHOLD,
        )
        if boundary is None:  # pragma: no cover - a counted failure must exist
            return 1
        expires_at = boundary + timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)
        remaining = (expires_at - datetime.now(UTC)).total_seconds()
        return max(1, ceil(remaining))

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
