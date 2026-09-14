from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Final

from app.core.constants import LOGIN_ATTEMPT_RETENTION_DAYS
from app.core.database import SessionLocal
from app.repositories.login_attempt import LoginAttemptRepository

logger = logging.getLogger(__name__)

_PRUNE_INTERVAL_SECONDS: Final[float] = 24 * 60 * 60


async def prune_login_attempts() -> None:
    """Delete audit rows older than the retention window."""
    cutoff = datetime.now(UTC) - timedelta(days=LOGIN_ATTEMPT_RETENTION_DAYS)
    async with SessionLocal() as session:
        await LoginAttemptRepository(session).prune_before(cutoff)
        await session.commit()


async def _prune_loop() -> None:
    while True:
        await asyncio.sleep(_PRUNE_INTERVAL_SECONDS)
        try:
            await prune_login_attempts()
        except Exception:
            logger.exception("Pruning login attempts failed")


def start_prune_task() -> asyncio.Task[None]:
    """Launch the daily retention sweep as a background task."""
    return asyncio.create_task(_prune_loop())
