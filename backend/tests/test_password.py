"""Changing a password you know, and resetting one you do not.

The reset path is the interesting half: it is unauthenticated, it names an
account, and it sends a code that costs money. Most of what is asserted here
is what the endpoint must *not* reveal — that the account exists, that it has
a verified address, that a budget was hit — and that a code minted for one
purpose cannot be spent on the other.
"""

from datetime import UTC, datetime
from typing import ClassVar

from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models import User, UserSession
from app.models.verification_code import VerificationPurposeEnum
from tests.test_auth import ConfiguredUser, create_altcha_payload

# Imported for their side effect of being registered as fixtures here; the
# reset flow drives the very same senders the binding flow does.
from tests.test_contact_verification import (  # noqa: F401
    RecordingSender,
    _clear_cooldown,
    sender,
)

OLD_PASSWORD = "old-horse-battery"  # noqa: S105
NEW_PASSWORD = "new-staple-correct"  # noqa: S105


async def _stored_hash(db_session: AsyncSession, username: str) -> str:
    """Read the hash straight out of the table.

    Not off the seeded ``User`` object: the endpoints commit, which expires
    it, and a refresh would land outside the class-scoped transaction.
    """
    result = await db_session.execute(
        select(User.hashed_password).where(User.username == username),
    )
    return result.scalar_one()


async def _session_count(db_session: AsyncSession, username: str) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(UserSession)
        .where(
            UserSession.user_id
            == select(User.id).where(User.username == username).scalar_subquery(),
        ),
    )
    return int(result.scalar_one())


