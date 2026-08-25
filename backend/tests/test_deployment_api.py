"""API tests for the dev deployment panel endpoints.

GitHub is always monkeypatched out (never hits real network): the service
layer already covers the GitHub-parsing paths in test_deployment_service.py,
what matters here is the role gate and the request/response wiring.
"""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import ClassVar, Self

import httpx
import pytest
from httpx import AsyncClient

from app.api.dependencies import get_deployment_service
from app.main import app
from app.models.user import RoleEnum
from app.services.deployment import DeploymentService, reset_release_cache

DEPLOYMENT_STATUS_URL = "/dev/deployment/status"


@pytest.fixture(autouse=True)
def _clear_release_cache() -> AsyncGenerator[None]:
    reset_release_cache()
    yield
    reset_release_cache()


@pytest.fixture(autouse=True)
def _github_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """GitHub calls fail at the transport level; the test client's own
    ASGI-transport requests to our app must still go through untouched.
    """
    original_get = httpx.AsyncClient.get

    async def _raise_for_github(
        self: httpx.AsyncClient,
        url: httpx.URL | str,
        *args: object,
        **kwargs: object,
    ) -> httpx.Response:
        # Compare the parsed host, not a substring of the whole URL: a
        # substring check also matches something like
        # "https://evil.example/?x=api.github.com", which is why CodeQL flags
        # the pattern (py/incomplete-url-substring-sanitization).
        if httpx.URL(url).host == "api.github.com":
            raise httpx.ConnectError("no network in tests")
        return await original_get(self, url, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.AsyncClient, "get", _raise_for_github)


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _StubClient:
    """No real GitHub call. The lookup raises, which is the "unreachable"
    branch the status tests assert on. There is no post(): the panel has no
    write path, so any attempt to make one would fail here with AttributeError
    rather than quietly reaching the network.
    """

    def __init__(self, *_a: object, **_kw: object) -> None: ...
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_a: object) -> None: ...

    async def get(self, *_a: object, **_kw: object) -> _Resp:
        raise httpx.ConnectError("stubbed: github unreachable")


@pytest.fixture(autouse=True)
def _stub_github(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", _StubClient)


@pytest.fixture(autouse=True)
def _override_deployment_service(tmp_path: Path) -> AsyncGenerator[None]:
    """Point the router at a throwaway tmp_path instead of real /srv paths."""

    def _factory() -> DeploymentService:
        return DeploymentService(
            app_version="1.2.3",
            github_repo="colinxu2020/BNDSphere",
            github_token=None,
            status_dir=tmp_path / "status",
        )

    app.dependency_overrides[get_deployment_service] = _factory
    yield
    app.dependency_overrides.pop(get_deployment_service, None)


class TestDeploymentRoleGating:
    """dev only, not admin — a deliberate privilege boundary."""

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "dep_dev_user",
            "password": "ada8d837f6b62e24",
            "role": RoleEnum.dev,
        },
        {
            "username": "dep_admin_user",
            "password": "6748dfa41e25ffbf",
            "role": RoleEnum.admin,
        },
        {
            "username": "dep_moderator_user",
            "password": "3f1c9a7b2d4e6f80",
            "role": RoleEnum.moderator,
        },
        {
            "username": "dep_plain_user",
            "password": "8a1f6b2d4e6f8043",
            "role": RoleEnum.user,
        },
    ]

    async def test_dev_can_access_status(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["dep_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.get(DEPLOYMENT_STATUS_URL, headers=headers)
        assert resp.status_code == 200

    async def test_admin_is_forbidden(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        """Managing users/clubs must not confer host-restart access."""
        headers = self.configured_users["dep_admin_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.get(DEPLOYMENT_STATUS_URL, headers=headers)
        assert resp.status_code == 403

    async def test_moderator_is_forbidden(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["dep_moderator_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.get(DEPLOYMENT_STATUS_URL, headers=headers)
        assert resp.status_code == 403

    async def test_plain_user_is_forbidden(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["dep_plain_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.get(DEPLOYMENT_STATUS_URL, headers=headers)
        assert resp.status_code == 403

    async def test_anonymous_is_unauthorized(self, client: AsyncClient) -> None:
        resp = await client.get(DEPLOYMENT_STATUS_URL)
        assert resp.status_code == 401


class TestDeploymentStatusShape:
    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "shape_dev_user",
            "password": "ada8d837f6b62e24",
            "role": RoleEnum.dev,
        },
    ]

    async def test_status_renders_when_github_unreachable(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["shape_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.get(DEPLOYMENT_STATUS_URL, headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["installed_version"] == "1.2.3"
        assert body["latest_version"] is None
        assert body["checked_at"] is None
        assert body["is_stale"] is True
        assert body["has_update"] is False
        # ISAA-shaped run state: no state.json yet -> idle, not busy, no diverge.
        assert body["stage"] == "idle"
        assert body["is_busy"] is False
        assert body["record_diverged"] is False
        assert body["log_tail"] == []


class TestDeploymentIsReadOnly:
    """No write path exists. These are the assertions that keep it that way."""

    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "ro_dev_user",
            "password": "ada8d837f6b62e24",
            "role": RoleEnum.dev,
        },
    ]

    @pytest.mark.parametrize(
        "path",
        ["/dev/deployment/update", "/dev/deployment/rollback"],
    )
    async def test_the_old_write_endpoints_are_gone(
        self,
        client: AsyncClient,
        setup_class_users: None,
        path: str,
    ) -> None:
        headers = self.configured_users["ro_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post(path, json={"version": "9.9.9"}, headers=headers)
        # 405 (not 404): /check is a POST on the same prefix, so the router
        # exists — it simply has no update or rollback verb any more.
        assert resp.status_code in {404, 405}

    async def test_status_links_to_the_workflow_instead_of_deploying(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["ro_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.get(DEPLOYMENT_STATUS_URL, headers=headers)

        assert resp.status_code == 200
        assert resp.json()["workflow_runs_url"] == (
            "https://github.com/colinxu2020/BNDSphere/actions/workflows/deploy.yml"
        )
