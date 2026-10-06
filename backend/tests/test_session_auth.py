"""Cookie-backed sessions: issuing, authenticating, and revoking them."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SESSION_COOKIE_NAME
from app.core.security import generate_session_token, hash_session_token
from app.models import User, UserSession
from tests.test_auth import ConfiguredUser, create_altcha_payload

PASSWORD = "correct-horse-battery"  # noqa: S105


async def _login(client: AsyncClient, username: str) -> str:
    resp = await client.post(
        "/auth/login",
        data={
            "username": username,
            "password": PASSWORD,
            "altcha": await create_altcha_payload(client, "login"),
        },
    )
    assert resp.status_code == 200
    return str(resp.json()["access_token"])


class TestSessionCookie:
    """Login hands back a cookie that authenticates on its own."""

    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "cookie_user", "password": PASSWORD},
    ]

    @pytest.mark.parametrize(
        "headers",
        [
            {"Origin": "https://attacker.example"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Sec-Fetch-Site": "same-site"},
        ],
    )
    async def test_foreign_login_cannot_set_a_session(
        self,
        client: AsyncClient,
        setup_class_users: None,
        headers: dict[str, str],
    ) -> None:
        client.cookies.clear()
        payload = await create_altcha_payload(client, "login")
        response = await client.post(
            "/auth/login",
            headers=headers,
            data={
                "username": "cookie_user",
                "password": PASSWORD,
                "altcha": payload,
            },
        )
        assert response.status_code == 403
        assert "set-cookie" not in response.headers
        # Origin rejection happens before challenge consumption.
        response = await client.post(
            "/auth/login",
            headers={"Origin": "http://127.0.0.1:8000"},
            data={
                "username": "cookie_user",
                "password": PASSWORD,
                "altcha": payload,
            },
        )
        assert response.status_code == 200
        client.cookies.clear()

    async def test_cookie_alone_authenticates(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        token = await _login(client, "cookie_user")
        # The client kept the Set-Cookie from login; no Authorization header
        # is sent here, so only the cookie can be carrying the identity.
        resp = await client.get("/users/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == "cookie_user"

        # ...and the same token works as a bearer, one credential two ways.
        client.cookies.clear()
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "cookie_user"

    async def test_set_cookie_flags(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        client.cookies.clear()
        resp = await client.post(
            "/auth/login",
            data={
                "username": "cookie_user",
                "password": PASSWORD,
                "altcha": await create_altcha_payload(client, "login"),
            },
        )
        assert resp.status_code == 200
        set_cookie = resp.headers["set-cookie"]
        assert f"{SESSION_COOKIE_NAME}=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie
        assert "Path=/" in set_cookie
        client.cookies.clear()

    async def test_token_is_not_stored_in_the_clear(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        token = await _login(client, "cookie_user")
        client.cookies.clear()

        stored = (
            await db_session.scalars(
                select(UserSession.token_hash).where(
                    UserSession.token_hash == hash_session_token(token),
                ),
            )
        ).all()
        assert len(stored) == 1
        # The raw token must appear nowhere in the table.
        all_hashes = (await db_session.scalars(select(UserSession.token_hash))).all()
        assert token not in all_hashes


class TestLogout:
    """Logout ends the session server-side, not just in the browser."""

    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "logout_user", "password": PASSWORD},
    ]

    @pytest.mark.parametrize(
        "headers",
        [
            {"Origin": "https://sibling.school.example", "Sec-Fetch-Site": "same-site"},
            {"Origin": "null", "Referer": "http://127.0.0.1:8000/profile"},
            {"Referer": "https://attacker.example/form"},
            {"Sec-Fetch-Site": "same-site"},
        ],
    )
    async def test_foreign_cookie_writes_cannot_mutate_or_revoke(
        self,
        client: AsyncClient,
        setup_class_users: None,
        headers: dict[str, str],
    ) -> None:
        token = await _login(client, "logout_user")
        update = await client.post(
            "/users/update-requests", headers=headers, json={"description": "forged"}
        )
        assert update.status_code == 403
        response = await client.post("/auth/logout", headers=headers)
        assert response.status_code == 403
        assert "set-cookie" not in response.headers
        assert SESSION_COOKIE_NAME in client.cookies
        # Read-only requests and the genuine session still work.
        assert (await client.get("/users/me", headers=headers)).status_code == 200
        response = await client.post(
            "/auth/logout", headers={"Referer": "http://127.0.0.1:8000/profile"}
        )
        assert response.status_code == 204
        assert (
            await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 401

    async def test_explicit_bearer_clients_do_not_need_cookie_origin_proof(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        token = await _login(client, "logout_user")
        response = await client.post(
            "/auth/logout",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "https://api-client.example",
            },
        )
        assert response.status_code == 204

    async def test_logout_revokes_the_session(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        token = await _login(client, "logout_user")
        assert (await client.get("/users/me")).status_code == 200

        resp = await client.post("/auth/logout")
        assert resp.status_code == 204

        # The cookie is cleared for the browser...
        assert SESSION_COOKIE_NAME not in client.cookies
        # ...and, the part a stateless token could never do, the credential is
        # dead server-side even for a caller that kept a copy.
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "AUTH_TOKEN_INVALID"

    async def test_no_credentials_at_all_is_rejected(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        # The bearer scheme no longer rejects on its own (a cookie-only request
        # is legitimate), so this path has to come back through
        # ``get_current_user`` — same 401, and the same error body as every
        # other auth failure.
        client.cookies.clear()
        resp = await client.get("/users/me")
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "AUTH_TOKEN_INVALID"

    async def test_logout_without_a_session_is_not_an_error(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        client.cookies.clear()
        resp = await client.post("/auth/logout")
        assert resp.status_code == 204

    async def test_cross_site_logout_stripped_by_lax_is_still_rejected(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        # SameSite=Lax strips the cookie from a cross-site POST, so a foreign
        # logout form arrives with no credential at all. It must be refused on
        # origin anyway — otherwise the response still deletes the cookie the
        # request never carried, and any site can sign users out.
        client.cookies.clear()
        resp = await client.post(
            "/auth/logout",
            headers={"Origin": "https://attacker.example"},
        )
        assert resp.status_code == 403
        assert "set-cookie" not in resp.headers


class TestSessionExpiry:
    """An expired row must not authenticate, sweep or no sweep."""

    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "expiry_user", "password": PASSWORD},
    ]

    async def test_expired_session_is_rejected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        user = self.configured_users["expiry_user"]["user"]
        token = generate_session_token()
        db_session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(token),
                # Already past: the daily sweep has not run, so the row is
                # still present and only the query's expiry filter stops it.
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
            ),
        )
        await db_session.flush()

        client.cookies.clear()
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "AUTH_TOKEN_INVALID"

    async def test_session_of_deleted_user_is_rejected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        user = User(username="ephemeral_user", hashed_password="x")  # noqa: S106
        db_session.add(user)
        await db_session.flush()

        token = generate_session_token()
        db_session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )
        await db_session.flush()

        await db_session.delete(user)
        await db_session.flush()

        client.cookies.clear()
        resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
