"""The second factor: TOTP, SMS, and the recovery codes behind both.

Two things matter most here and both are asserted end to end: a correct
password alone must not open a session on an account with 2FA armed, and a
recovery code must work exactly once. The TOTP maths is checked against the
RFC's own vectors, because an implementation that is subtly wrong would pass
every round-trip test written against itself.
"""

import time
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants
from app.core.security import get_password_hash, hash_recovery_code
from app.core.totp import _hotp as hotp
from app.core.totp import generate_totp_secret, match_totp, provisioning_uri
from app.models import RecoveryCode, User
from app.models.verification_code import VerificationCode, VerificationPurposeEnum
from tests.test_auth import ConfiguredUser, create_altcha_payload

# Imported for their side effect of registering as fixtures here: the SMS
# second factor rides the very same sender the binding flow does.
from tests.test_contact_verification import (  # noqa: F401
    RecordingSender,
    _clear_cooldown,
    sender,
)

PASSWORD = "correct-horse-battery"  # noqa: S105

# RFC 6238 Appendix B, SHA-1: the seed is the ASCII "12345678901234567890",
# which is this in base32.
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # noqa: S105 -- a published test vector


class TestTotpPrimitives:
    """The maths, against the RFC rather than against itself."""

    def test_rfc_6238_vectors(self) -> None:
        # (timestamp, the RFC's 8-digit value) — truncated to the 6 digits an
        # authenticator app actually shows.
        for timestamp, expected in (
            (59, "94287082"),
            (1111111109, "07081804"),
            (1111111111, "14050471"),
            (1234567890, "89005924"),
            (2000000000, "69279037"),
        ):
            counter = timestamp // 30
            assert hotp(RFC_SECRET, counter) == expected[-6:]

    def test_accepts_one_step_of_drift_either_way(self) -> None:
        now = time.time()
        counter = int(now // 30)
        for drift in (-1, 0, 1):
            # The step it matched is what the caller records to refuse a
            # replay, so it has to be the drifted one, not "now".
            matched = match_totp(RFC_SECRET, hotp(RFC_SECRET, counter + drift), at=now)
            assert matched == counter + drift
        # Two steps out is a code that has been dead for a minute.
        assert match_totp(RFC_SECRET, hotp(RFC_SECRET, counter + 2), at=now) is None

    def test_malformed_submissions_are_refused_not_crashed(self) -> None:
        # ``compare_digest`` raises on non-ASCII, and ``str.isdigit`` is true
        # for fullwidth digits — which is exactly what a request body can
        # carry, so the length-and-digits guard has to run before the compare.
        fullwidth = "".join(chr(0xFF10 + digit) for digit in range(6))
        for bad in ("", "abcdef", "12345", "1234567", fullwidth):
            assert match_totp(RFC_SECRET, bad) is None

    def test_provisioning_uri_names_the_account(self) -> None:
        secret = generate_totp_secret()
        uri = provisioning_uri(secret, "someone", "BNDSphere")
        assert uri.startswith("otpauth://totp/BNDSphere%3Asomeone?")
        assert f"secret={secret}" in uri
        assert "digits=6" in uri
        assert "period=30" in uri

    def test_recovery_code_hash_ignores_how_it_was_typed(self) -> None:
        canonical = hash_recovery_code("a1b2-c3d4-e5f6-7890")
        assert hash_recovery_code("A1B2C3D4E5F67890") == canonical
        assert hash_recovery_code("  a1b2 c3d4 e5f6 7890  ") == canonical
        assert hash_recovery_code("a1b2-c3d4-e5f6-7891") != canonical


async def _current_code(
    db_session: AsyncSession,
    username: str,
    *,
    steps_ahead: int = 0,
) -> str:
    """Compute the code the account's authenticator would be showing.

    ``steps_ahead`` reaches the next 30-second window, which is still inside
    the accepted drift. Tests need it because a step this account has already
    spent is refused — see ``_spend_totp_step``.
    """
    result = await db_session.execute(
        select(User.totp_secret).where(User.username == username),
    )
    secret = result.scalar_one()
    assert secret is not None
    return hotp(secret, int(time.time() // 30) + steps_ahead)


async def _recovery_code_count(db_session: AsyncSession, username: str) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(RecoveryCode)
        .where(
            RecoveryCode.user_id
            == select(User.id).where(User.username == username).scalar_subquery(),
        ),
    )
    return int(result.scalar_one())


async def _login(client: AsyncClient, username: str) -> dict[str, object]:
    resp = await client.post(
        "/auth/login",
        data={
            "username": username,
            "password": PASSWORD,
            "altcha": await create_altcha_payload(client, "login"),
        },
    )
    return {"status": resp.status_code, "body": resp.json()}


class TestTotpEnrollmentAndLogin:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {"username": "totp_user", "password": PASSWORD},
    ]

    async def test_login_is_one_step_before_anything_is_armed(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        result = await _login(client, "totp_user")
        assert result["status"] == 200

    async def test_enrollment_needs_the_password(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/2fa/totp/start",
            json={"password": "not-the-password"},
            headers=self.configured_users["totp_user"]["headers"],
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "INCORRECT_USER_PASSWD"

    async def test_enroll_confirm_and_then_login_in_two_steps(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["totp_user"]["headers"]

        resp = await client.post(
            "/auth/2fa/totp/start",
            json={"password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 200
        secret = resp.json()["secret"]
        assert resp.json()["provisioning_uri"].startswith("otpauth://totp/")

        # Unconfirmed, so nothing is enforced yet: an abandoned enrollment
        # must not be a way to lock an account out of itself.
        assert (await _login(client, "totp_user"))["status"] == 200

        resp = await client.post(
            "/auth/2fa/totp/confirm",
            json={"code": hotp(secret, int(time.time() // 30))},
            headers=headers,
        )
        assert resp.status_code == 200
        codes = resp.json()["recovery_codes"]
        assert len(codes) == constants.RECOVERY_CODE_COUNT
        assert len(set(codes)) == constants.RECOVERY_CODE_COUNT
        # Stored as hashes only, which is why they can never be shown again.
        stored = await db_session.execute(
            select(RecoveryCode.code_hash).where(
                RecoveryCode.user_id
                == select(User.id)
                .where(User.username == "totp_user")
                .scalar_subquery(),
            ),
        )
        assert set(stored.scalars()) == {hash_recovery_code(code) for code in codes}

        # Now the password alone is not enough.
        result = await _login(client, "totp_user")
        assert result["status"] == 401
        body = result["body"]
        assert isinstance(body, dict)
        assert body["error_code"] == "TWO_FACTOR_REQUIRED"
        assert body["details"]["methods"] == ["totp", "recovery"]
        ticket = body["details"]["two_factor_token"]
        assert ticket

        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": ticket,
                "method": "totp",
                # One step on: ``confirm`` just spent the current one.
                "code": await _current_code(db_session, "totp_user", steps_ahead=1),
            },
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        assert (
            await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 200

    async def test_a_wrong_code_opens_nothing(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        body = (await _login(client, "totp_user"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "totp",
                "code": "000000",
            },
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "TWO_FACTOR_CODE_INVALID"

    async def test_a_code_cannot_be_spent_twice(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        """RFC 6238 §5.2. A code is good for 90 seconds; a login is not.

        Whoever reads it over a shoulder gets the rest of that window, which
        is several logins' worth, unless the verifier remembers the step.
        """
        # Rewind the ledger so this window's code is unspent regardless of
        # which step the enrollment above happened to consume.
        await db_session.execute(
            update(User)
            .where(User.username == "totp_user")
            .values(last_totp_counter=int(time.time() // 30) - 1),
        )
        await db_session.flush()

        code = await _current_code(db_session, "totp_user")
        body = (await _login(client, "totp_user"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "totp",
                "code": code,
            },
        )
        assert resp.status_code == 200

        body = (await _login(client, "totp_user"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "totp",
                "code": code,
            },
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "TWO_FACTOR_CODE_INVALID"

    async def test_sms_cannot_be_answered_when_it_is_not_armed(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        body = (await _login(client, "totp_user"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "sms",
                "code": "000000",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "TWO_FACTOR_METHOD_UNAVAILABLE"

    async def test_a_forged_ticket_is_refused(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": "not.a.token",
                "method": "totp",
                "code": "000000",
            },
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "TWO_FACTOR_CHALLENGE_INVALID"

    async def test_enrolling_over_a_live_authenticator_is_refused(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/2fa/totp/start",
            json={"password": PASSWORD},
            headers=self.configured_users["totp_user"]["headers"],
        )
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "TWO_FACTOR_ALREADY_ENABLED"

    async def test_disabling_takes_the_recovery_codes_with_it(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["totp_user"]["headers"]
        assert await _recovery_code_count(db_session, "totp_user") > 0

        resp = await client.post(
            "/auth/2fa/totp/disable",
            json={"password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 204
        # Nothing is armed, so codes that could answer a challenge would only
        # be a bypass waiting for 2FA to be switched back on.
        assert await _recovery_code_count(db_session, "totp_user") == 0

        resp = await client.get("/auth/2fa", headers=headers)
        assert resp.json() == {
            "totp_enabled": False,
            "sms_enabled": False,
            "sms_available": False,
            "recovery_codes_remaining": 0,
        }
        assert (await _login(client, "totp_user"))["status"] == 200


class TestRecoveryCodes:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {"username": "recoverer", "password": PASSWORD},
    ]

    async def _arm(self, client: AsyncClient) -> list[str]:
        headers = self.configured_users["recoverer"]["headers"]
        resp = await client.post(
            "/auth/2fa/totp/start",
            json={"password": PASSWORD},
            headers=headers,
        )
        secret = resp.json()["secret"]
        resp = await client.post(
            "/auth/2fa/totp/confirm",
            json={"code": hotp(secret, int(time.time() // 30))},
            headers=headers,
        )
        assert resp.status_code == 200
        codes: list[str] = resp.json()["recovery_codes"]
        return codes

    async def test_a_recovery_code_works_exactly_once(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        code = (await self._arm(client))[0]

        body = (await _login(client, "recoverer"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "recovery",
                "code": code,
            },
        )
        assert resp.status_code == 200

        body = (await _login(client, "recoverer"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "recovery",
                "code": code,
            },
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "TWO_FACTOR_CODE_INVALID"

    async def test_regenerating_invalidates_the_old_set(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["recoverer"]["headers"]
        resp = await client.get("/auth/2fa", headers=headers)
        # One of the ten was spent by the previous test.
        assert resp.json()["recovery_codes_remaining"] == (
            constants.RECOVERY_CODE_COUNT - 1
        )

        stale = (
            await db_session.execute(
                select(RecoveryCode.code_hash)
                .where(
                    RecoveryCode.user_id
                    == select(User.id)
                    .where(User.username == "recoverer")
                    .scalar_subquery(),
                )
                .limit(1),
            )
        ).scalar_one()

        resp = await client.post(
            "/auth/2fa/recovery-codes",
            json={"password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 200
        fresh = resp.json()["recovery_codes"]
        assert len(fresh) == constants.RECOVERY_CODE_COUNT
        assert stale not in {hash_recovery_code(code) for code in fresh}
        assert await _recovery_code_count(db_session, "recoverer") == (
            constants.RECOVERY_CODE_COUNT
        )


class TestSmsSecondFactor:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "sms_user",
            "hashed_password": get_password_hash(PASSWORD),
            "phone": "+8613800138000",
            "phone_verified_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
        {"username": "phoneless", "password": PASSWORD},
    ]

    async def test_arming_sms_needs_a_verified_number(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/2fa/sms/enable",
            json={"password": PASSWORD},
            headers=self.configured_users["phoneless"]["headers"],
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "TWO_FACTOR_METHOD_UNAVAILABLE"

    async def test_login_texts_a_purpose_bound_code(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["sms_user"]["headers"]
        resp = await client.post(
            "/auth/2fa/sms/enable",
            json={"password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["recovery_codes"]) == constants.RECOVERY_CODE_COUNT

        body = (await _login(client, "sms_user"))["body"]
        assert isinstance(body, dict)
        assert body["details"]["methods"] == ["sms", "recovery"]
        ticket = body["details"]["two_factor_token"]

        # Nothing has been sent yet: the code costs money, so it goes out when
        # it is asked for rather than on every password submission.
        before = len(sender.sent)
        resp = await client.post(
            "/auth/login/2fa/send",
            json={"two_factor_token": ticket},
        )
        assert resp.status_code == 202
        assert len(sender.sent) == before + 1
        target, code, _, purpose = sender.sent[-1]
        assert target == "+8613800138000"
        assert purpose is VerificationPurposeEnum.two_factor

        resp = await client.post(
            "/auth/login/2fa",
            json={"two_factor_token": ticket, "method": "sms", "code": code},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        assert (
            await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 200

        # And it is spent.
        body = (await _login(client, "sms_user"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa",
            json={
                "two_factor_token": body["details"]["two_factor_token"],
                "method": "sms",
                "code": code,
            },
        )
        assert resp.status_code == 401

    async def test_a_login_code_cannot_rebind_the_number(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        await _clear_cooldown(db_session, "sms_user")
        body = (await _login(client, "sms_user"))["body"]
        assert isinstance(body, dict)
        resp = await client.post(
            "/auth/login/2fa/send",
            json={"two_factor_token": body["details"]["two_factor_token"]},
        )
        assert resp.status_code == 202
        _, code, _, purpose = sender.sent[-1]
        assert purpose is VerificationPurposeEnum.two_factor

        resp = await client.post(
            "/verification/phone/confirm",
            json={"phone": "+8613800138000", "code": code},
            headers=self.configured_users["sms_user"]["headers"],
        )
        assert resp.status_code == 400


async def _age_bind_codes(
    db_session: AsyncSession,
    username: str,
    seconds: int = 90,
) -> None:
    """Push this account's binding codes just past the resend cooldown.

    Not ``_clear_cooldown``: that backdates by two hours, which also takes the
    codes out of the hourly budget window — the very thing these tests are
    trying to fill up.
    """
    await db_session.execute(
        update(VerificationCode)
        .where(
            VerificationCode.user_id
            == select(User.id).where(User.username == username).scalar_subquery(),
            VerificationCode.purpose == VerificationPurposeEnum.bind,
        )
        .values(created_at=datetime.now(UTC) - timedelta(seconds=seconds)),
    )
    await db_session.flush()


class TestEnrollmentExpiry:
    """A started-but-never-finished enrollment is not a standing offer."""

    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {"username": "dawdler", "password": PASSWORD},
    ]

    async def test_a_stale_secret_cannot_be_confirmed_and_is_forgotten(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["dawdler"]["headers"]
        resp = await client.post(
            "/auth/2fa/totp/start",
            json={"password": PASSWORD},
            headers=headers,
        )
        secret = resp.json()["secret"]

        await db_session.execute(
            update(User)
            .where(User.username == "dawdler")
            .values(
                totp_secret_issued_at=datetime.now(UTC)
                - timedelta(minutes=constants.TWO_FACTOR_ENROLLMENT_TTL_MINUTES + 1),
            ),
        )
        await db_session.flush()

        resp = await client.post(
            "/auth/2fa/totp/confirm",
            json={"code": hotp(secret, int(time.time() // 30))},
            headers=headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "TWO_FACTOR_METHOD_UNAVAILABLE"

        # The secret is gone, not merely unusable: a credential nobody holds
        # is one only whoever has the session can still finish arming.
        left = await db_session.scalar(
            select(User.totp_secret).where(User.username == "dawdler"),
        )
        assert left is None


class TestASecondMethodKeepsTheFirstsCodes:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    NUMBER = "+8613800138001"

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "doubler",
            "hashed_password": get_password_hash(PASSWORD),
            "phone": NUMBER,
            "phone_verified_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
    ]

    async def test_arming_sms_after_totp_does_not_reissue(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        """The paper in the drawer has to keep working.

        A fresh set is shown once, on a screen that is about something else
        entirely; the codes printed when TOTP was armed would stop working
        with nobody told.
        """
        headers = self.configured_users["doubler"]["headers"]
        resp = await client.post(
            "/auth/2fa/totp/start",
            json={"password": PASSWORD},
            headers=headers,
        )
        secret = resp.json()["secret"]
        resp = await client.post(
            "/auth/2fa/totp/confirm",
            json={"code": hotp(secret, int(time.time() // 30))},
            headers=headers,
        )
        assert resp.status_code == 200
        printed = resp.json()["recovery_codes"]
        assert len(printed) == constants.RECOVERY_CODE_COUNT

        resp = await client.post(
            "/auth/2fa/sms/enable",
            json={"password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 200
        # Empty means "what you already have still works".
        assert resp.json()["recovery_codes"] == []

        stored = await db_session.execute(
            select(RecoveryCode.code_hash).where(
                RecoveryCode.user_id
                == select(User.id).where(User.username == "doubler").scalar_subquery(),
            ),
        )
        assert set(stored.scalars()) == {hash_recovery_code(c) for c in printed}

    async def test_moving_the_number_disarms_the_sms_factor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        """2FA must not follow the account onto a handset nobody armed."""
        headers = self.configured_users["doubler"]["headers"]
        assert (await client.get("/auth/2fa", headers=headers)).json()["sms_enabled"]

        await _clear_cooldown(db_session, "doubler")
        resp = await client.post(
            "/verification/phone/send",
            json={"phone": "13700137000", "password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 202
        _, code, _, _ = sender.sent[-1]
        resp = await client.post(
            "/verification/phone/confirm",
            json={"phone": "13700137000", "code": code},
            headers=headers,
        )
        assert resp.status_code == 200

        status = (await client.get("/auth/2fa", headers=headers)).json()
        assert status["sms_enabled"] is False
        # Still offered — the new number is verified — but it has to be armed
        # deliberately, with the password, like the first one was.
        assert status["sms_available"] is True


class TestSendBudgetsAreScopedToTheirPurpose:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    NUMBER = "+8613800138002"

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "budgeted",
            "hashed_password": get_password_hash(PASSWORD),
            "phone": NUMBER,
            "phone_verified_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
    ]

    async def test_binding_sends_cannot_starve_the_login_factor(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        """One shared pool would cap an SMS-2FA account at five logins a day.

        Binding happens a handful of times in an account's life; logging in
        happens forever. Counted together, ordinary logins also drain the
        deployment-wide ceiling and take phone verification down with them.
        """
        headers = self.configured_users["budgeted"]["headers"]
        resp = await client.post(
            "/auth/2fa/sms/enable",
            json={"password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 200

        for _ in range(constants.SMS_SEND_MAX_PER_ACCOUNT_PER_HOUR):
            await _age_bind_codes(db_session, "budgeted")
            resp = await client.post(
                "/verification/phone/send",
                json={"phone": self.NUMBER, "password": PASSWORD},
                headers=headers,
            )
            assert resp.status_code == 202
        await _age_bind_codes(db_session, "budgeted")
        resp = await client.post(
            "/verification/phone/send",
            json={"phone": self.NUMBER, "password": PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 429

        body = (await _login(client, "budgeted"))["body"]
        assert isinstance(body, dict)
        before = len(sender.sent)
        resp = await client.post(
            "/auth/login/2fa/send",
            json={"two_factor_token": body["details"]["two_factor_token"]},
        )
        assert resp.status_code == 202
        assert len(sender.sent) == before + 1
