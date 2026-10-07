"""Cookie-backed sessions: issuing, authenticating, and revoking them."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import ClassVar
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.constants import SESSION_COOKIE_NAME
from app.core.security import generate_session_token, hash_session_token
from app.core.settings import web_settings
from app.models import User, UserSession
from app.repositories.user_session import UserSessionRepository
from app.services.user_session import UserSessionService
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


@pytest.mark.parametrize("concurrent", [False, True])
async def test_session_issuance_bounds_rows_without_revoking_other_accounts(
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
    concurrent: bool,
) -> None:
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)
    now = datetime.now(UTC)
    old_tokens = [generate_session_token() for _ in range(10)]
    expired_token = generate_session_token()
    other_token = generate_session_token()
    async with sessions() as db:
        users = [User(username=uuid4().hex, hashed_password="unused") for _ in range(2)]
        db.add_all(users)
        await db.flush()
        user_id, other_id = [user.id for user in users]
        db.add_all(
            [
                UserSession(
                    user_id=user_id,
                    token_hash=hash_session_token(token),
                    created_at=now - timedelta(minutes=20 - index),
                    expires_at=now + timedelta(days=1),
                )
                for index, token in enumerate(old_tokens)
            ]
        )
        db.add(
            UserSession(
                user_id=user_id,
                token_hash=hash_session_token(expired_token),
                created_at=now,
                expires_at=now - timedelta(seconds=1),
            )
        )
        db.add(
            UserSession(
                user_id=other_id,
                token_hash=hash_session_token(other_token),
                expires_at=now + timedelta(days=1),
            )
        )
        await db.commit()

    # Widen the real insert path so competing requests overlap after trimming.
    create = UserSessionRepository.create

    async def slow_create(self, *args, **kwargs):
        await asyncio.sleep(0.05)
        return await create(self, *args, **kwargs)

    monkeypatch.setattr(UserSessionRepository, "create", slow_create)

    async def issue() -> str:
        async with sessions() as db:
            user = await db.get(User, user_id)
            assert user is not None
            return await UserSessionService(UserSessionRepository(db)).issue(user)

    try:
        tokens = await asyncio.wait_for(
            asyncio.gather(*(issue() for _ in range(2 if concurrent else 1))),
            timeout=10,
        )
        async with sessions() as db:
            service = UserSessionService(UserSessionRepository(db))
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(UserSession)
                    .where(UserSession.user_id == user_id)
                )
                == 10
            )
            assert await service.resolve(old_tokens[0]) is None
            assert await service.resolve(old_tokens[-1]) is not None
            assert await service.resolve(other_token) is not None
            assert (
                await db.scalar(
                    select(UserSession.id).where(
                        UserSession.token_hash == hash_session_token(expired_token)
                    )
                )
                is None
            )
            for token in tokens:
                assert await service.resolve(token) is not None
    finally:
        async with sessions() as db:
            await db.execute(delete(User).where(User.id.in_([user_id, other_id])))
            await db.commit()


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
            {"Referer": "https://attacker.example/settings"},
            {"Referer": "http://[invalid"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Sec-Fetch-Site": "same-site"},
        ],
    )
    async def test_foreign_login_cannot_set_a_session(
        self,
        client: AsyncClient,
        setup_class_users: None,
        headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The wildcard the dev/test settings run with matches any origin;
        # pin a concrete one so "foreign" is actually foreign.
        monkeypatch.setattr(web_settings(), "cors_origin", "https://school.example.com")
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
        assert response.json() == {
            "message_key": "error.auth.untrusted_origin",
            "error_code": "UNTRUSTED_ORIGIN",
            "details": {},
        }
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
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Same wildcard caveat as the login test above.
        monkeypatch.setattr(web_settings(), "cors_origin", "https://school.example.com")
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
        client.cookies.clear()
        response = await client.post(
            "/auth/logout",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "https://api-client.example",
            },
        )
        assert response.status_code == 204

    @pytest.mark.parametrize("foreign", [False, True])
    async def test_logout_with_both_credentials_checks_origin_and_revokes_both(
        self,
        client: AsyncClient,
        setup_class_users: None,
        monkeypatch: pytest.MonkeyPatch,
        foreign: bool,
    ) -> None:
        monkeypatch.setattr(web_settings(), "cors_origin", "https://school.example.com")
        bearer = await _login(client, "logout_user")
        cookie = await _login(client, "logout_user")
        response = await client.post(
            "/auth/logout",
            headers={
                "Authorization": f"Bearer {bearer}",
                "Origin": "https://attacker.example"
                if foreign
                else "https://school.example.com",
            },
        )
        assert response.status_code == (403 if foreign else 204)
        if foreign:
            assert "set-cookie" not in response.headers
        for token in (bearer, cookie):
            assert (
                await client.get(
                    "/users/me", headers={"Authorization": f"Bearer {token}"}
                )
            ).status_code == (200 if foreign else 401)
        if foreign:
            response = await client.post(
                "/auth/logout",
                headers={
                    "Authorization": f"Bearer {bearer}",
                    "Origin": "https://school.example.com",
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
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # SameSite=Lax strips the cookie from a cross-site POST, so a foreign
        # logout form arrives with no credential at all. It must be refused on
        # origin anyway — otherwise the response still deletes the cookie the
        # request never carried, and any site can sign users out.
        monkeypatch.setattr(web_settings(), "cors_origin", "https://school.example.com")
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
