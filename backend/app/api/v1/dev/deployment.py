from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies import DeploymentServiceDep
from app.schemas.deployment import (
    DeploymentStatusResponse,
    UpdateRequestBody,
    VersionCheckResponse,
    WriteRequestResponse,
)
from app.services.deployment import (
    DeploymentAlreadyCurrentError,
    DeploymentInProgressError,
    DeploymentNoPreviousVersionError,
    DeploymentService,
    version_newer,
)

router = APIRouter(tags=["Dev: Deployment"])

# Same window as the release cache: if the last successful GitHub check is
# older than this, GitHub has likely been unreachable for a while and the
# panel should say so rather than silently show old data as current.
STALE_AFTER = timedelta(minutes=5)


async def _version_check(service: DeploymentService) -> dict[str, Any]:
    release = await service.latest_release()
    checked_at = service.checked_at
    current = service.current_version()
    latest_tag = release.tag if release else None

    is_stale = checked_at is None or (datetime.now(UTC) - checked_at) > STALE_AFTER
    has_update = latest_tag is not None and version_newer(latest_tag, current)

    return {
        "installed_version": current,
        "latest_version": latest_tag,
        "latest_notes": release.notes if release else None,
        "latest_url": release.url if release else None,
        "latest_published_at": release.published_at if release else None,
        "checked_at": checked_at,
        "is_stale": is_stale,
        "has_update": has_update,
    }


@router.get("/status")
async def get_status(service: DeploymentServiceDep) -> DeploymentStatusResponse:
    """Everything the panel needs on load: version check + updater run state."""
    check = await _version_check(service)
    state = service.updater_state()

    return DeploymentStatusResponse(
        **check,
        stage=state.get("stage", "idle"),
        action=state.get("action"),
        requested_version=state.get("requested_version"),
        target_version=state.get("target_version"),
        previous_version=service.previous_version(),
        started_at=state.get("started_at"),
        updated_at=state.get("updated_at"),
        finished_at=state.get("finished_at"),
        error_code=state.get("error_code"),
        error_message=state.get("error_message"),
        is_busy=service.is_busy(),
        record_diverged=service.record_diverged(),
        log_tail=service.log_tail(),
    )


@router.post("/check")
async def check_for_update(service: DeploymentServiceDep) -> VersionCheckResponse:
    """Cheap, cached (5 min) GitHub lookup — never touches the updater."""
    return VersionCheckResponse(**await _version_check(service))


@router.post("/update", status_code=status.HTTP_202_ACCEPTED)
async def request_update(
    body: UpdateRequestBody,
    service: DeploymentServiceDep,
) -> WriteRequestResponse:
    """Queue an update. The updater sidecar polls and performs it."""
    if service.is_busy():
        raise DeploymentInProgressError(service.updater_state().get("stage", "unknown"))
    if body.version == service.current_version():
        raise DeploymentAlreadyCurrentError(body.version)

    request_id = service.write_request("update", body.version)
    return WriteRequestResponse(request_id=request_id)


@router.post("/rollback", status_code=status.HTTP_202_ACCEPTED)
async def request_rollback(service: DeploymentServiceDep) -> WriteRequestResponse:
    """Queue a rollback to the updater's own recorded previous version.

    The target is never taken from the client — that would just be an image
    selector by another name.
    """
    if service.is_busy():
        raise DeploymentInProgressError(service.updater_state().get("stage", "unknown"))

    previous = service.previous_version()
    if not previous:
        raise DeploymentNoPreviousVersionError

    request_id = service.write_request("rollback", previous)
    return WriteRequestResponse(request_id=request_id)
