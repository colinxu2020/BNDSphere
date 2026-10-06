import asyncio
import importlib
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, delete, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from starlette.requests import Request

from app.api.request_origin import ensure_trusted_origin
from app.core import constants
from app.core.security import get_password_hash, hash_verification_code
from app.core.settings import SmtpSettings, web_settings
from app.models import User, VerificationCode
from app.models.verification_code import VerificationChannelEnum as Channel
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user import UserRepository
from app.repositories.verification_code import VerificationCodeRepository
from app.schemas.user import AdminUserUpdate
from app.services.auth import AuthService
from app.services.contact_verification import (
    _POLICIES,
    ContactVerificationService,
    _ChannelPolicy,
)
from app.services.email_sender import _send_blocking
from app.services.errors import (
    DuplicateResourceError,
    NotificationChannelUnavailableError,
    VerificationCodeInvalidError,
    VerificationSendThrottledError,
)
from app.services.sms_sender import _raise_for_api_error
from app.services.user import UserService
from tests.conftest import SUPERUSER_TEST_DB_URL


def service(db: AsyncSession) -> ContactVerificationService:
    return ContactVerificationService(
        VerificationCodeRepository(db),
        AuthService(UserRepository(db), LoginAttemptRepository(db)),
    )


def test_login_accepts_explicitly_configured_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_settings(), "cors_origin", "https://school.example.com")
    request = Request(
        {
            "type": "http",
            "scheme": "http",
            "server": ("backend", 8000),
            "path": "/api/v1/auth/login",
            "root_path": "",
            "headers": [
                (b"origin", b"https://school.example.com"),
                (b"sec-fetch-site", b"cross-site"),
            ],
        }
    )
    ensure_trusted_origin(request)


