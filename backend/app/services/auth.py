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
from app.services.errors import LoginThrottledError


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

        On an account with a second factor the correct password records
        nothing at all — see below. Callers that use this purely to re-check a
        password (changing one, disarming 2FA) get the same treatment, which
        is the harmless direction: they neither consume nor reset the budget.

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
            await self._ensure_not_locked_out(username)

            user = await self.repository.get_by_username(username)
            successful = user is not None and verify_password(
                password,
                user.hashed_password,
            )
            if successful and user is not None and user.two_factor_enabled:
                # Nothing recorded yet: a correct password on a 2FA account
                # has not logged anyone in, and writing a success here would
                # reset the failure window — which would hand someone who
                # already has the password unlimited guesses at the six
                # digits. ``TwoFactorService`` records the outcome once the
                # challenge is answered.
                #
                # ponytail: the cost is an audit gap — a correct password
                # whose challenge is never answered leaves no row at all.
                # Closing it means a stage column on ``login_attempts``; the
                # table is a lockout counter first and a log second, so it
                # can wait.
                return user
            await self._record_attempt(username, ip, successful=successful)
            return user if successful else None

    async def ensure_not_locked_out(self, username: str) -> None:
        """Raise ``LoginThrottledError`` if this account is locked out.

        For the second-factor step, which is a login attempt in its own right
        and has to count against the same budget: six digits are within reach
        of a grinder that nothing throttles.

        ponytail: unlike ``authenticate`` this does not hold the lock across
        the verification that follows, so concurrent guesses can slip a few
        past the threshold. Closing it means threading the whole second-factor
        check through here — worth it only if the few turns out to matter.
        """
        async with self.transaction():
            await self.login_attempt_repository.lock_username(username)
            await self._ensure_not_locked_out(username)

    async def record_attempt(
        self,
        username: str,
        ip: str | None,
        *,
        successful: bool,
    ) -> None:
        """Record how a second-factor attempt ended.

        Success resets the failure window, exactly as a one-step login does:
        the login is finished either way, and this is the step that finished
        it.
        """
        await self._record_attempt(username, ip, successful=successful)

    async def _ensure_not_locked_out(self, username: str) -> None:
        # Resolve the window once and thread it through: recomputing it for
        # the expiry boundary would use a later ``now`` (and run another
        # ``last_success_at`` query), which can shift the boundary by a row at
        # the window edge and disagree with the count it must match.
        since = await self._window_start(username)
        failure_count = await self._recent_failure_count(username, since)
        if failure_count >= LOGIN_LOCKOUT_THRESHOLD:
            raise LoginThrottledError(
                await self._retry_after_seconds(username, failure_count, since),
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
