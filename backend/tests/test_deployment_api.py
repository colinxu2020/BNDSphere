"""API tests for the dev deployment panel endpoints.

GitHub is always monkeypatched out (never hits real network): the service
layer already covers the GitHub-parsing paths in test_deployment_service.py,
what matters here is the role gate and the request/response wiring.
"""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import ClassVar

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
        if "api.github.com" in str(url):
            raise httpx.ConnectError("no network in tests")
        return await original_get(self, url, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.AsyncClient, "get", _raise_for_github)


@pytest.fixture(autouse=True)
def _override_deployment_service(tmp_path: Path) -> AsyncGenerator[None]:
    """Point the router at a throwaway tmp_path instead of real /srv paths."""

    def _factory() -> DeploymentService:
        return DeploymentService(
            app_version="1.2.3",
            github_repo="colinxu2020/BNDSphere",
            github_token=None,
            request_dir=tmp_path / "request",
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


class TestDeploymentUpdateRequest:
    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "upd_dev_user",
            "password": "ada8d837f6b62e24",
            "role": RoleEnum.dev,
        },
    ]

    async def test_malformed_version_is_rejected_and_writes_nothing(
        self,
        client: AsyncClient,
        setup_class_users: None,
        tmp_path: Path,
    ) -> None:
        headers = self.configured_users["upd_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post(
            "/dev/deployment/update",
            json={"version": "1.2.3; rm -rf /"},
            headers=headers,
        )

        assert resp.status_code == 422
        assert not (tmp_path / "request" / "request.json").exists()

    async def test_valid_update_queues_a_request(
        self,
        client: AsyncClient,
        setup_class_users: None,
        tmp_path: Path,
    ) -> None:
        headers = self.configured_users["upd_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post(
            "/dev/deployment/update",
            json={"version": "9.9.9"},
            headers=headers,
        )

        assert resp.status_code == 202
        written = json.loads((tmp_path / "request" / "request.json").read_text())
        assert set(written.keys()) == {"id", "action", "version", "requested_at"}
        assert written["action"] == "update"
        assert written["version"] == "9.9.9"

    async def test_update_already_current_is_rejected(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["upd_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post(
            "/dev/deployment/update",
            json={"version": "1.2.3"},  # matches the overridden app_version
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_update_while_busy_is_conflict(
        self,
        client: AsyncClient,
        setup_class_users: None,
        tmp_path: Path,
    ) -> None:
        status_dir = tmp_path / "status"
        status_dir.mkdir(parents=True)
        (status_dir / "state.json").write_text(json.dumps({"stage": "deploying"}))

        headers = self.configured_users["upd_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post(
            "/dev/deployment/update",
            json={"version": "9.9.9"},
            headers=headers,
        )
        assert resp.status_code == 409


class TestDeploymentRollbackRequest:
    USER_SPECS: ClassVar[list[dict[str, object]]] = [
        {
            "username": "rb_dev_user",
            "password": "ada8d837f6b62e24",
            "role": RoleEnum.dev,
        },
    ]

    async def test_rollback_without_previous_version_is_rejected(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        headers = self.configured_users["rb_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post("/dev/deployment/rollback", headers=headers)
        assert resp.status_code == 400

    async def test_rollback_targets_the_updaters_own_recorded_version(
        self,
        client: AsyncClient,
        setup_class_users: None,
        tmp_path: Path,
    ) -> None:
        # The client sends no version at all — the target can only come from
        # deployed.json, never from the request body (there is no field for it).
        status_dir = tmp_path / "status"
        status_dir.mkdir(parents=True)
        (status_dir / "deployed.json").write_text(
            json.dumps({"previous_version": "1.1.0"}),
        )

        headers = self.configured_users["rb_dev_user"]["headers"]  # type: ignore[attr-defined]
        resp = await client.post("/dev/deployment/rollback", headers=headers)

        assert resp.status_code == 202
        written = json.loads((tmp_path / "request" / "request.json").read_text())
        assert written["action"] == "rollback"
        assert written["version"] == "1.1.0"