async def test_lowered_budget_waits_until_enough_sends_expire(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    user = User(username=uuid4().hex, hashed_password="unused")
    db_session.add(user)
    await db_session.flush()
    for age in (20, 30, 40):
        db_session.add(
            VerificationCode(
                user_id=user.id,
                channel=Channel.email,
                target="lowered@example.com",
                code_hash=hash_verification_code("123456"),
                created_at=now - timedelta(minutes=age),
                expires_at=now,
            )
        )
    await db_session.commit()
    policy = _ChannelPolicy(timedelta(minutes=10), 2, 100, None)
    with pytest.raises(VerificationSendThrottledError) as error:
        await service(db_session)._enforce_budgets(
            user, Channel.email, "lowered@example.com", policy, now
        )
    assert error.value.headers["Retry-After"] == "1800"


@pytest.mark.parametrize(
    "newest_state", ["used", "expired", "exhausted", "other_target"]
)
async def test_older_codes_never_revive(
    db_session: AsyncSession,
    newest_state: str,
) -> None:
    now = datetime.now(UTC)
    user = User(username=uuid4().hex, hashed_password="unused")
    db_session.add(user)
    await db_session.flush()
    old = VerificationCode(
        user_id=user.id,
        channel=Channel.email,
        target="old@example.com",
        code_hash=hash_verification_code("123456"),
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    db_session.add(old)
    await db_session.flush()
    # Equal timestamps exercise deterministic id ordering as well.
    newest = VerificationCode(
        user_id=user.id,
        channel=Channel.email,
        target="new@example.com" if newest_state == "other_target" else old.target,
        code_hash=hash_verification_code("654321"),
        created_at=now,
        expires_at=now - timedelta(seconds=1)
        if newest_state == "expired"
        else now + timedelta(minutes=10),
        consumed_at=now if newest_state == "used" else None,
        attempts=constants.VERIFICATION_CODE_MAX_ATTEMPTS
        if newest_state == "exhausted"
        else 0,
    )
    db_session.add(newest)
    await db_session.commit()
    with pytest.raises(VerificationCodeInvalidError):
        await service(db_session)._consume(
            user, Channel.email, "old@example.com", "123456"
        )


@pytest.mark.parametrize("scope", ["account", "target", "global"])
async def test_retry_after_tracks_real_window_expiry(
    db_session: AsyncSession,
    scope: str,
) -> None:
    now = datetime.now(UTC)
    user = User(username=uuid4().hex, hashed_password="unused")
    db_session.add(user)
    await db_session.flush()
    channel = Channel.sms if scope == "global" else Channel.email
    age = timedelta(minutes=20) if scope == "account" else timedelta(hours=2)
    db_session.add(
        VerificationCode(
            user_id=user.id,
            channel=channel,
            target="budget@example.com",
            code_hash=hash_verification_code("123456"),
            created_at=now - age,
            expires_at=now,
        )
    )
    await db_session.commit()
    policy = _ChannelPolicy(
        ttl=timedelta(minutes=10),
        per_account_hourly=1 if scope == "account" else 100,
        per_target_daily=1 if scope == "target" else 100,
        global_daily=1 if scope == "global" else None,
    )
    with pytest.raises(VerificationSendThrottledError) as error:
        await service(db_session)._enforce_budgets(
            user, channel, "budget@example.com", policy, now
        )
    window = timedelta(hours=1) if scope == "account" else timedelta(days=1)
    assert error.value.headers["Retry-After"] == str(
        int((window - age).total_seconds())
    )


@pytest.mark.parametrize("scope", ["email_target", "sms_target", "sms_global"])
async def test_concurrent_accounts_cannot_overspend(
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
) -> None:
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)
    channel = Channel.email if scope == "email_target" else Channel.sms
    async with sessions() as seed:
        users = [User(username=uuid4().hex, hashed_password="unused") for _ in range(2)]
        seed.add_all(users)
        await seed.commit()
        user_ids = [user.id for user in users]
        count = await seed.scalar(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.channel == channel,
                VerificationCode.created_at > datetime.now(UTC) - timedelta(days=1),
            )
        )
    monkeypatch.setitem(
        _POLICIES,
        channel,
        _ChannelPolicy(
            ttl=timedelta(minutes=10),
            per_account_hourly=100,
            per_target_daily=100 if scope == "sms_global" else 1,
            global_daily=int(count or 0) + 1 if scope == "sms_global" else None,
        ),
    )
    original = ContactVerificationService._enforce_budgets

    async def widened_check(self, *args):
        await original(self, *args)
        # Ensure competing requests overlap between the check and insert.
        await asyncio.sleep(0.05)

    monkeypatch.setattr(ContactVerificationService, "_enforce_budgets", widened_check)
    target = uuid4().hex

    async def issue(user_id: int, index: int):
        async with sessions() as db:
            user = await db.get(User, user_id)
            assert user is not None
            return await service(db)._issue(
                user,
                channel,
                f"{target}-{index}" if scope == "sms_global" else target,
            )

    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *(issue(user_id, index) for index, user_id in enumerate(user_ids)),
                return_exceptions=True,
            ),
            timeout=10,
        )
        assert (
            sum(
                isinstance(result, VerificationSendThrottledError) for result in results
            )
            == 1
        )
        assert sum(isinstance(result, tuple) for result in results) == 1
        async with sessions() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(VerificationCode)
                    .where(
                        VerificationCode.user_id.in_(user_ids),
                    )
                )
                == 1
            )
    finally:
        async with sessions() as db:
            await db.execute(delete(User).where(User.id.in_(user_ids)))
            await db.commit()


@pytest.mark.parametrize("change", ["same", "profile", "new", "clear"])
async def test_admin_email_edits_reset_only_changed_verification(
    db_session: AsyncSession,
    change: str,
) -> None:
    verified_at = datetime.now(UTC)
    user = User(
        username=uuid4().hex,
        hashed_password="unused",
        email=f"{uuid4().hex}@example.com",
        email_verified_at=verified_at,
    )
    db_session.add(user)
    await db_session.commit()
    updates = {
        "same": {"email": user.email.upper()},
        "profile": {"description": "edited"},
        "new": {"email": f"New{uuid4().hex}@example.com"},
        "clear": {"email": None},
    }
    updated = await UserService(UserRepository(db_session)).update(
        user,
        AdminUserUpdate(**updates[change]),
    )
    assert updated.email_verified_at == (
        None if change in {"new", "clear"} else verified_at
    )
    if updated.email:
        assert updated.email == updated.email.lower()


