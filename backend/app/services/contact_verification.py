import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy.exc import IntegrityError

from app.core import constants
from app.core.security import hash_verification_code
from app.models.user import User
from app.models.verification_code import (
    VerificationChannelEnum,
    VerificationCode,
    VerificationPurposeEnum,
)
from app.repositories.user import UserRepository
from app.repositories.verification_code import VerificationCodeRepository
from app.schemas.verification_code import VerificationCodeCreate, VerificationCodeSent
from app.services.auth import AuthService
from app.services.base import ServiceBase
from app.services.email_sender import EmailSender
from app.services.errors import (
    VerificationCodeInvalidError,
    VerificationSendThrottledError,
    VerificationTargetInvalidError,
    VerificationTargetTakenError,
)
from app.services.sms_sender import SmsSender

# Mainland China mobile numbers: 11 digits, leading 1, second digit 3-9.
_CN_MOBILE = re.compile(r"^1[3-9]\d{9}$")
_PHONE_NOISE = re.compile(r"[\s\-()]")


def normalize_phone(raw: str) -> str:
    """Reduce a typed phone number to E.164, or reject it.

    Normalizing before anything else is what makes the send budgets hold:
    ``13800138000``, ``+86 138 0013 8000`` and ``86-13800138000`` are one
    number, and if they were stored as three the per-target cap would be
    three times what it says.

    Mainland numbers only — this is a school in Beijing, and accepting
    international numbers would mean international SMS pricing on a budget
    sized for domestic.
    """
    digits = _PHONE_NOISE.sub("", raw)
    if digits.startswith("+") and not digits.startswith("+86"):
        # An explicit country code that is not China. Dropping the "+" and
        # testing the rest against the mainland pattern is not enough: US
        # numbers begin with 1 and are 11 digits too, so "+1 415 555 0100"
        # would pass and text +8614155550100 — a real mainland subscriber who
        # never asked for it.
        raise VerificationTargetInvalidError(VerificationChannelEnum.sms.value)
    digits = digits.removeprefix("+")
    # Safe unconditionally: a mainland mobile number starts with 1, so a
    # leading "86" can only be the country code.
    digits = digits.removeprefix("86")
    if not _CN_MOBILE.match(digits):
        raise VerificationTargetInvalidError(VerificationChannelEnum.sms.value)
    return f"+86{digits}"


def normalize_email(raw: str) -> str:
    """Lowercase and trim. Same reason as ``normalize_phone``: one address,
    one budget line.

    The local part is technically case-sensitive per RFC 5321, but no mail
    provider a student will use treats it that way, and honouring the RFC here
    would mean ``Me@x.com`` and ``me@x.com`` could be bound to two accounts.
    """
    return raw.strip().lower()


def _generate_code() -> str:
    """Mint a zero-padded decimal code from the CSPRNG.

    ``randbelow`` over the full range keeps every value equally likely,
    including the ones with leading zeros that a naive ``randint(100000, ...)``
    would exclude.
    """
    digits = constants.VERIFICATION_CODE_DIGITS
    return f"{secrets.randbelow(10**digits):0{digits}d}"


@dataclass(frozen=True)
class _ChannelPolicy:
    """Everything that differs between email and SMS."""

    ttl: timedelta
    per_account_hourly: int
    per_target_daily: int
    # Deployment-wide daily ceiling, or None when the channel costs nothing
    # to send and only needs the per-account and per-target budgets.
    global_daily: int | None


_POLICIES: dict[VerificationChannelEnum, _ChannelPolicy] = {
    VerificationChannelEnum.email: _ChannelPolicy(
        ttl=timedelta(minutes=constants.EMAIL_CODE_TTL_MINUTES),
        per_account_hourly=constants.EMAIL_SEND_MAX_PER_ACCOUNT_PER_HOUR,
        per_target_daily=constants.EMAIL_SEND_MAX_PER_TARGET_PER_DAY,
        global_daily=None,
    ),
    VerificationChannelEnum.sms: _ChannelPolicy(
        ttl=timedelta(minutes=constants.SMS_CODE_TTL_MINUTES),
        per_account_hourly=constants.SMS_SEND_MAX_PER_ACCOUNT_PER_HOUR,
        per_target_daily=constants.SMS_SEND_MAX_PER_TARGET_PER_DAY,
        global_daily=constants.SMS_GLOBAL_MAX_PER_DAY,
    ),
}


