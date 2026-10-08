"""Binding a verified email address to an account.

The sender is replaced throughout: these tests assert the code *logic* —
budgets, attempt caps, normalization — not that an SMTP relay can be reached.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from typing import ClassVar

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_contact_verification_service
from app.core import constants
from app.main import app
from app.models import LoginAttempt, User, VerificationCode
from app.models.legal_consent import (
    CURRENT_LEGAL_DOCUMENT_VERSIONS,
    LegalConsent,
    LegalDocumentEnum,
)
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user import UserRepository
from app.repositories.verification_code import VerificationCodeRepository
from app.services.auth import AuthService
from app.services.contact_verification import ContactVerificationService
from tests.test_auth import ConfiguredUser

# Every binding send re-checks this, so the seeded accounts need a password
# the tests can type back.
PASSWORD = "contact-binder-pw"  # noqa: S105 -- a fixture credential


class RecordingSender:
    """Stands in for the email sender and keeps what it was handed."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, int]] = []

    async def send_code(self, target: str, code: str, minutes: int) -> None:
        self.sent.append((target, code, minutes))

    @property
    def last_code(self) -> str:
        return self.sent[-1][1]


@pytest_asyncio.fixture(scope="class")
async def sender(
    db_session: AsyncSession, setup_class_users: None
) -> AsyncGenerator[RecordingSender]:
    """Swap the sender for a recorder, and hand it to the test."""
    recorder = RecordingSender()
    for user_id in (await db_session.scalars(select(User.id))).all():
        await UserRepository(db_session).accept_legal_document(
            user_id,
            LegalDocumentEnum.privacy_policy,
            CURRENT_LEGAL_DOCUMENT_VERSIONS[LegalDocumentEnum.privacy_policy],
        )
    await db_session.commit()

    def _override() -> ContactVerificationService:
        return ContactVerificationService(
            VerificationCodeRepository(db_session),
            AuthService(
                UserRepository(db_session),
                LoginAttemptRepository(db_session),
            ),
            email_sender=recorder,  # type: ignore[arg-type]
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


class TestContactReauthenticationBudget:
    configured_users: ClassVar[dict[str, ConfiguredUser]]
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "reauth_binder", "password": PASSWORD},
        {
            "username": "reauth_owner",
            "password": PASSWORD,
            "email": "occupied@example.com",
        },
    ]

    async def test_owned_target_spends_password_budget_before_hashing(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from app.services import auth

        hashes = 0
        original = auth.verify_password

        def count_hashes(password: str, hashed_password: str) -> bool:
            nonlocal hashes
            hashes += 1
            return original(password, hashed_password)

        monkeypatch.setattr(auth, "verify_password", count_hashes)
        headers = self.configured_users["reauth_binder"]["headers"]
        target = "occupied@example.com"
        for _ in range(constants.LOGIN_LOCKOUT_THRESHOLD):
            response = await client.post(
                "/verification/email/send",
                headers=headers,
                json={"email": target, "password": PASSWORD},
            )
            assert response.status_code == 409

        # A successful ordinary login still works, but cannot reset this budget.
        auth_service = AuthService(
            UserRepository(db_session), LoginAttemptRepository(db_session)
        )
        assert await auth_service.authenticate("reauth_binder", PASSWORD, ip=None)
        response = await client.post(
            "/verification/email/send",
            headers=headers,
            json={"email": "free@example.com", "password": PASSWORD},
        )
        assert response.status_code == 429
        assert response.json()["error_code"] == "LOGIN_THROTTLED"
        assert 3500 < int(response.headers["Retry-After"]) <= 3600
        assert hashes == constants.LOGIN_LOCKOUT_THRESHOLD + 1
        attempts = (
            await db_session.scalars(
                select(LoginAttempt).where(
                    LoginAttempt.username == "reauth_binder",
                    LoginAttempt.created_at >= datetime.now(UTC) - timedelta(hours=1),
                )
            )
        ).all()
        assert len(attempts) == constants.LOGIN_LOCKOUT_THRESHOLD + 1
        assert all(attempt.successful for attempt in attempts)
        assert not sender.sent


class TestContactConfirmationAtomicity:
    configured_users: ClassVar[dict[str, ConfiguredUser]]
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {
            "username": "atomic_binder",
            "password": PASSWORD,
            "email": "original@example.com",
        },
        {"username": "atomic_owner", "password": PASSWORD},
    ]

    async def test_binding_conflict_preserves_code_and_wrong_guess_count(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
    ) -> None:
        headers = self.configured_users["atomic_binder"]["headers"]
        target = "atomic@example.com"
        original = "original@example.com"
        response = await client.post(
            "/verification/email/send",
            headers=headers,
            json={"email": target, "password": PASSWORD},
        )
        assert response.status_code == 202
        code = sender.last_code
        wrong = "000000" if code != "000000" else "111111"
        response = await client.post(
            "/verification/email/confirm",
            headers=headers,
            json={"email": target, "code": wrong},
        )
        assert response.status_code == 400

        # Another account takes the target after issuance, exercising the real
        # database uniqueness constraint rather than a mocked binding failure.
        await db_session.execute(
            update(User).where(User.username == "atomic_owner").values(email=target)
        )
        await db_session.commit()
        response = await client.post(
            "/verification/email/confirm",
            headers=headers,
            json={"email": target, "code": code},
        )
        assert response.status_code == 409
        record = (
            await db_session.scalars(
                select(VerificationCode).where(VerificationCode.target == target)
            )
        ).one()
        assert record.consumed_at is None
        assert record.attempts == 1
        assert (
            await db_session.scalar(
                select(User.email).where(User.username == "atomic_binder")
            )
            == original
        )
        await db_session.execute(
            update(User).where(User.username == "atomic_owner").values(email=None)
        )
        await db_session.commit()
        response = await client.post(
            "/verification/email/confirm",
            headers=headers,
            json={"email": target, "code": code},
        )
        assert response.status_code == 200
        assert response.json()["email"] == target
        assert response.json()["email_verified_at"] is not None
        response = await client.post(
            "/verification/email/confirm",
            headers=headers,
            json={"email": target, "code": code},
        )
        assert response.status_code == 400