async def test_historical_email_casing_is_reserved(db_session: AsyncSession) -> None:
    address = f"Owner{uuid4().hex}@example.com"
    user = User(username=uuid4().hex, hashed_password="unused", email=address)
    db_session.add(user)
    await db_session.commit()
    assert await UserRepository(db_session).get_by_email(address.lower()) is user
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                User(
                    username=uuid4().hex,
                    hashed_password="unused",
                    email=address.lower(),
                )
            )
            await db_session.flush()


async def test_reauthentication_accepts_existing_long_password(
    db_session: AsyncSession,
) -> None:
    from app.schemas.verification_code import EmailVerificationSend

    password = "a" * 180
    request = EmailVerificationSend(email="long@example.com", password=password)
    user = User(username=uuid4().hex, hashed_password=get_password_hash(password))
    db_session.add(user)
    await db_session.commit()
    await service(db_session).auth_service.reauthenticate(
        user, request.password, ip=None
    )


def test_smtp_starttls_verifies_certificates(monkeypatch: pytest.MonkeyPatch) -> None:
    smtp = MagicMock()
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp)
    _send_blocking(
        SmtpSettings(smtp_host="smtp.example.com", smtp_from="school@example.com"),
        "student@example.com",
        "123456",
        10,
    )
    context = smtp.return_value.__enter__.return_value.starttls.call_args.kwargs[
        "context"
    ]
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED


@pytest.mark.parametrize("stage", ["refused", "timeout", "quit", "timeout_then_quit"])
def test_smtp_only_explicit_pre_acceptance_failures_are_rejections(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    smtp = MagicMock()
    connection = smtp.return_value.__enter__.return_value
    if stage == "refused":
        connection.send_message.side_effect = smtplib.SMTPDataError(550, b"refused")
    elif stage in {"timeout", "timeout_then_quit"}:
        connection.send_message.side_effect = TimeoutError()
    if stage in {"quit", "timeout_then_quit"}:
        smtp.return_value.__exit__.side_effect = smtplib.SMTPResponseException(
            451, b"quit failed"
        )
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp)
    with pytest.raises(NotificationChannelUnavailableError) as error:
        _send_blocking(
            SmtpSettings(smtp_host="smtp.example.com", smtp_from="school@example.com"),
            "student@example.com",
            "123456",
            10,
        )
    assert error.value.definitely_rejected is (stage == "refused")


@pytest.mark.parametrize(
    "response,rejected",
    [
        ({"Error": {"Code": "AuthFailure", "Message": "refused"}}, True),
        ({"SendStatusSet": [{"Code": "FailedOperation", "Message": "refused"}]}, True),
        ({}, False),
        ({"SendStatusSet": [{}]}, False),
    ],
)
def test_sms_only_explicit_provider_rejections_restore_previous_issuance(
    response: dict, rejected: bool
) -> None:
    with pytest.raises(NotificationChannelUnavailableError) as error:
        _raise_for_api_error({"Response": response}, "+8613800138000")
    assert error.value.definitely_rejected is rejected


