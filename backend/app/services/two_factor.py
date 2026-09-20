from datetime import UTC, datetime, timedelta

from app.core import constants
from app.core.security import (
    create_two_factor_token,
    generate_recovery_code,
    hash_recovery_code,
    verify_two_factor_token,
)
from app.core.totp import generate_totp_secret, provisioning_uri, verify_totp
from app.models.recovery_code import RecoveryCode
from app.models.user import User
from app.repositories.recovery_code import RecoveryCodeRepository
from app.repositories.user import UserRepository
from app.schemas.two_factor import (
    RecoveryCodeCreate,
    RecoveryCodes,
    TotpEnrollment,
    TwoFactorMethodEnum,
    TwoFactorStatus,
)
from app.schemas.verification_code import VerificationCodeSent
from app.services.auth import AuthService
from app.services.base import ServiceBase
from app.services.contact_verification import ContactVerificationService
from app.services.errors import (
    AuthenticationError,
    TwoFactorAlreadyEnabledError,
    TwoFactorChallengeInvalidError,
    TwoFactorCodeInvalidError,
    TwoFactorMethodUnavailableError,
    VerificationCodeInvalidError,
)


class TwoFactorService(
    ServiceBase[RecoveryCode, RecoveryCodeCreate, RecoveryCodeCreate],
):
    """Arm, disarm and answer the second factor.

    Three methods share one challenge: a TOTP from an authenticator app, a
    code sent to the account's verified number, and a printed recovery code
    for when the phone holding the first two is gone. The third is not a
    convenience — without it, turning 2FA on is a way to lose an account.

    Every method that changes *how* the account is protected re-checks the
    password. A live session is not enough: the question these routes decide
    is whether a stolen session can remove the thing standing in its way.
    """

    repository: RecoveryCodeRepository

    def __init__(
        self,
        repository: RecoveryCodeRepository,
        user_repository: UserRepository,
        auth_service: AuthService,
        verification_service: ContactVerificationService,
    ) -> None:
        super().__init__(repository)
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.verification_service = verification_service

    # ── login ────────────────────────────────────────────────────────

    @staticmethod
    def methods_for(user: User) -> list[TwoFactorMethodEnum]:
        """List the methods that can answer this account's challenge, best first."""
        methods = []
        if user.totp_enabled:
            methods.append(TwoFactorMethodEnum.totp)
        if user.sms_two_factor_enabled:
            methods.append(TwoFactorMethodEnum.sms)
        if methods:
            # Only offered alongside a real factor: recovery codes exist to
            # rescue an account whose factor is unreachable, so listing them
            # for an account with no factor at all would be nonsense.
            methods.append(TwoFactorMethodEnum.recovery)
        return methods

    @staticmethod
    def begin_challenge(user: User) -> str:
        """Mint the ticket that stands between a correct password and a session."""
        return create_two_factor_token(
            user.id,
            datetime.now(UTC)
            + timedelta(minutes=constants.TWO_FACTOR_CHALLENGE_TTL_MINUTES),
        )

    async def send_login_code(self, token: str) -> VerificationCodeSent:
        """Text a second-factor code to the account named by the ticket."""
        user = await self._user_for_challenge(token)
        if not user.sms_two_factor_enabled or user.phone is None:
            raise TwoFactorMethodUnavailableError(TwoFactorMethodEnum.sms.value)
        return await self.verification_service.send_two_factor_code(user, user.phone)

    async def complete_challenge(
        self,
        token: str,
        method: TwoFactorMethodEnum,
        code: str,
        *,
        ip: str | None,
    ) -> User:
        """Answer the challenge and return the account it belongs to.

        The outcome is recorded as a login attempt, so second-factor guesses
        count against the same per-account lockout the password step uses —
        which is the only thing between six digits and a grinder.
        """
        user = await self._user_for_challenge(token)
        if method not in self.methods_for(user):
            raise TwoFactorMethodUnavailableError(method.value)

        await self.auth_service.ensure_not_locked_out(user.username)
        accepted = await self._verify(user, method, code)
        await self.auth_service.record_attempt(
            user.username,
            ip,
            successful=accepted,
        )
        if not accepted:
            raise TwoFactorCodeInvalidError
        return user

    async def _verify(
        self,
        user: User,
        method: TwoFactorMethodEnum,
        code: str,
    ) -> bool:
        if method is TwoFactorMethodEnum.totp:
            # ``methods_for`` already established both of these; re-checking
            # is how that reaches the type checker, and the fallback is the
            # safe answer either way.
            if user.totp_secret is None:
                return False
            return verify_totp(user.totp_secret, code)
        if method is TwoFactorMethodEnum.sms:
            if user.phone is None:
                return False
            try:
                await self.verification_service.consume_two_factor_code(
                    user,
                    user.phone,
                    code,
                )
            except VerificationCodeInvalidError:
                # Turned into a boolean rather than propagated so this path
                # still records a failed login attempt on the way out. The
                # per-code attempt counter was already incremented and
                # committed inside ``_consume``.
                return False
            return True
        return await self._redeem_recovery_code(user, code)

    async def _user_for_challenge(self, token: str) -> User:
        try:
            user_id = verify_two_factor_token(token)
        except ValueError:
            raise TwoFactorChallengeInvalidError from None
        user = await self.user_repository.get(user_id)
        # A ticket for an account that has since turned 2FA off is not a way
        # in: it was never a credential, only a pointer at the step that is.
        if user is None or not user.two_factor_enabled:
            raise TwoFactorChallengeInvalidError
        return user

    # ── enrollment ───────────────────────────────────────────────────

    async def status(self, user: User) -> TwoFactorStatus:
        return TwoFactorStatus(
            totp_enabled=user.totp_enabled,
            sms_enabled=user.sms_two_factor_enabled,
            sms_available=user.phone is not None and user.phone_verified_at is not None,
            recovery_codes_remaining=await self.repository.count_unconsumed(user.id),
        )

    async def start_totp(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> TotpEnrollment:
        """Mint a secret and hand it over once, for an app to store.

        Refused while TOTP is already on rather than quietly replacing the
        secret: an enrollment that is started and then abandoned would leave
        the account with its second factor switched off and nobody told.
        """
        await self._reauthenticate(user, password, ip=ip)
        if user.totp_enabled:
            raise TwoFactorAlreadyEnabledError(TwoFactorMethodEnum.totp.value)

        secret = generate_totp_secret()
        async with self.transaction():
            user.totp_secret = secret
            user.totp_confirmed_at = None
            await self._save(user)
        return TotpEnrollment(
            secret=secret,
            provisioning_uri=provisioning_uri(
                secret,
                user.username,
                constants.TWO_FACTOR_ISSUER,
            ),
        )

    async def confirm_totp(self, user: User, code: str) -> RecoveryCodes:
        """Prove the app holds the secret, then arm TOTP.

        No password here: ``start_totp`` already asked, and the code itself is
        proof of possession. No attempt cap either — the secret being guessed
        at is the caller's own, and they were handed it a minute ago.
        """
        if user.totp_secret is None or user.totp_enabled:
            raise TwoFactorMethodUnavailableError(TwoFactorMethodEnum.totp.value)
        if not verify_totp(user.totp_secret, code):
            raise TwoFactorCodeInvalidError

        async with self.transaction():
            user.totp_confirmed_at = datetime.now(UTC)
            await self._save(user)
        return await self._mint_recovery_codes(user)

    async def disable_totp(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> None:
        await self._reauthenticate(user, password, ip=ip)
        async with self.transaction():
            user.totp_secret = None
            user.totp_confirmed_at = None
            await self._save(user)
            await self._drop_recovery_codes_if_disarmed(user)

    async def enable_sms(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> RecoveryCodes:
        """Arm the account's verified number as a second factor.

        Nothing to confirm: the number already answered a code when it was
        bound, which is the same proof this would ask for again.
        """
        await self._reauthenticate(user, password, ip=ip)
        if user.phone is None or user.phone_verified_at is None:
            raise TwoFactorMethodUnavailableError(TwoFactorMethodEnum.sms.value)
        if user.sms_two_factor_enabled:
            raise TwoFactorAlreadyEnabledError(TwoFactorMethodEnum.sms.value)

        async with self.transaction():
            user.sms_two_factor_enabled_at = datetime.now(UTC)
            await self._save(user)
        return await self._mint_recovery_codes(user)

    async def disable_sms(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> None:
        await self._reauthenticate(user, password, ip=ip)
        async with self.transaction():
            user.sms_two_factor_enabled_at = None
            await self._save(user)
            await self._drop_recovery_codes_if_disarmed(user)

    async def regenerate_recovery_codes(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> RecoveryCodes:
        await self._reauthenticate(user, password, ip=ip)
        if not user.two_factor_enabled:
            raise TwoFactorMethodUnavailableError(TwoFactorMethodEnum.recovery.value)
        return await self._mint_recovery_codes(user)

    # ── shared ───────────────────────────────────────────────────────

    async def _reauthenticate(
        self,
        user: User,
        password: str,
        *,
        ip: str | None,
    ) -> None:
        """Re-check the password through the throttled, audited path.

        ``AuthService.authenticate`` rather than ``verify_password`` directly,
        so these routes cannot be used as an unthrottled password oracle that
        happens to need a session.
        """
        verified = await self.auth_service.authenticate(
            user.username,
            password,
            ip=ip,
        )
        if verified is None:
            raise AuthenticationError(
                "error.auth.incorrect_user_passwd",
                "INCORRECT_USER_PASSWD",
            )

    async def _mint_recovery_codes(self, user: User) -> RecoveryCodes:
        """Replace the account's recovery codes and return the new set.

        Always a full replacement, never a top-up: the server holds only
        hashes, so it could not show an existing set again, and a screen that
        listed some old codes and some new ones would be a set nobody has a
        complete copy of.
        """
        codes = [generate_recovery_code() for _ in range(constants.RECOVERY_CODE_COUNT)]
        async with self.transaction():
            await self.repository.delete_for_user(user.id)
            for code in codes:
                await self.repository.create(
                    RecoveryCodeCreate(
                        user_id=user.id,
                        code_hash=hash_recovery_code(code),
                    ),
                )
        return RecoveryCodes(recovery_codes=codes)

    async def _redeem_recovery_code(self, user: User, code: str) -> bool:
        async with self.transaction():
            record = await self.repository.get_unconsumed(
                user.id,
                hash_recovery_code(code),
            )
            if record is None:
                return False
            await self.repository.mark_consumed(record, datetime.now(UTC))
        return True

    async def _drop_recovery_codes_if_disarmed(self, user: User) -> None:
        """Bin the codes once the last real factor is off.

        They guard nothing at that point, and leaving them would mean turning
        2FA back on later silently resurrects a code list the owner may have
        thrown away years earlier.
        """
        if not user.two_factor_enabled:
            await self.repository.delete_for_user(user.id)

    async def _save(self, user: User) -> None:
        self.user_repository.db.add(user)
        await self.user_repository.db.flush()
