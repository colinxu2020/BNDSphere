"""Unit tests for app.services.deployment.

No DB, no HTTP — httpx calls are monkeypatched. Exercises the shell/python
version_newer parity and the read-degrades-not-raises contract for the deploy
workflow's status files. There is no write path left to test: the panel
cannot start a deploy.
"""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest

from app.services.deployment import (
    DeploymentService,
    reset_release_cache,
    version_newer,
)


@pytest.fixture(autouse=True)
def _clear_release_cache() -> AsyncGenerator[None]:
    """The release cache is module-level (spec'd that way); isolate tests."""
    reset_release_cache()
    yield
    reset_release_cache()


def _service(tmp_path: Path, **overrides: object) -> DeploymentService:
    defaults: dict[str, object] = {
        "app_version": "1.2.3",
        "github_repo": "colinxu2020/BNDSphere",
        "github_token": None,
        "status_dir": tmp_path / "status",
    }
    defaults.update(overrides)
    return DeploymentService(**defaults)  # type: ignore[arg-type]


# ── version_newer: must agree with infra/updater/lib/validate.sh ──


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("v1.2.4", "1.2.3", True),  # leading v stripped
        ("1.2.3", "v1.2.3", False),  # equal is not newer
        ("1.3", "1.2.9", True),  # segment-wise, not lexical
        ("1.2", "1.2.0.0", False),  # differing segment counts, zero-padded, equal
        ("1.2.0.0", "1.2", False),  # same, reversed
        ("1.2.4-rc.1", "1.2.3", True),  # pre-release ignored for ordering
        ("1.2.3-rc.1", "1.2.3", False),  # equal once suffix stripped
        ("garbage", "1.0.0", False),  # non-numeric candidate never newer
        ("1.0.0", "dev", True),  # non-numeric current is older than any real version
        ("dev", "dev", False),  # non-numeric candidate short-circuits first
        ("dev", "1.0.0", False),
    ],
)
def test_version_newer(candidate: str, current: str, *, expected: bool) -> None:
    assert version_newer(candidate, current) is expected


# ── current_version / record_diverged ──


def test_current_version_ignores_disagreeing_deployed_json(tmp_path: Path) -> None:
    service = _service(tmp_path, app_version="1.0.0")
    service.status_dir.mkdir(parents=True)
    (service.status_dir / "deployed.json").write_text(
        json.dumps({"current_version": "9.9.9"}),
    )

    # Ground truth is the baked-in app_version, never the (possibly stale)
    # record an updater crash could have left behind.
    assert service.current_version() == "1.0.0"
    assert service.record_diverged() is True


def test_record_diverged_false_when_agreeing(tmp_path: Path) -> None:
    service = _service(tmp_path, app_version="1.0.0")
    service.status_dir.mkdir(parents=True)
    (service.status_dir / "deployed.json").write_text(
        json.dumps({"current_version": "1.0.0"}),
    )
    assert service.record_diverged() is False


# ── status files degrade instead of raising ──


def test_updater_state_missing_file_is_idle(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service.updater_state() == {"stage": "idle"}


def test_updater_state_unparseable_degrades_to_unknown(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.status_dir.mkdir(parents=True)
    (service.status_dir / "state.json").write_text("{not valid json")

    assert service.updater_state() == {"stage": "unknown"}


def test_deployed_missing_file_is_empty(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service.deployed() == {}


def test_deployed_unparseable_degrades_to_unknown(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.status_dir.mkdir(parents=True)
    (service.status_dir / "deployed.json").write_text("not json at all")

    assert service.deployed() == {"stage": "unknown"}


@pytest.mark.parametrize(
    ("stage", "expected_busy"),
    [
        ("idle", False),
        ("success", False),
        ("rollback_success", False),
        ("failed", False),
        ("migrating", True),
        ("deploying", True),
        ("health_checking", True),
        ("rolling_back", True),
    ],
)
def test_is_busy_matches_updater_terminal_stages(
    tmp_path: Path,
    stage: str,
    *,
    expected_busy: bool,
) -> None:
    service = _service(tmp_path)
    service.status_dir.mkdir(parents=True)
    (service.status_dir / "state.json").write_text(json.dumps({"stage": stage}))

    assert service.is_busy() is expected_busy


def test_previous_version_reads_deployed_json(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.status_dir.mkdir(parents=True)
    (service.status_dir / "deployed.json").write_text(
        json.dumps({"previous_version": "1.0.0"}),
    )
    assert service.previous_version() == "1.0.0"


def test_previous_version_none_when_absent(tmp_path: Path) -> None:
    assert _service(tmp_path).previous_version() is None


def test_log_tail_missing_file_is_empty(tmp_path: Path) -> None:
    assert _service(tmp_path).log_tail() == []


def test_log_tail_caps_to_limit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.status_dir.mkdir(parents=True)
    lines = [f"line {i}" for i in range(5)]
    (service.status_dir / "update.log").write_text("\n".join(lines) + "\n")

    assert service.log_tail(limit=2) == lines[-2:]


# ── latest_release: no real network, httpx is monkeypatched ──


async def test_latest_release_none_when_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise(
        _self: httpx.AsyncClient,
        *_args: object,
        **_kwargs: object,
    ) -> httpx.Response:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "get", _raise)

    service = _service(tmp_path)
    release = await service.latest_release()

    assert release is None
    # Unreachable must NOT be recorded as a successful check.
    assert service.checked_at is None


async def test_latest_release_parses_github_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "tag_name": "v1.5.0",
        "published_at": "2026-01-01T00:00:00Z",
        "body": "notes",
        "html_url": "https://example.com/release",
    }

    async def _fake_get(
        _self: httpx.AsyncClient,
        url: str,
        **_kwargs: object,
    ) -> httpx.Response:
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    service = _service(tmp_path)
    release = await service.latest_release()

    assert release is not None
    assert release.tag == "v1.5.0"
    assert release.notes == "notes"
    assert service.checked_at is not None


async def test_latest_release_none_on_404(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get(
        _self: httpx.AsyncClient,
        url: str,
        **_kwargs: object,
    ) -> httpx.Response:
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    service = _service(tmp_path)
    release = await service.latest_release()

    assert release is None
    # A completed (if empty) check still counts as "checked".
    assert service.checked_at is not None
