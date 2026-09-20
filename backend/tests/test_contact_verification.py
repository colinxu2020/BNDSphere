"""Binding a verified email address or phone number to an account.

The senders are replaced throughout: these tests assert the code *logic* —
budgets, attempt caps, normalization — not that an SMTP relay or Tencent
Cloud can be reached. ``TestTencentSignature`` is the exception and covers
the one piece of the SMS path that can be checked without a network.
"""

import hashlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_contact_verification_service
from app.core import constants
from app.main import app
from app.models import User, VerificationCode
from app.models.verification_code import VerificationPurposeEnum
from app.repositories.verification_code import VerificationCodeRepository
from app.services.contact_verification import (
    ContactVerificationService,
    normalize_phone,
)
from app.services.errors import VerificationTargetInvalidError
from app.services.sms_sender import build_authorization, canonical_request
from tests.test_auth import ConfiguredUser


class RecordingSender:
    """Stands in for both senders and keeps what it was handed."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, int, VerificationPurposeEnum]] = []

    async def send_code(
        self,
        target: str,
        code: str,
        minutes: int,
        purpose: VerificationPurposeEnum = VerificationPurposeEnum.bind,
    ) -> None:
        self.sent.append((target, code, minutes, purpose))

    @property
    def last_code(self) -> str:
        return self.sent[-1][1]

    @property
    def last_purpose(self) -> VerificationPurposeEnum:
        return self.sent[-1][3]


@pytest_asyncio.fixture(scope="class")
async def sender(db_session: AsyncSession) -> AsyncGenerator[RecordingSender]:
    """Swap both channels for a recorder, and hand it to the test."""
    recorder = RecordingSender()

    def _override() -> ContactVerificationService:
        return ContactVerificationService(
            VerificationCodeRepository(db_session),
            email_sender=recorder,  # type: ignore[arg-type]
            sms_sender=recorder,  # type: ignore[arg-type]
        )

    app.dependency_overrides[get_contact_verification_service] = _override
    yield recorder
    app.dependency_overrides.pop(get_contact_verification_service, None)


async def _clear_cooldown(db_session: AsyncSession, username: str) -> None:
    """Age this account's codes out of the resend cooldown.

    The cooldown is real and tested on its own; every *other* test would
    otherwise need its own user just to be allowed a second send.

    Keyed by username rather than by the seeded ``User`` object: that object
    is expired by the commits the endpoints issue, and touching ``.id`` then
    triggers a refresh that the class-scoped transaction has already moved
    past.
    """
    await db_session.execute(
        update(VerificationCode)
        .where(
            VerificationCode.user_id
            == select(User.id).where(User.username == username).scalar_subquery(),
        )
        .values(created_at=datetime.now(UTC) - timedelta(hours=2)),
    )
    await db_session.flush()


class TestEmailVerification:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "email_binder"},
        {"username": "email_rival", "email": "taken@example.com"},
    ]

    async def test_send_then_confirm_binds_the_address(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["email_binder"]["headers"]
        resp = await client.post(
            "/verification/email/send",
            json={"email": "Student@Example.com"},
            headers=headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["expires_in"] == constants.EMAIL_CODE_TTL_MINUTES * 60
        assert body["resend_after"] == constants.VERIFICATION_RESEND_INTERVAL_SECONDS

        # Normalized before it was handed to the sender, so the budgets and
        # the stored address agree on one spelling.
        target, code, _, purpose = sender.sent[-1]
        assert target == "student@example.com"
        assert purpose is VerificationPurposeEnum.bind

        resp = await client.post(
            "/verification/email/confirm",
            json={"email": "student@example.com", "code": code},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "student@example.com"
        assert resp.json()["email_verified_at"] is not None

    async def test_code_is_not_stored_in_the_clear(
        self,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        code = sender.last_code
        rows = (await db_session.execute(select(VerificationCode.code_hash))).scalars()
        assert code not in list(rows)

    async def test_replaying_a_used_code_fails(
        self,
        client: AsyncClient,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["email_binder"]["headers"]
        resp = await client.post(
            "/verification/email/confirm",
            json={"email": "student@example.com", "code": sender.last_code},
            headers=headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VERIFICATION_CODE_INVALID"

    async def test_resend_inside_the_cooldown_is_throttled(
        self,
        client: AsyncClient,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["email_binder"]["headers"]
        before = len(sender.sent)
        resp = await client.post(
            "/verification/email/send",
            json={"email": "student@example.com"},
            headers=headers,
        )
        assert resp.status_code == 429
        assert resp.json()["error_code"] == "VERIFICATION_SEND_THROTTLED"
        assert int(resp.headers["retry-after"]) >= 1
        # Throttled means *not sent* — otherwise the budget would be theatre.
        assert len(sender.sent) == before

    async def test_address_owned_by_another_account_is_refused(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        await _clear_cooldown(db_session, "email_binder")
        before = len(sender.sent)
        resp = await client.post(
            "/verification/email/send",
            json={"email": "taken@example.com"},
            headers=self.configured_users["email_binder"]["headers"],
        )
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "VERIFICATION_TARGET_TAKEN"
        # Refused before the send: a stranger's inbox must not be reachable
        # by anyone who knows the address.
        assert len(sender.sent) == before

    async def test_unauthenticated_send_is_rejected(
        self,
        client: AsyncClient,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/verification/email/send",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 401


class TestWrongCodes:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [{"username": "code_guesser"}]

    async def test_attempts_are_capped_and_burn_the_code(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["code_guesser"]["headers"]
        resp = await client.post(
            "/verification/email/send",
            json={"email": "guesser@example.com"},
            headers=headers,
        )
        assert resp.status_code == 202
        real_code = sender.last_code
        wrong = "000000" if real_code != "000000" else "111111"

        for _ in range(constants.VERIFICATION_CODE_MAX_ATTEMPTS):
            resp = await client.post(
                "/verification/email/confirm",
                json={"email": "guesser@example.com", "code": wrong},
                headers=headers,
            )
            assert resp.status_code == 400

        # The cap is spent, so even the right code no longer opens it — that
        # is what keeps a six-digit secret out of reach.
        resp = await client.post(
            "/verification/email/confirm",
            json={"email": "guesser@example.com", "code": real_code},
            headers=headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VERIFICATION_CODE_INVALID"

    async def test_expired_code_is_refused(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["code_guesser"]["headers"]
        await _clear_cooldown(db_session, "code_guesser")

        resp = await client.post(
            "/verification/email/send",
            json={"email": "guesser@example.com"},
            headers=headers,
        )
        assert resp.status_code == 202
        code = sender.last_code

        await db_session.execute(
            update(VerificationCode)
            .where(
                VerificationCode.user_id
                == select(User.id)
                .where(User.username == "code_guesser")
                .scalar_subquery(),
            )
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
        )
        await db_session.flush()

        resp = await client.post(
            "/verification/email/confirm",
            json={"email": "guesser@example.com", "code": code},
            headers=headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VERIFICATION_CODE_INVALID"


class TestPhoneVerification:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [{"username": "phone_binder"}]

    async def test_number_is_normalized_before_it_is_stored(
        self,
        client: AsyncClient,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["phone_binder"]["headers"]
        resp = await client.post(
            "/verification/phone/send",
            json={"phone": "+86 138 0013 8000"},
            headers=headers,
        )
        assert resp.status_code == 202
        target, code, minutes, purpose = sender.sent[-1]
        assert target == "+8613800138000"
        assert minutes == constants.SMS_CODE_TTL_MINUTES
        assert purpose is VerificationPurposeEnum.bind

        # Confirmed with a different spelling of the same number: if these
        # normalized differently, the budgets would be per-spelling too.
        resp = await client.post(
            "/verification/phone/confirm",
            json={"phone": "13800138000", "code": code},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["phone"] == "+8613800138000"
        assert resp.json()["phone_verified_at"] is not None

    async def test_a_number_that_is_not_a_mainland_mobile_is_refused(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        await _clear_cooldown(db_session, "phone_binder")
        before = len(sender.sent)
        resp = await client.post(
            "/verification/phone/send",
            json={"phone": "+1 202 555 0143"},
            headers=self.configured_users["phone_binder"]["headers"],
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VERIFICATION_TARGET_INVALID"
        assert len(sender.sent) == before


class TestPhoneNormalization:
    """Pure function, no database: every spelling collapses to one key."""

    def test_accepted_spellings_agree(self) -> None:
        for raw in (
            "13800138000",
            "+8613800138000",
            "8613800138000",
            "+86 138 0013 8000",
            "138-0013-8000",
            " (138) 0013 8000 ",
        ):
            assert normalize_phone(raw) == "+8613800138000"

    def test_rejected(self) -> None:
        for raw in ("12800138000", "1380013800", "138001380000", "abc", ""):
            try:
                normalize_phone(raw)
            except VerificationTargetInvalidError:
                continue
            msg = f"{raw!r} should not have been accepted"
            raise AssertionError(msg)


class TestTencentSignature:
    """TC3-HMAC-SHA256, checked where a published answer exists.

    Tencent's Signature v3 documentation works a full example but masks the
    SecretId, so the finished signature cannot be reproduced. What it does
    publish is the SHA-256 of the canonical request — which is the part of
    the scheme with the fiddly assembly rules, and the part this codebase
    could plausibly get wrong. That is checked against their value below.
    The HMAC chain on top of it is only regression-pinned.
    """

    # https://www.tencentcloud.com/document/product/598/32226 — DescribeInstances
    DOC_BODY = (
        '{"Limit": 1, "Filters": [{"Values": ["unnamed"], "Name": "instance-name"}]}'
    )
    DOC_PAYLOAD_SHA = "99d58dfbc6745f6747f36bfca17dee5e6881dc0428a0a36f96199342bc5b4907"
    DOC_CANONICAL_SHA = (
        "2815843035062fffda5fd6f2a44ea8a34818b0dc46f024b8b3786976a3adda7a"
    )

    SMS_PAYLOAD = '{"PhoneNumberSet":["+8613800138000"],"SmsSdkAppId":"1400000000"}'

    def test_canonical_request_matches_tencents_worked_example(self) -> None:
        body_sha = hashlib.sha256(self.DOC_BODY.encode()).hexdigest()
        assert body_sha == self.DOC_PAYLOAD_SHA
        built = canonical_request(
            {
                "content-type": "application/json; charset=utf-8",
                "host": "cvm.tencentcloudapi.com",
            },
            self.DOC_BODY,
        )
        assert hashlib.sha256(built.encode()).hexdigest() == self.DOC_CANONICAL_SHA

    def test_signature_is_stable(self) -> None:
        # Regression pin over the validated canonical request: the credential
        # scope, signed-header list and HMAC chain cannot drift unnoticed.
        auth = build_authorization("AKIDEXAMPLE", "SECRETEXAMPLE", self.SMS_PAYLOAD, 0)
        assert auth == (
            "TC3-HMAC-SHA256 Credential=AKIDEXAMPLE/1970-01-01/sms/tc3_request, "
            "SignedHeaders=content-type;host;x-tc-action, "
            "Signature=f24cfb10060cf923148949473eea747cd82d0bc77331b07cca7c275955be19f8"
        )

    def test_payload_is_covered_by_the_signature(self) -> None:
        # Changing one byte of the body must change the signature, or the
        # message content is not actually authenticated.
        a = build_authorization("id", "key", self.SMS_PAYLOAD, 1_700_000_000)
        b = build_authorization("id", "key", self.SMS_PAYLOAD + " ", 1_700_000_000)
        assert a != b

    def test_timestamp_is_covered_by_the_signature(self) -> None:
        a = build_authorization("id", "key", self.SMS_PAYLOAD, 1_700_000_000)
        b = build_authorization("id", "key", self.SMS_PAYLOAD, 1_700_000_001)
        assert a != b