class TestEmailVerification:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "email_binder", "password": PASSWORD},
        {"username": "email_rival", "email": "taken@example.com", "password": PASSWORD},
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
            json={"email": "Student@Example.com", "password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["expires_in"] == constants.EMAIL_CODE_TTL_MINUTES * 60
        assert body["resend_after"] == constants.VERIFICATION_RESEND_INTERVAL_SECONDS

        # Normalized before it was handed to the sender, so the budgets and
        # the stored address agree on one spelling.
        target, code, _ = sender.sent[-1]
        assert target == "student@example.com"

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
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["email_binder"]["headers"]
        await _clear_cooldown(db_session, "email_binder")
        resp = await client.post(
            "/verification/email/send",
            json={"email": "hashed@example.com", "password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 202
        code = sender.last_code
        rows = (await db_session.execute(select(VerificationCode.code_hash))).scalars()
        assert code not in list(rows)
        # Consume the code so the replay test still sees a used one.
        resp = await client.post(
            "/verification/email/confirm",
            json={"email": "hashed@example.com", "code": code},
            headers=headers,
        )
        assert resp.status_code == 200

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
            json={"email": "student@example.com", "password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 429
        assert resp.json()["error_code"] == "VERIFICATION_SEND_THROTTLED"
        assert int(resp.headers["retry-after"]) >= 1
        # Throttled means *not sent* — otherwise the budget would be theatre.
        assert len(sender.sent) == before

    async def test_throttled_send_never_reaches_the_password_check(
        self,
        client: AsyncClient,
        sender: RecordingSender,
        setup_class_users: None,
    ) -> None:
        # The password check is an argon2 hash — expensive by design — so an
        # over-quota request must be turned away before it runs. A wrong
        # password inside the cooldown therefore gets the throttle, not an
        # authentication error.
        resp = await client.post(
            "/verification/email/send",
            json={"email": "student@example.com", "password": "not-the-password"},
            headers=self.configured_users["email_binder"]["headers"],
        )
        assert resp.status_code == 429
        assert resp.json()["error_code"] == "VERIFICATION_SEND_THROTTLED"

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
            json={"email": "taken@example.com", "password": PASSWORD},
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
            json={"email": "nobody@example.com", "password": PASSWORD},
        )
        assert resp.status_code == 401


class TestContactPolicyRenewal:
    configured_users: ClassVar[dict[str, ConfiguredUser]]
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "legacy_policy_user", "password": PASSWORD},
    ]

    async def test_old_consent_requires_explicit_versioned_acceptance_before_contact_processing(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        headers = self.configured_users["legacy_policy_user"]["headers"]
        user_id = await db_session.scalar(
            select(User.id).where(User.username == "legacy_policy_user")
        )
        await db_session.execute(
            delete(LegalConsent).where(LegalConsent.user_id == user_id)
        )
        old_version = date(2026, 9, 15)
        await UserRepository(db_session).accept_legal_document(
            user_id, LegalDocumentEnum.privacy_policy, old_version
        )
        await db_session.commit()
        current = CURRENT_LEGAL_DOCUMENT_VERSIONS[
            LegalDocumentEnum.privacy_policy
        ].isoformat()
        response = await client.get("/verification/contact-policy", headers=headers)
        assert response.json() == {"version": current, "accepted": False}

        async def unexpected_password_check(*args, **kwargs):
            pytest.fail("A user without renewed consent reached password hashing")

        with monkeypatch.context() as patch:
            patch.setattr(AuthService, "reauthenticate", unexpected_password_check)
            for route, body in [
                ("email/send", {"email": "legacy@example.com", "password": PASSWORD}),
                ("email/confirm", {"email": "legacy@example.com", "code": "123456"}),
            ]:
                response = await client.post(
                    f"/verification/{route}", json=body, headers=headers
                )
                assert response.status_code == 403
                assert response.json()["error_code"] == "CONTACT_POLICY_REQUIRED"
        assert not sender.sent
        assert not (
            await db_session.scalars(
                select(VerificationCode).where(VerificationCode.user_id == user_id)
            )
        ).all()
        for body, status in [
            ({"version": old_version.isoformat(), "accepted": True}, 400),
            ({"version": current, "accepted": False}, 422),
            ({"version": current}, 422),
        ]:
            response = await client.post(
                "/verification/contact-policy", json=body, headers=headers
            )
            assert response.status_code == status
        for _ in range(2):
            response = await client.post(
                "/verification/contact-policy",
                json={"version": current, "accepted": True},
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json() == {"version": current, "accepted": True}
        assert (
            await client.get("/verification/contact-policy", headers=headers)
        ).json()["accepted"]
        versions = (
            await db_session.scalars(
                select(LegalConsent.document_version).where(
                    LegalConsent.user_id == user_id
                )
            )
        ).all()
        assert sorted(versions) == [old_version, date.fromisoformat(current)]
        response = await client.post(
            "/verification/email/send",
            json={"email": "legacy@example.com", "password": PASSWORD},
            headers=headers,
        )
        assert response.status_code == 202
        response = await client.post(
            "/verification/email/confirm",
            json={"email": "legacy@example.com", "code": sender.last_code},
            headers=headers,
        )
        assert response.status_code == 200


class TestWrongCodes:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "code_guesser", "password": PASSWORD}
    ]

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
            json={"email": "guesser@example.com", "password": PASSWORD},
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
            json={"email": "guesser@example.com", "password": PASSWORD},
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
