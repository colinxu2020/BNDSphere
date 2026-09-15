from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from time import monotonic
from typing import Final

# Above this many tracked keys (one per scope+IP), evict the coldest buckets.
# Only reachable under a distributed source-IP flood; keeps memory bounded.
_MAX_TRACKED_KEYS: Final[int] = 100_000


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    limit: int
    window_seconds: float


@dataclass(slots=True)
class _Bucket:
    window_seconds: float
    hits: deque[float] = field(default_factory=deque)


class InMemoryRateLimiter:
    """Sliding-window limiter scoped to one process.

    Deliberately process-local: the deployment runs a single backend process
    (see AGENTS.md), and the durable, cross-restart defence is the per-account
    throttle persisted in Postgres. This layer only blunts bulk scanning from
    a single source, so losing its state on restart is acceptable.
    """

    def __init__(self) -> None:
        # Ordered least- to most-recently-used so the cap can evict the
        # coldest buckets without discarding the active ones.
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()
        self._lock = asyncio.Lock()

    async def hit(
        self,
        entries: Sequence[tuple[str, Sequence[RateLimitRule]]],
    ) -> float | None:
        """Record one request against every key and report a retry delay.

        Returns ``None`` when all rules pass. When any rule is already
        exhausted, returns the longest number of seconds until the oldest
        relevant hit ages out and records nothing, so a blocked caller cannot
        extend its own lockout.
        """
        now = monotonic()
        async with self._lock:
            retry_after = self._evaluate(entries, now)
            if retry_after is not None:
                return retry_after
            for key, rules in entries:
                window = max(rule.window_seconds for rule in rules)
                self._record(key, window, now)
            self._evict_if_needed()
            return None

    def clear(self) -> None:
        self._buckets.clear()

    def _evaluate(
        self,
        entries: Sequence[tuple[str, Sequence[RateLimitRule]]],
        now: float,
    ) -> float | None:
        worst: float | None = None
        for key, rules in entries:
            bucket = self._buckets.get(key)
            if bucket is None:
                continue
            for rule in rules:
                cutoff = now - rule.window_seconds
                in_window = [hit for hit in bucket.hits if hit > cutoff]
                if len(in_window) < rule.limit:
                    continue
                wait = rule.window_seconds - (now - in_window[0])
                worst = wait if worst is None else max(worst, wait)
        return worst

    def _record(self, key: str, window: float, now: float) -> None:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(window_seconds=window)
            self._buckets[key] = bucket
        bucket.window_seconds = window
        bucket.hits.append(now)
        cutoff = now - window
        while bucket.hits and bucket.hits[0] <= cutoff:
            bucket.hits.popleft()
        self._buckets.move_to_end(key)

    def _evict_if_needed(self) -> None:
        """Trim the coldest buckets once the tracked-key cap is exceeded.

        Never clears the whole mapping: the shared global bucket and active
        clients are the most recently used and survive, so a flood of fresh
        source keys cannot reset everyone's budget to a clean slate.
        """
        while len(self._buckets) > _MAX_TRACKED_KEYS:
            self._buckets.popitem(last=False)
