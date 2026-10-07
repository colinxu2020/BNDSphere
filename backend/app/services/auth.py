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
        reauthentication: bool = False,
    ) -> User | None:
        """Verify credentials, recording the attempt and enforcing lockout.

        Counts failures against the submitted username — existent or not — so
        the throttle cannot be used to probe which usernames exist. A
        successful login resets the count. Reauthentication counts all attempts
        in the rolling window, including successful ordinary logins, so correct
        passwords and later contact-binding failures cannot bypass its budget.
        The whole check-and-record runs in one transaction under a per-username
        advisory lock, so concurrent
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
        username = username.strip()[:USER_MAX_USERNAME_LENGTH]
        async with self.transaction():
            await self.login_attempt_repository.lock_username(username)

            # Resolve the window once and thread it through: recomputing it for
            # the expiry boundary would use a later ``now`` (and run another
            # ``last_success_at`` query), which can shift the boundary by a row
            # at the window edge and disagree with the count it must match.
            since = (
                datetime.now(UTC) - timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)
                if reauthentication
                else await self._window_start(username)
            )
            attempt_count = await self.login_attempt_repository.count_since(
                username, since, failures_only=not reauthentication
            )
            if attempt_count >= LOGIN_LOCKOUT_THRESHOLD:
                raise LoginThrottledError(
                    await self._retry_after_seconds(
                        username,
                        attempt_count,
                        since,
                        failures_only=not reauthentication,
                    ),
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
        if (
            await self.authenticate(
                user.username, password, ip=ip, reauthentication=True
            )
            is None
        ):
            raise AuthenticationError(
                "error.auth.incorrect_user_passwd",
                "INCORRECT_USER_PASSWD",
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
        attempt_count: int,
        since: datetime,
        *,
        failures_only: bool = True,
    ) -> int:
        """Seconds until enough counted attempts age out to lift the lockout."""
        boundary = await self.login_attempt_repository.expiry_boundary(
            username,
            since,
            attempt_count - LOGIN_LOCKOUT_THRESHOLD,
            failures_only=failures_only,
        )
        if boundary is None:  # pragma: no cover - a counted attempt must exist
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