@pytest.mark.parametrize("channel", [Channel.email, Channel.sms])
@pytest.mark.parametrize("rejected", [True, False])
async def test_failed_resend_preserves_budget_and_only_restores_on_rejection(
    db_session: AsyncSession,
    channel: Channel,
    rejected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.contact_verification._generate_code", lambda: "654321"
    )
    now = datetime.now(UTC)
    user = User(username=uuid4().hex, hashed_password="unused")
    db_session.add(user)
    await db_session.flush()
    target = (
        f"{uuid4().hex}@example.com" if channel == Channel.email else "+8613800138000"
    )
    old = VerificationCode(
        user_id=user.id,
        channel=channel,
        target=target,
        code_hash=hash_verification_code("123456"),
        created_at=now - timedelta(seconds=61),
        expires_at=now + timedelta(minutes=10),
    )
    db_session.add(old)
    await db_session.commit()
    verifier = service(db_session)
    code, _, record_id = await verifier._issue(user, channel, target)
    sender = verifier.email_sender if channel == Channel.email else verifier.sms_sender
    sender.send_code = AsyncMock(
        side_effect=NotificationChannelUnavailableError(
            channel.value, definitely_rejected=rejected
        )
    )
    with pytest.raises(NotificationChannelUnavailableError):
        await verifier._deliver(user.id, channel, target, code, record_id)
    assert (
        await verifier.repository.count_for_user_since(
            user.id, channel, now - timedelta(hours=1)
        )
        == 2
    )
    assert (
        await db_session.get(VerificationCode, record_id)
    ).delivery_rejected is rejected
    with pytest.raises(VerificationSendThrottledError):
        await verifier._ensure_send_allowed(channel, user, target)
    if rejected:
        with pytest.raises(VerificationCodeInvalidError):
            await verifier._consume(user, channel, target, code)
        await verifier._consume(user, channel, target, "123456")
    else:
        with pytest.raises(VerificationCodeInvalidError):
            await verifier._consume(user, channel, target, "123456")
        await verifier._consume(user, channel, target, code)


@pytest.mark.parametrize("state", ["used", "expired", "exhausted"])
async def test_rejected_resend_does_not_revive_an_older_invalidated_code(
    db_session: AsyncSession,
    state: str,
) -> None:
    now = datetime.now(UTC)
    user = User(username=uuid4().hex, hashed_password="unused")
    db_session.add(user)
    await db_session.flush()
    for number, code in enumerate(("123456", "654321", "000000")):
        db_session.add(
            VerificationCode(
                user_id=user.id,
                channel=Channel.email,
                target="old@example.com",
                code_hash=hash_verification_code(code),
                created_at=now + timedelta(seconds=number),
                expires_at=now - timedelta(seconds=1)
                if number == 1 and state == "expired"
                else now + timedelta(minutes=10),
                consumed_at=now if number == 1 and state == "used" else None,
                attempts=constants.VERIFICATION_CODE_MAX_ATTEMPTS
                if number == 1 and state == "exhausted"
                else 0,
                delivery_rejected=number == 2,
            )
        )
    await db_session.commit()
    with pytest.raises(VerificationCodeInvalidError):
        await service(db_session)._consume(
            user, Channel.email, "old@example.com", "123456"
        )


async def test_admin_email_update_translates_real_case_insensitive_collision(
    db_session: AsyncSession,
) -> None:
    address = f"Historical{uuid4().hex}@example.com"
    owner = User(username=uuid4().hex, hashed_password="unused", email=address)
    other = User(username=uuid4().hex, hashed_password="unused")
    db_session.add_all([owner, other])
    await db_session.commit()
    with pytest.raises(DuplicateResourceError) as error:
        await UserService(UserRepository(db_session)).update(
            other, AdminUserUpdate(email=address.lower())
        )
    assert error.value.error_code == "DUPLICATE_EMAIL"
    assert error.value.status_code == 409


def test_email_index_migration_preserves_conflicting_accounts() -> None:
    migration = importlib.import_module(
        "migrations.versions.d9f4b8c2a601_merge_sessions_and_normalize_email",
    )
    engine = create_engine(
        SUPERUSER_TEST_DB_URL.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                    address = f"Collision{uuid4().hex}@example.com"
                    ids = [
                        connection.scalar(
                            insert(User)
                            .values(
                                username=uuid4().hex,
                                hashed_password="unused",
                                email=email,
                            )
                            .returning(User.id)
                        )
                        for email in (address, address.lower())
                    ]
                    with pytest.raises(
                        RuntimeError, match="Resolve those addresses manually"
                    ):
                        migration.upgrade()
                    assert (
                        len(
                            connection.scalars(
                                select(User.id).where(User.id.in_(ids))
                            ).all()
                        )
                        == 2
                    )
                    connection.execute(delete(User).where(User.id == ids[1]))
                    migration.upgrade()
                    migration.downgrade()
                    migration.upgrade()
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
