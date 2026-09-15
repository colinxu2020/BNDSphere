from typing import ClassVar, TypedDict

from httpx import AsyncClient

from app.models import User

VALID_CONSENTS = {
    "accepted_privacy_policy": True,
    "accepted_user_agreement": True,
    "accepted_cross_border_transfer": True,
}


class ConfiguredUser(TypedDict):
    """Shape of the ``configured_users`` mapping set by ``setup_class_users``."""

    headers: dict[str, str]
    user: User


class TestRegister:
    """Registration endpoint: success, duplicate, and validation paths.

    ``existing_user`` is seeded by the ``setup_class_users`` fixture, so the
    duplicate-username test is independent of test execution order.
    """

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "existing_user", "password": "seed-password-not-used"},
    ]

    async def test_register_creates_new_user(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        payload = {
            "username": "brand_new_user",
            "password": "ada8d837f6b62e24",
            **VALID_CONSENTS,
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "brand_new_user"
        assert isinstance(body["id"], int)
        assert "hashed_password" not in body

    async def test_register_duplicate_username(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        payload = {
            "username": "existing_user",
            "password": "6748dfa41e25ffbf",
            **VALID_CONSENTS,
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409
        body = resp.json()
        assert body["message_key"] == "error.user.duplicate_username"
        assert body["error_code"] == "DUPLICATE_USERNAME"
        assert body["details"] == {"username": "existing_user"}

    async def test_register_rejects_short_password(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        # password < min_length(6) → pydantic 422 before any DB write.
        resp = await client.post(
            "/auth/register",
            json={
                "username": "short_pw_user",
                "password": "12345",
                **VALID_CONSENTS,
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail[0]["loc"] == ["body", "password"]
        assert detail[0]["type"] == "string_too_short"

    async def test_register_rejects_missing_fields(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/register",
            json={"username": "no_password_user", **VALID_CONSENTS},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail[0]["loc"] == ["body", "password"]
        assert detail[0]["type"] == "missing"

    async def test_register_requires_all_three_consents(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        for index, field in enumerate(VALID_CONSENTS):
            payload = {
                "username": f"declines_consent_{index}",
                "password": "ada8d837f6b62e24",
                **VALID_CONSENTS,
                field: False,
            }
            resp = await client.post("/auth/register", json=payload)
            assert resp.status_code == 422
            assert resp.json()["detail"][0]["loc"] == ["body", field]

    async def test_register_requires_explicit_consents(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/register",
            json={"username": "no_consents_user", "password": "ada8d837f6b62e24"},
        )
        assert resp.status_code == 422
        missing_fields = {item["loc"][-1] for item in resp.json()["detail"]}
        assert missing_fields == set(VALID_CONSENTS)


class TestLogin:
    """Login endpoint: success and failure paths with form-encoded bodies."""

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "login_user", "password": "correct-horse-battery"},
    ]

    async def test_login_success_returns_token(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        # OAuth2PasswordRequestForm requires application/x-www-form-urlencoded,
        # so the body must be sent with ``data=`` (not ``json=``).
        resp = await client.post(
            "/auth/login",
            data={"username": "login_user", "password": "correct-horse-battery"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"  # noqa: S105
        # JWT is three dot-separated segments: header.payload.signature.
        assert body["access_token"].count(".") == 2

    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/login",
            data={"username": "login_user", "password": "wrong-password"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["message_key"] == "error.auth.incorrect_user_passwd"
        assert body["error_code"] == "INCORRECT_USER_PASSWD"

    async def test_login_unknown_user(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.post(
            "/auth/login",
            data={"username": "ghost_user", "password": "whatever-password"},
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "INCORRECT_USER_PASSWD"


class TestTokenValidation:
    """Token chain: verify_access_token → get_current_user → user lookup."""

    # Populated by the ``setup_class_users`` fixture at class setup time.
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "token_user", "password": "ada8d837f6b62e24"},
    ]

    async def test_valid_token_accesses_me(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        configured = self.configured_users["token_user"]
        resp = await client.get("/users/me", headers=configured["headers"])
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "token_user"
        assert body["id"] == configured["user"].id

    async def test_invalid_token_rejected(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        resp = await client.get(
            "/users/me",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["message_key"] == "error.auth.token_invalid"
        assert body["error_code"] == "AUTH_TOKEN_INVALID"


class TestSeededUsersSurviveRollback:
    """Regression guard: a request-time rollback must not wipe seeded rows.

    The fixture seeds ``seeded_user`` and releases its savepoint before any
    test runs. The single test below triggers a duplicate-username 409 whose
    request-time rollback only unwinds its own savepoint, so the seeded user
    must still conflict on a second registration.
    """

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "seeded_user", "password": "ada8d837f6b62e24"},
    ]

    async def test_seeded_user_survives_request_rollback(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        first = await client.post(
            "/auth/register",
            json={
                "username": "seeded_user",
                "password": "6748dfa41e25ffbf",
                **VALID_CONSENTS,
            },
        )
        assert first.status_code == 409

        # The seeded user must still be present → a second duplicate also 409s.
        second = await client.post(
            "/auth/register",
            json={
                "username": "seeded_user",
                "password": "3f1c9a7b2d4e6f80",
                **VALID_CONSENTS,
            },
        )
        assert second.status_code == 409
        assert second.json()["error_code"] == "DUPLICATE_USERNAME"