class ContactVerificationService(
    ServiceBase[VerificationCode, VerificationCodeCreate, VerificationCodeCreate],
):
    """Bind a verified email address or phone number to an account.

    Both channels run the same two-step flow — send a code, answer it — and
    differ only in the policy above and which sender carries the message.

    Starting that flow costs the account password. A bound address is where
    password resets are delivered, so a session alone must not be enough to
    move it: otherwise an unattended logged-in browser is a full takeover.
    """

    repository: VerificationCodeRepository

    def __init__(
        self,
        repository: VerificationCodeRepository,
        auth_service: AuthService,
        user_repository: UserRepository | None = None,
        email_sender: EmailSender | None = None,
        sms_sender: SmsSender | None = None,
    ) -> None:
        super().__init__(repository)
        self.auth_service = auth_service
        self.user_repository = user_repository or UserRepository(repository.db)
        self.email_sender = email_sender or EmailSender()
        self.sms_sender = sms_sender or SmsSender()

    # ── send ─────────────────────────────────────────────────────────

    async def send_email_code(
        self,
        user: User,
        raw_email: str,
        password: str,
        *,
        ip: str | None,
    ) -> VerificationCodeSent:
        """Send a binding code, after the account owner proves it is them.

        The password is checked before the budget is touched, so a wrong one
        costs the account nothing but a recorded failed attempt.
        """
        await self.auth_service.reauthenticate(user, password, ip=ip)
        email = normalize_email(raw_email)
        await self._ensure_target_free(VerificationChannelEnum.email, email, user)
        code, sent = await self._issue(
            user,
            VerificationChannelEnum.email,
            VerificationPurposeEnum.bind,
            email,
        )
        await self.email_sender.send_code(
            email,
            code,
            constants.EMAIL_CODE_TTL_MINUTES,
        )
        return sent

    async def send_phone_code(
        self,
        user: User,
        raw_phone: str,
        password: str,
        *,
        ip: str | None,
    ) -> VerificationCodeSent:
        await self.auth_service.reauthenticate(user, password, ip=ip)
        phone = normalize_phone(raw_phone)
        await self._ensure_target_free(VerificationChannelEnum.sms, phone, user)
        code, sent = await self._issue(
            user,
            VerificationChannelEnum.sms,
            VerificationPurposeEnum.bind,
            phone,
        )
        await self.sms_sender.send_code(phone, code, constants.SMS_CODE_TTL_MINUTES)
        return sent

    async def send_reset_code(
        self,
        user: User,
        channel: VerificationChannelEnum,
        target: str,
    ) -> VerificationCodeSent:
        """Send a password-reset code to an address the account already owns.

        No ``_ensure_target_free`` here: ``target`` comes off the account
        rather than off the request, because a reset is asked for by someone
        who is not logged in and letting them name the destination would make
        this a way to mail a code anywhere.
        """
        purpose = VerificationPurposeEnum.password_reset
        code, sent = await self._issue(user, channel, purpose, target)
        if channel is VerificationChannelEnum.email:
            await self.email_sender.send_code(
                target,
                code,
                constants.EMAIL_CODE_TTL_MINUTES,
                purpose,
            )
        else:
            await self.sms_sender.send_code(
                target,
                code,
                constants.SMS_CODE_TTL_MINUTES,
                purpose,
            )
        return sent

    async def consume_reset_code(
        self,
        user: User,
        channel: VerificationChannelEnum,
        target: str,
        code: str,
    ) -> None:
        """Burn a password-reset code, or raise. Binds nothing."""
        await self._consume(
            user,
            channel,
            VerificationPurposeEnum.password_reset,
            target,
            code,
        )

    async def _issue(
        self,
        user: User,
        channel: VerificationChannelEnum,
        purpose: VerificationPurposeEnum,
        target: str,
    ) -> tuple[str, VerificationCodeSent]:
        """Reserve budget and store one code. Returns it for the sender.

        The row is written and committed *before* the message goes out, so a
        provider failure still spends the budget. That is the conservative
        direction on purpose: the send may well have happened, and a failure
        that refunded the quota would turn every provider hiccup into a free
        retry — which is exactly the loop an attacker would aim for on a
        channel that costs money per message.
        """
        policy = _POLICIES[channel]
        code = _generate_code()
        now = datetime.now(UTC)

        async with self.transaction():
            # Two concurrent "resend" clicks would otherwise both read the
            # pre-insert counts and both send.
            await self.repository.lock_user_channel(user.id, channel)
            await self._enforce_budgets(user, channel, target, policy, now)
            await self.repository.create(
                VerificationCodeCreate(
                    user_id=user.id,
                    channel=channel,
                    purpose=purpose,
                    target=target,
                    code_hash=hash_verification_code(code),
                    expires_at=now + policy.ttl,
                ),
            )

        return code, VerificationCodeSent(
            expires_in=int(policy.ttl.total_seconds()),
            resend_after=constants.VERIFICATION_RESEND_INTERVAL_SECONDS,
        )

    async def _enforce_budgets(
        self,
        user: User,
        channel: VerificationChannelEnum,
        target: str,
        policy: _ChannelPolicy,
        now: datetime,
    ) -> None:
        cooldown = timedelta(seconds=constants.VERIFICATION_RESEND_INTERVAL_SECONDS)
        last_sent = await self.repository.last_sent_at(user.id, channel)
        if last_sent is not None and now - last_sent < cooldown:
            raise VerificationSendThrottledError(
                _seconds_until(last_sent + cooldown, now),
            )

        hour_ago = now - timedelta(hours=1)
        if (
            await self.repository.count_for_user_since(user.id, channel, hour_ago)
            >= policy.per_account_hourly
        ):
            raise VerificationSendThrottledError(
                _seconds_until(hour_ago + timedelta(hours=1), now)
            )

        day_ago = now - timedelta(days=1)
        if (
            await self.repository.count_for_target_since(channel, target, day_ago)
            >= policy.per_target_daily
        ):
            raise VerificationSendThrottledError(
                _seconds_until(day_ago + timedelta(days=1), now)
            )

        if policy.global_daily is not None and (
            await self.repository.count_for_channel_since(channel, day_ago)
            >= policy.global_daily
        ):
            # The whole deployment is out of budget for the day. Nothing the
            # caller can do differently, so the retry hint is the window.
            raise VerificationSendThrottledError(int(timedelta(days=1).total_seconds()))

    # ── confirm ──────────────────────────────────────────────────────

    async def confirm_email_code(self, user: User, raw_email: str, code: str) -> User:
        email = normalize_email(raw_email)
        await self._consume(
            user,
            VerificationChannelEnum.email,
            VerificationPurposeEnum.bind,
            email,
            code,
        )
        return await self._bind(user, email=email)

    async def confirm_phone_code(self, user: User, raw_phone: str, code: str) -> User:
        phone = normalize_phone(raw_phone)
        await self._consume(
            user,
            VerificationChannelEnum.sms,
            VerificationPurposeEnum.bind,
            phone,
            code,
        )
        return await self._bind(user, phone=phone)

    async def _consume(
        self,
        user: User,
        channel: VerificationChannelEnum,
        purpose: VerificationPurposeEnum,
        target: str,
        submitted: str,
    ) -> None:
        now = datetime.now(UTC)
        accepted = False
        async with self.transaction():
            # Same lock as the send path: without it two racing submissions of
            # the same wrong code each read ``attempts`` before the other's
            # increment lands, and the cap counts one attempt instead of two.
            await self.repository.lock_user_channel(user.id, channel)
            record = await self.repository.get_active(
                user.id,
                channel,
                purpose,
                target,
                now,
            )
            if record is not None and (
                record.attempts < constants.VERIFICATION_CODE_MAX_ATTEMPTS
            ):
                accepted = secrets.compare_digest(
                    record.code_hash,
                    hash_verification_code(submitted),
                )
                if accepted:
                    await self.repository.mark_consumed(record, now)
                else:
                    await self.repository.record_attempt(record)

        # Raised *after* the block, not inside it: an exception here unwinds
        # the transaction, and the attempt counter is the one thing that must
        # survive a rejected guess. Raising inside rolled the increment back
        # with it, which left the cap counting to five forever.
        if not accepted:
            raise VerificationCodeInvalidError

    async def _bind(
        self,
        user: User,
        email: str | None = None,
        phone: str | None = None,
    ) -> User:
        """Write the confirmed address onto the account.

        The uniqueness check in ``_ensure_target_free`` runs minutes earlier,
        at send time, so the database constraint is what actually decides:
        two people can both be holding a live code for one address.
        """
        now = datetime.now(UTC)
        try:
            async with self.transaction():
                if email is not None:
                    user.email = email
                    user.email_verified_at = now
                if phone is not None:
                    user.phone = phone
                    user.phone_verified_at = now
                self.user_repository.db.add(user)
                await self.user_repository.db.flush()
        except IntegrityError:
            channel = (
                VerificationChannelEnum.email
                if email is not None
                else VerificationChannelEnum.sms
            )
            raise VerificationTargetTakenError(channel.value) from None
        return user

    # ── shared ───────────────────────────────────────────────────────

    async def _ensure_target_free(
        self,
        channel: VerificationChannelEnum,
        target: str,
        user: User,
    ) -> None:
        """Reject an address that already belongs to somebody else.

        Checked before sending as well as at bind time: not for correctness —
        the unique constraint covers that — but so the caller is told now
        instead of after a code they can never usefully answer, and so a
        stranger's phone cannot be made to buzz by anyone who knows the
        number.
        """
        owner = (
            await self.user_repository.get_by_email(target)
            if channel is VerificationChannelEnum.email
            else await self.user_repository.get_by_phone(target)
        )
        if owner is not None and owner.id != user.id:
            raise VerificationTargetTakenError(channel.value)


def verified_target(user: User, channel: VerificationChannelEnum) -> str | None:
    """Return the confirmed address on this channel, or None if there is not one.

    Unverified is the same as absent on purpose: an address nobody proved
    they can read is not something a password may be reset through.
    """
    if channel is VerificationChannelEnum.email:
        return user.email if user.email_verified_at is not None else None
    return user.phone if user.phone_verified_at is not None else None


def _seconds_until(moment: datetime, now: datetime) -> int:
    return max(1, ceil((moment - now).total_seconds()))
