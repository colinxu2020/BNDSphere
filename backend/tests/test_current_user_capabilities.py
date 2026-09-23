from typing import ClassVar, TypedDict

import pytest
from httpx import AsyncClient

from app.models.user import RoleEnum, User
from app.services.errors import ResourceForbiddenError
from app.services.policies import AccessPolicy


@pytest.mark.parametrize("role", list(RoleEnum))
def test_advertised_roles_match_authorization(role: RoleEnum) -> None:
    user = User(id=1, username="capability-test", role=role)
    advertised = AccessPolicy.effective_roles(role)
    for required in RoleEnum:
        if required == RoleEnum.ban:
            continue
        try:
            AccessPolicy.ensure_role_allowed(user, [required])
        except ResourceForbiddenError:
            assert required not in advertised
        else:
            assert required in advertised


class ConfiguredUser(TypedDict):
    headers: dict[str, str]
    user: User


class TestCurrentUserCapabilities:
    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": role.value, "role": role.value} for role in RoleEnum
    ]
    configured_users: ClassVar[dict[str, ConfiguredUser]]

    @pytest.mark.parametrize(
        ("role", "expected"),
        [
            ("user", ["user"]),
            ("moderator", ["moderator"]),
            ("federation_staff", ["moderator", "federation_staff"]),
            ("admin", ["user", "moderator", "federation_staff", "admin", "dev"]),
            ("dev", ["user", "moderator", "federation_staff", "admin", "dev"]),
        ],
    )
    async def test_current_user_reports_backend_role_capabilities(
        self,
        client: AsyncClient,
        setup_class_users: None,
        role: str,
        expected: list[str],
    ) -> None:
        response = await client.get(
            "/users/me", headers=self.configured_users[role]["headers"]
        )
        assert response.status_code == 200
        assert response.json()["effective_roles"] == expected

    async def test_anonymous_and_banned_users_cannot_get_capabilities(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        assert (await client.get("/users/me")).status_code == 401
        banned = await client.get(
            "/users/me", headers=self.configured_users["ban"]["headers"]
        )
        assert banned.status_code == 403

    async def test_public_profile_does_not_expose_capabilities(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        user_id = self.configured_users["admin"]["user"].id
        response = await client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert "effective_roles" not in response.json()
