import re
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from math import ceil

from sqlalchemy.exc import IntegrityError

from app.core import constants
from app.core.security import hash_verification_code
from app.models.legal_consent import CURRENT_LEGAL_DOCUMENT_VERSIONS, LegalDocumentEnum
from app.models.user import User
from app.models.verification_code import VerificationChannelEnum, VerificationCode
from app.repositories.user import UserRepository
from app.repositories.verification_code import VerificationCodeRepository
from app.schemas.contact_policy import ContactPolicyStatus
from app.schemas.verification_code import VerificationCodeCreate, VerificationCodeSent
from app.services.auth import AuthService
from app.services.base import ServiceBase
from app.services.email_sender import EmailSender
from app.services.errors import (
    BadRequestError,
    NotificationChannelUnavailableError,
    ResourceForbiddenError,
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

    async def contact_policy_status(self, user: User) -> ContactPolicyStatus:
        version = CURRENT_LEGAL_DOCUMENT_VERSIONS[LegalDocumentEnum.privacy_policy]
        return ContactPolicyStatus(
            version=version,
            accepted=await self.user_repository.has_legal_consent(
                user.id,
                LegalDocumentEnum.privacy_policy,
                version,
            ),
        )

    async def accept_contact_policy(
        self, user: User, version: date
    ) -> ContactPolicyStatus:
        current = CURRENT_LEGAL_DOCUMENT_VERSIONS[LegalDocumentEnum.privacy_policy]
        if version != current:
            raise BadRequestError(
                "error.verification.policy_changed", "CONTACT_POLICY_CHANGED"
            )
        async with self.transaction():
            await self.user_repository.accept_legal_document(
                user.id, LegalDocumentEnum.privacy_policy, current
            )
        return ContactPolicyStatus(version=current, accepted=True)

    async def _ensure_contact_policy(self, user: User) -> None:
        if not (await self.contact_policy_status(user)).accepted:
            raise ResourceForbiddenError(
                "error.verification.policy_required", "CONTACT_POLICY_REQUIRED"
            )

    async def send_email_code(
        self,
        user: User,
        raw_email: str,
        password: str,
        *,
        ip: str | None,
    ) -> VerificationCodeSent:
        """Send a binding code, after the account owner proves it is them.

        The budget is checked before the password: verifying one is an argon2
        hash, which is expensive by design, so requests that are over quota
        must be turned away before they reach it — otherwise the send budget
        itself becomes the rate limit on a CPU-burning oracle. This early
        pass is unlocked and only decides whether the request is worth the
        hash; the authoritative, locked check still runs inside ``_issue``.
        """
        await self._ensure_contact_policy(user)
        email = normalize_email(raw_email)
        await self._ensure_send_allowed(VerificationChannelEnum.email, user, email)
        await self.auth_service.reauthenticate(user, password, ip=ip)
        await self._ensure_target_free(VerificationChannelEnum.email, email, user)
        code, sent, record_id = await self._issue(
            user, VerificationChannelEnum.email, email
        )
        await self._deliver(
            user.id, VerificationChannelEnum.email, email, code, record_id
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
        """Send an SMS code with the same ordering: budget first, argon2 second."""
        await self._ensure_contact_policy(user)
        phone = normalize_phone(raw_phone)
        await self._ensure_send_allowed(VerificationChannelEnum.sms, user, phone)
        await self.auth_service.reauthenticate(user, password, ip=ip)
        await self._ensure_target_free(VerificationChannelEnum.sms, phone, user)
        code, sent, record_id = await self._issue(
            user, VerificationChannelEnum.sms, phone
        )
        await self._deliver(
            user.id, VerificationChannelEnum.sms, phone, code, record_id
        )
        return sent

    async def _deliver(
        self,
        user_id: int,
        channel: VerificationChannelEnum,
        target: str,
        code: str,
        record_id: int,
    ) -> None:
        try:
            if channel is VerificationChannelEnum.email:
                await self.email_sender.send_code(
                    target, code, constants.EMAIL_CODE_TTL_MINUTES
                )
            else:
                await self.sms_sender.send_code(
                    target, code, constants.SMS_CODE_TTL_MINUTES
                )
        except NotificationChannelUnavailableError as exc:
            if exc.definitely_rejected:
                async with self.transaction():
                    await self.repository.lock_user_channel(user_id, channel)
                    await self.repository.mark_delivery_rejected(record_id)
            # A timeout may have delivered the message. Never revive an older
            # code on that evidence, or refund any failed send's budget.
            raise

    async def _ensure_send_allowed(
        self,
        channel: VerificationChannelEnum,
        user: User,
        target: str,
    ) -> None:
        """Cheap, unlocked budget check run ahead of the password hash.

        Raises the same throttling error as the locked check inside
        ``_issue``, so an over-quota caller never reaches argon2. Racing
        requests can slip past this pass; the locked re-check in ``_issue``
        remains what actually enforces the budget.
        """
        await self._enforce_budgets(
            user,
            channel,
            target,
            _POLICIES[channel],
            datetime.now(UTC),
        )

    async def _issue(
        self,
        user: User,
        channel: VerificationChannelEnum,
        target: str,
    ) -> tuple[str, VerificationCodeSent, int]:
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
        async with self.transaction():
            await self.repository.lock_send_budget(
                channel,
                target,
                global_budget=policy.global_daily is not None,
            )
            await self.repository.lock_user_channel(user.id, channel)
            now = datetime.now(UTC)
            await self._enforce_budgets(user, channel, target, policy, now)
            record = await self.repository.create(
                VerificationCodeCreate(
                    user_id=user.id,
                    channel=channel,
                    target=target,
                    code_hash=hash_verification_code(code),
                    expires_at=now + policy.ttl,
                ),
            )
            record_id = record.id

        return (
            code,
            VerificationCodeSent(
                expires_in=int(policy.ttl.total_seconds()),
                resend_after=constants.VERIFICATION_RESEND_INTERVAL_SECONDS,
            ),
            record_id,
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
        resets = []
        last_sent = await self.repository.last_sent_at(user.id, channel)
        if last_sent is not None and now - last_sent < cooldown:
            resets.append(last_sent + cooldown)

        hourly = timedelta(hours=1)
        daily = timedelta(days=1)
        account_reset = await self.repository.budget_reset_at(
            channel,
            now - hourly,
            policy.per_account_hourly,
            user_id=user.id,
        )
        target_reset = await self.repository.budget_reset_at(
            channel,
            now - daily,
            policy.per_target_daily,
            target=target,
        )
        if account_reset is not None:
            resets.append(account_reset + hourly)
        if target_reset is not None:
            resets.append(target_reset + daily)
        if policy.global_daily is not None:
            global_reset = await self.repository.budget_reset_at(
                channel,
                now - daily,
                policy.global_daily,
            )
            if global_reset is not None:
                resets.append(global_reset + daily)
        if resets:
            raise VerificationSendThrottledError(_seconds_until(max(resets), now))

    # ── confirm ──────────────────────────────────────────────────────

    async def confirm_email_code(self, user: User, raw_email: str, code: str) -> User:
        await self._ensure_contact_policy(user)
        email = normalize_email(raw_email)
        await self._consume(user, VerificationChannelEnum.email, email, code)
        return user

    async def confirm_phone_code(self, user: User, raw_phone: str, code: str) -> User:
        await self._ensure_contact_policy(user)
        phone = normalize_phone(raw_phone)
        await self._consume(user, VerificationChannelEnum.sms, phone, code)
        return user

    async def _consume(
        self,
        user: User,
        channel: VerificationChannelEnum,
        target: str,
        submitted: str,
    ) -> None:
        accepted = False
        async with self.transaction():
            # Same lock as the send path: without it two racing submissions of
            # the same wrong code each read ``attempts`` before the other's
            # increment lands, and the cap counts one attempt instead of two.
            await self.repository.lock_user_channel(user.id, channel)
            now = datetime.now(UTC)
            record = await self.repository.get_active(user.id, channel, target, now)
            if record is not None and (
                record.attempts < constants.VERIFICATION_CODE_MAX_ATTEMPTS
            ):
                accepted = secrets.compare_digest(
                    record.code_hash,
                    hash_verification_code(submitted),
                )
                if accepted:
                    await self.repository.mark_consumed(record, now)
                    # Binding joins this transaction: a failed write must not
                    # consume the code, while rejected guesses still commit.
                    await self._bind(
                        user,
                        email=target
                        if channel is VerificationChannelEnum.email
                        else None,
                        phone=target
                        if channel is VerificationChannelEnum.sms
                        else None,
                    )
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


def _seconds_until(moment: datetime, now: datetime) -> int:
    return max(1, ceil((moment - now).total_seconds()))
