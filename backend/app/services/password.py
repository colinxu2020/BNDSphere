import logging

from app.core import constants
from app.core.security import get_password_hash
from app.models.user import User
from app.models.verification_code import VerificationChannelEnum
from app.repositories.user import UserRepository
from app.schemas.user import AdminUserUpdate, UserCreate
from app.schemas.verification_code import VerificationCodeSent
from app.services.auth import AuthService
from app.services.base import ServiceBase
from app.services.contact_verification import (
    ContactVerificationService,
    verified_target,
)
from app.services.errors import (
    AuthenticationError,
    NotificationChannelUnavailableError,
    VerificationCodeInvalidError,
    VerificationSendThrottledError,
)
from app.services.user_session import UserSessionService

logger = logging.getLogger(__name__)

_TTL_MINUTES: dict[VerificationChannelEnum, int] = {
    VerificationChannelEnum.email: constants.EMAIL_CODE_TTL_MINUTES,
    VerificationChannelEnum.sms: constants.SMS_CODE_TTL_MINUTES,
}


class PasswordService(ServiceBase[User, UserCreate, AdminUserUpdate]):
    """Change a password the owner knows, or reset one they do not.

    Both paths end the same way: the new hash is written and *every* session
    for the account is revoked. A password change that left old sessions alive
    would not evict whoever the change is being made because of.
    """

    repository: UserRepository

    def __init__(
        self,
        repository: UserRepository,
        auth_service: AuthService,
        session_service: UserSessionService,
        verification_service: ContactVerificationService,
    ) -> None:
        super().__init__(repository)
        self.auth_service = auth_service
        self.session_service = session_service
        self.verification_service = verification_service

    # ── change (knows the current password) ──────────────────────────

    async def change(
        self,
        user: User,
        current_password: str,
        new_password: str,
        *,
        ip: str | None,
    ) -> str:
        """Re-authenticate, set the new password, and return a fresh token.

        The current password is checked through ``AuthService.authenticate``
        rather than ``verify_password`` directly, so this route inherits the
        per-account lockout and the audit trail instead of being an
        unthrottled password oracle that happens to need a session.

        Every session is revoked and one new one opened, so the caller stays
        signed in on this device and nowhere else.
        """
        username = user.username
        verified = await self.auth_service.authenticate(
            username,
            current_password,
            ip=ip,
        )
        if verified is None:
            raise AuthenticationError(
                "error.auth.incorrect_user_passwd",
                "INCORRECT_USER_PASSWD",
            )

        await self._set_password(verified, new_password)
        return await self.session_service.issue(verified)

    # ── reset (does not) ─────────────────────────────────────────────

    async def request_reset(
        self,
        username: str,
        channel: VerificationChannelEnum,
    ) -> VerificationCodeSent:
        """Send a reset code, if there is anywhere to send it.

        Returns the identical response whether the account exists, has no
        verified address on this channel, or is out of send budget — the
        endpoint is unauthenticated, so any difference between those cases is
        a way to test which usernames are real.

        ponytail: the timing difference between sending and not sending is
        still observable (an SMTP round trip is not free). Closing that needs
        the send moved onto a queue; the per-IP budget on the endpoint is what
        bounds it until then.
        """
        user = await self.repository.get_by_username(
            username[: constants.USER_MAX_USERNAME_LENGTH],
        )
        target = verified_target(user, channel) if user is not None else None
        if user is not None and target is not None:
            try:
                await self.verification_service.send_reset_code(user, channel, target)
            except (
                VerificationSendThrottledError,
                NotificationChannelUnavailableError,
            ):
                # Swallowed rather than returned: a 429 here says "this
                # account exists and already asked", which is the oracle this
                # whole method exists to avoid.
                logger.warning("Password reset code for %s was not sent", username)

        return VerificationCodeSent(
            expires_in=_TTL_MINUTES[channel] * 60,
            resend_after=constants.VERIFICATION_RESEND_INTERVAL_SECONDS,
        )

    async def confirm_reset(
        self,
        username: str,
        channel: VerificationChannelEnum,
        code: str,
        new_password: str,
    ) -> None:
        """Answer a reset code and set a new password.

        An unknown account and an account with nothing verified on this
        channel both raise the same error a wrong code does, for the same
        reason ``request_reset`` is uniform.

        No session is opened: the caller proves the new password works by
        logging in with it, and handing a session to whoever answered a code
        would make a stolen code as good as a stolen password.
        """
        user = await self.repository.get_by_username(
            username[: constants.USER_MAX_USERNAME_LENGTH],
        )
        target = verified_target(user, channel) if user is not None else None
        if user is None or target is None:
            raise VerificationCodeInvalidError

        await self.verification_service.consume_reset_code(user, channel, target, code)
        await self._set_password(user, new_password)

    # ── shared ───────────────────────────────────────────────────────

    async def _set_password(self, user: User, new_password: str) -> None:
        async with self.transaction():
            user.hashed_password = get_password_hash(new_password)
            self.repository.db.add(user)
            await self.repository.db.flush()
            await self.session_service.revoke_all(user)
