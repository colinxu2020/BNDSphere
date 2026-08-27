from datetime import datetime

from pydantic import BaseModel, Field


class VersionCheckResponse(BaseModel):
    """Discourse-shaped version check: flat, cheap, cached, separate from execution."""

    # The configured repository, always present so the panel can name it even
    # before any release has ever been seen. Deriving it from a release URL
    # leaves the card blank on a fresh install, which is when it matters most.
    github_repo: str
    # Deploys are run from GitHub, not from here — this is the link there.
    workflow_runs_url: str
    installed_version: str
    latest_version: str | None = None
    latest_notes: str | None = None
    latest_url: str | None = None
    latest_published_at: str | None = None
    checked_at: datetime | None = None
    is_stale: bool
    has_update: bool


class DeploymentStatusResponse(VersionCheckResponse):
    """The version check plus the updater's own (ISAA-shaped) run state."""

    stage: str
    action: str | None = None
    requested_version: str | None = None
    target_version: str | None = None
    previous_version: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    is_busy: bool
    record_diverged: bool
    log_tail: list[str] = Field(default_factory=list)