class TestPasswordChange:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "changer", "password": OLD_PASSWORD},
        {"username": "stubborn", "password": OLD_PASSWORD},
    ]

    async def test_change_replaces_hash_and_rotates_sessions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["changer"]["headers"]
        before = await _stored_hash(db_session, "changer")

        resp = await client.post(
            "/auth/password/change",
            json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        assert token

        after = await _stored_hash(db_session, "changer")
        assert after != before
        assert verify_password(NEW_PASSWORD, after)

        # Exactly one session survives: every old one was revoked and the
        # caller was handed a replacement, so this device stays signed in and
        # no other does.
        assert await _session_count(db_session, "changer") == 1
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # And the token this test class was seeded with is now dead.
        assert (await client.get("/users/me", headers=headers)).status_code == 401

    async def test_wrong_current_password_changes_nothing(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["stubborn"]["headers"]
        before = await _stored_hash(db_session, "stubborn")

        resp = await client.post(
            "/auth/password/change",
            json={"current_password": "not-the-password", "new_password": NEW_PASSWORD},
            headers=headers,
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "INCORRECT_USER_PASSWD"
        assert await _stored_hash(db_session, "stubborn") == before
        # The session it was attempted from is still good — a failed attempt
        # must not sign the owner out.
        assert (await client.get("/users/me", headers=headers)).status_code == 200

    async def test_change_requires_a_session(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/password/change",
            json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert resp.status_code == 401

    async def test_too_short_a_new_password_is_refused(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/password/change",
            json={"current_password": OLD_PASSWORD, "new_password": "12345"},
            headers=self.configured_users["stubborn"]["headers"],
        )
        assert resp.status_code == 422


class TestPasswordReset:
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    VERIFIED_EMAIL = "resetter@example.com"

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "resetter",
            "hashed_password": get_password_hash(OLD_PASSWORD),
            "email": VERIFIED_EMAIL,
            "email_verified_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
        # Has an address on file that nobody ever proved they can read.
        {
            "username": "unverified",
            "hashed_password": get_password_hash(OLD_PASSWORD),
            "email": "unverified@example.com",
        },
    ]

    async def _request(
        self,
        client: AsyncClient,
        username: str,
        channel: str = "email",
    ) -> Response:
        resp = await client.post(
            "/auth/password/reset/request",
            json={
                "username": username,
                "channel": channel,
                "altcha": await create_altcha_payload(client, "password_reset"),
            },
        )
        assert resp.status_code == 202
        return resp

    async def test_reset_sends_a_purpose_bound_code(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        await self._request(client, "resetter")
        target, code, _, purpose = sender.sent[-1]
        assert target == self.VERIFIED_EMAIL
        assert purpose is VerificationPurposeEnum.password_reset

        resp = await client.post(
            "/auth/password/reset/confirm",
            json={
                "username": "resetter",
                "channel": "email",
                "code": code,
                "new_password": NEW_PASSWORD,
            },
        )
        assert resp.status_code == 204
        assert verify_password(NEW_PASSWORD, await _stored_hash(db_session, "resetter"))
        # No session is opened, and any that existed are gone: answering a
        # code must not be as good as knowing the password.
        assert await _session_count(db_session, "resetter") == 0

        # The code is spent.
        resp = await client.post(
            "/auth/password/reset/confirm",
            json={
                "username": "resetter",
                "channel": "email",
                "code": code,
                "new_password": "another-password-entirely",
            },
        )
        assert resp.status_code == 400

    async def test_unknown_account_answers_the_same(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        # The previous test already spent this account's resend cooldown, and
        # a throttled send is invisible from outside by design.
        await _clear_cooldown(db_session, "resetter")
        before = len(sender.sent)
        real = await self._request(client, "resetter")
        ghost = await self._request(client, "nobody_at_all")

        assert real.json() == ghost.json()
        # Only the real account produced a message.
        assert len(sender.sent) == before + 1

    async def test_unverified_address_is_not_sent_to(
        self,
        client: AsyncClient,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        before = len(sender.sent)
        resp = await self._request(client, "unverified")
        assert resp.json()["expires_in"] > 0
        assert len(sender.sent) == before

    async def test_wrong_code_is_refused(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        await _clear_cooldown(db_session, "resetter")
        await self._request(client, "resetter")
        before = await _stored_hash(db_session, "resetter")

        resp = await client.post(
            "/auth/password/reset/confirm",
            json={
                "username": "resetter",
                "channel": "email",
                "code": "000000",
                "new_password": NEW_PASSWORD,
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VERIFICATION_CODE_INVALID"
        assert await _stored_hash(db_session, "resetter") == before

    async def test_unknown_account_cannot_be_told_from_a_bad_code(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/password/reset/confirm",
            json={
                "username": "nobody_at_all",
                "channel": "email",
                "code": "000000",
                "new_password": NEW_PASSWORD,
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "VERIFICATION_CODE_INVALID"


class TestPurposeBinding:
    """A code minted for one purpose must not be spendable on the other.

    This is the control that makes "read me the code we just sent you" a
    weaker attack than it would otherwise be: the binding code a caller can
    talk someone into requesting is not the reset code.
    """

    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "crosser",
            "hashed_password": get_password_hash(OLD_PASSWORD),
            "email": "crosser@example.com",
            "email_verified_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
    ]

    async def test_binding_code_cannot_reset_a_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["crosser"]["headers"]
        resp = await client.post(
            "/verification/email/send",
            json={"email": "crosser@example.com"},
            headers=headers,
        )
        assert resp.status_code == 202
        _, code, _, purpose = sender.sent[-1]
        assert purpose is VerificationPurposeEnum.bind

        before = await _stored_hash(db_session, "crosser")
        resp = await client.post(
            "/auth/password/reset/confirm",
            json={
                "username": "crosser",
                "channel": "email",
                "code": code,
                "new_password": NEW_PASSWORD,
            },
        )
        assert resp.status_code == 400
        assert await _stored_hash(db_session, "crosser") == before

    async def test_reset_code_cannot_bind_an_address(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sender: RecordingSender,  # noqa: F811
        setup_class_users: None,
    ) -> None:
        await _clear_cooldown(db_session, "crosser")
        resp = await client.post(
            "/auth/password/reset/request",
            json={
                "username": "crosser",
                "channel": "email",
                "altcha": await create_altcha_payload(client, "password_reset"),
            },
        )
        assert resp.status_code == 202
        _, code, _, purpose = sender.sent[-1]
        assert purpose is VerificationPurposeEnum.password_reset

        resp = await client.post(
            "/verification/email/confirm",
            json={"email": "crosser@example.com", "code": code},
            headers=self.configured_users["crosser"]["headers"],
        )
        assert resp.status_code == 400
