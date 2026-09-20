from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Final

from app.core.constants import LOGIN_ATTEMPT_RETENTION_DAYS
from app.core.database import SessionLocal
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.user_session import UserSessionRepository

logger = logging.getLogger(__name__)

_PRUNE_INTERVAL_SECONDS: Final[float] = 24 * 60 * 60


async def prune_login_attempts() -> None:
    """Delete audit rows older than the retention window."""
    cutoff = datetime.now(UTC) - timedelta(days=LOGIN_ATTEMPT_RETENTION_DAYS)
    async with SessionLocal() as session:
        await LoginAttemptRepository(session).prune_before(cutoff)
        await session.commit()


async def prune_expired_sessions() -> None:
    """Delete sessions that are already past their expiry.

    Housekeeping only. ``UserSessionRepository.get_active_by_token_hash``
    filters on expiry itself, so an unswept row cannot authenticate in the
    meantime; this just stops the table growing without bound.
    """
    async with SessionLocal() as session:
        await UserSessionRepository(session).prune_expired(datetime.now(UTC))
        await session.commit()


async def run_retention_sweep() -> None:
    """Run every retention job. Each is independent, so one failure is logged
    and the rest still run.
    """
    for job in (prune_login_attempts, prune_expired_sessions):
        try:
            await job()
        except Exception:
            logger.exception("Retention job %s failed", job.__name__)


async def _prune_loop() -> None:
    while True:
        await asyncio.sleep(_PRUNE_INTERVAL_SECONDS)
        await run_retention_sweep()


def start_prune_task() -> asyncio.Task[None]:
    """Launch the daily retention sweep as a background task."""
    return asyncio.create_task(_prune_loop())
