"""Read/write side of the dev deployment panel.

Mirrors two reference designs:
- Discourse: a cheap, cached, periodic *version check* kept completely
  separate from upgrade *execution*.
- ISAA: a status JSON with a state string, timestamps, and a capped log
  array, where a missing or unreadable status file is a normal state, not
  an error.

This module is **read-only**. It has no write path of any kind: deploys are
triggered by a developer running the ``Deploy`` workflow from GitHub, so the
backend never starts one, and cannot. It reads the files that workflow writes
on the host (``state.json``, ``deployed.json``, ``update.log``, bind-mounted
read-only) and reports them.

Consequence worth stating plainly: a fully compromised backend cannot cause a
deployment. It can lie to the panel about nothing, because it owns nothing —
the status it serves is written by the host and mounted read-only.
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import zip_longest
from pathlib import Path
from typing import Any, Final, cast

import httpx

GITHUB_API_BASE: Final[str] = "https://api.github.com"

# Must agree with infra/updater/lib/validate.sh's VERSION_RE and VERSION_MAX_LEN.
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$",
)
VERSION_MAX_LEN: Final[int] = 64

_NUMERIC_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9]+(\.[0-9]+)*$")

# Same set as infra/updater/lib/state.sh's TERMINAL_STAGES.
TERMINAL_STAGES: Final[frozenset[str]] = frozenset(
    {"idle", "success", "rollback_success", "failed"},
)

_CACHE_TTL: Final[timedelta] = timedelta(minutes=5)


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    published_at: str | None
    notes: str | None
    url: str


# Module-level cache: (when the check last succeeded, what it found). A
# transport failure leaves this untouched, so checked_at keeps naming the
# last time GitHub was actually reachable rather than resetting to "now" —
# that is what lets the panel show growing staleness while GitHub is down.
_cache: tuple[datetime, ReleaseInfo | None] | None = None


def reset_release_cache() -> None:
    """Forget the cached GitHub lookup (test-only escape hatch)."""
    global _cache  # noqa: PLW0603
    _cache = None


def _version_key(value: str) -> str:
    """Strip a leading 'v' and any pre-release/build suffix."""
    stripped = value.removeprefix("v")
    return re.split(r"[-+]", stripped, maxsplit=1)[0]


def version_newer(candidate: str, current: str) -> bool:
    """Report whether ``candidate`` is a newer version than ``current``.

    Ports infra/updater/lib/validate.sh's version_newer exactly: dotted
    numeric segments compared left to right, padded with zeros, pre-release
    suffixes ignored for ordering. A non-numeric candidate (garbage tag) is
    never newer. A non-numeric current (the "dev" default) is older than
    any real version.
    """
    cand_key = _version_key(candidate)
    curr_key = _version_key(current)

    if not _NUMERIC_RE.match(cand_key):
        return False
    if not _NUMERIC_RE.match(curr_key):
        return True

    for cand_part, curr_part in zip_longest(
        cand_key.split("."),
        curr_key.split("."),
        fillvalue="0",
    ):
        cand_num, curr_num = int(cand_part), int(curr_part)
        if cand_num != curr_num:
            return cand_num > curr_num
    return False  # equal is not newer


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    """Read a JSON object file, degrading instead of raising.

    Missing file -> ``default`` (a normal state: the updater hasn't run
    yet, or owns nothing here). Unparseable or non-object content ->
    ``{"stage": "unknown"}`` (corrupt, but still a state to render).
    """
    try:
        raw = path.read_text()
    except OSError:
        return default

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"stage": "unknown"}

    if not isinstance(data, dict):
        return {"stage": "unknown"}

    return cast("dict[str, Any]", data)


class DeploymentService:
    def __init__(
        self,
        app_version: str,
        github_repo: str,
        github_token: str | None,
        status_dir: Path,
        deploy_workflow: str = "deploy.yml",
    ) -> None:
        self.app_version = app_version
        self.github_repo = github_repo
        self.github_token = github_token
        self.status_dir = status_dir
        self.deploy_workflow = deploy_workflow

    # ── version check (Discourse-shaped: cheap, cached, separate from execution) ──

    async def _fetch_latest_release(self) -> tuple[bool, ReleaseInfo | None]:
        """Hit GitHub once. Returns (reachable, release).

        ``reachable`` is False only on a transport-level failure (DNS,
        connect, timeout, ...) — that's the one case checked_at must NOT
        advance for. A non-200 response (rate limited, no releases yet, repo
        doesn't exist) is still a completed check: reachable=True,
        release=None.
        """
        url = f"{GITHUB_API_BASE}/repos/{self.github_repo}/releases/latest"
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
        except httpx.HTTPError:
            return False, None

        if resp.status_code != httpx.codes.OK:
            return True, None

        try:
            data = cast("dict[str, Any]", resp.json())
        except ValueError:
            return True, None

        tag = data.get("tag_name")
        if not tag:
            return True, None

        return True, ReleaseInfo(
            tag=tag,
            published_at=data.get("published_at"),
            notes=data.get("body"),
            url=data.get("html_url", ""),
        )

    async def latest_release(self) -> ReleaseInfo | None:
        """Look up the latest GitHub release, cached for 5 minutes.

        Never raises: any HTTP error, non-200, rate limit, or absence of
        releases is a state to render (``None``), not an error.
        """
        global _cache  # noqa: PLW0603
        now = datetime.now(UTC)

        if _cache is not None and now - _cache[0] < _CACHE_TTL:
            return _cache[1]

        reachable, release = await self._fetch_latest_release()
        if reachable:
            _cache = (now, release)
            return release

        # Unreachable: keep serving the last known-good value (if any)
        # without touching checked_at, so staleness is visible.
        return _cache[1] if _cache is not None else None

    @property
    def checked_at(self) -> datetime | None:
        """When the cached lookup last succeeded (Discourse's updated_at)."""
        return _cache[0] if _cache is not None else None

    def current_version(self) -> str:
        """Report the baked-in running version — never deployed.json's record.

        An updater crash mid-write can leave that record ahead of reality;
        trusting it over the running process would confidently report a
        version that is not running (spec §7).
        """
        return self.app_version

    # ── updater status (ISAA-shaped: state string, timestamps, capped log) ──

    def updater_state(self) -> dict[str, Any]:
        return _read_json(self.status_dir / "state.json", {"stage": "idle"})

    def deployed(self) -> dict[str, Any]:
        return _read_json(self.status_dir / "deployed.json", {})

    def log_tail(self, limit: int = 200) -> list[str]:
        path = self.status_dir / "update.log"
        try:
            lines = path.read_text().splitlines()
        except OSError:
            return []
        return lines[-limit:] if limit > 0 else []

    def previous_version(self) -> str | None:
        value = self.deployed().get("previous_version")
        return cast("str | None", value) if isinstance(value, str) else None

    def is_busy(self) -> bool:
        stage = self.updater_state().get("stage", "idle")
        return stage not in TERMINAL_STAGES

    def record_diverged(self) -> bool:
        """Report whether deployed.json's current_version disagrees with reality."""
        recorded = self.deployed().get("current_version")
        return isinstance(recorded, str) and recorded != self.app_version

    # ── the workflow lives on GitHub; this is just the link to it ──

    @property
    def workflow_runs_url(self) -> str:
        """Where a developer goes to actually run a deploy."""
        return (
            f"https://github.com/{self.github_repo}"
            f"/actions/workflows/{self.deploy_workflow}"
        )
