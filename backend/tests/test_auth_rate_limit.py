import asyncio
from typing import ClassVar

import pytest
from httpx import AsyncClient
from sqlalchemy import BigInteger, cast, func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.core import rate_limit as rate_limit_module
from app.core.constants import (
    LOGIN_IP_MAX_PER_MINUTE,
    LOGIN_LOCKOUT_THRESHOLD,
    REGISTER_IP_MAX_PER_HOUR,
)
from app.core.rate_limit import InMemoryRateLimiter, RateLimitRule
from app.models import LoginAttempt
from app.repositories.login_attempt import LoginAttemptRepository, _advisory_key


async def _try_advisory_lock(conn: AsyncConnection, username: str) -> bool:
    result = await conn.execute(
        select(
            func.pg_try_advisory_xact_lock(cast(_advisory_key(username), BigInteger)),
        ),
    )
    return bool(result.scalar_one())


class TestInMemoryRateLimiter:
    """Unit coverage for the sliding-window limiter itself."""

    async def test_allows_up_to_limit_then_blocks(self) -> None:
        limiter = InMemoryRateLimiter()
        rules = [RateLimitRule(limit=2, window_seconds=60)]

        assert await limiter.hit([("k", rules)]) is None
        assert await limiter.hit([("k", rules)]) is None
        retry_after = await limiter.hit([("k", rules)])
        assert retry_after is not None
        assert 0 < retry_after <= 60

    async def test_blocked_hit_is_not_recorded(self) -> None:
        limiter = InMemoryRateLimiter()
        rules = [RateLimitRule(limit=1, window_seconds=60)]

        assert await limiter.hit([("k", rules)]) is None
        assert await limiter.hit([("k", rules)]) is not None
        assert await limiter.hit([("k", rules)]) is not None
        # A rejected hit must not count, or a blocked caller would keep
        # extending its own lockout by hammering the endpoint.
        assert len(limiter._buckets["k"].hits) == 1  # noqa: SLF001

    async def test_keys_are_independent(self) -> None:
        limiter = InMemoryRateLimiter()
        rules = [RateLimitRule(limit=1, window_seconds=60)]

        assert await limiter.hit([("a", rules)]) is None
        assert await limiter.hit([("b", rules)]) is None
        assert await limiter.hit([("a", rules)]) is not None

    async def test_hits_age_out_of_the_window(self) -> None:
        limiter = InMemoryRateLimiter()
        rules = [RateLimitRule(limit=1, window_seconds=0.05)]

        assert await limiter.hit([("k", rules)]) is None
        assert await limiter.hit([("k", rules)]) is not None
        await asyncio.sleep(0.1)
        assert await limiter.hit([("k", rules)]) is None

    def test_clear_resets_state(self) -> None:
        limiter = InMemoryRateLimiter()
        limiter.clear()
        assert limiter._buckets == {}  # noqa: SLF001 -- white-box reset check

    async def test_eviction_sheds_only_the_coldest(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(rate_limit_module, "_MAX_TRACKED_KEYS", 2)
        limiter = InMemoryRateLimiter()
        rules = [RateLimitRule(limit=5, window_seconds=60)]

        await limiter.hit([("hot", rules)])
        await limiter.hit([("cold", rules)])
        await limiter.hit([("hot", rules)])
        # Over the cap: the least recently used key goes, not the whole map.
        await limiter.hit([("new", rules)])

        assert set(limiter._buckets) == {"hot", "new"}  # noqa: SLF001


class TestUsernameAdvisoryLock:
    """A per-username advisory lock serializes check-and-record."""

    async def test_same_username_excludes_other_sessions(
        self,
        db_engine: AsyncEngine,
    ) -> None:
        async with db_engine.connect() as holder, db_engine.connect() as other:
            await holder.execute(
                select(
                    func.pg_advisory_xact_lock(
                        cast(_advisory_key("race_user"), BigInteger),
                    ),
                ),
            )
            # The holder's key is exclusive, but unrelated usernames are free.
            assert await _try_advisory_lock(other, "race_user") is False
            assert await _try_advisory_lock(other, "unrelated_user") is True

    async def test_login_takes_the_username_lock(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        locked: list[str] = []
        original = LoginAttemptRepository.lock_username

        async def spy(repository: LoginAttemptRepository, username: str) -> None:
            locked.append(username)
            await original(repository, username)

        monkeypatch.setattr(LoginAttemptRepository, "lock_username", spy)

        resp = await client.post(
            "/auth/login",
            data={"username": "lock_spy_user", "password": "whatever"},
        )
        assert resp.status_code == 401
        assert locked == ["lock_spy_user"]


class TestLoginThrottle:
    """Failed logins accumulate per account and lock the account out."""

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "throttle_user", "password": "correct-horse-battery"},
    ]

    async def test_lockout_after_threshold(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        setup_class_users: None,
    ) -> None:
        for _ in range(LOGIN_LOCKOUT_THRESHOLD):
            resp = await client.post(
                "/auth/login",
                data={"username": "throttle_user", "password": "wrong-password"},
            )
            assert resp.status_code == 401

        # Even the correct password is rejected while throttled.
        blocked = await client.post(
            "/auth/login",
            data={
                "username": "throttle_user",
                "password": "correct-horse-battery",
            },
        )
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "LOGIN_THROTTLED"
        assert int(blocked.headers["Retry-After"]) >= 1

        # Every failure is audited with the source IP; the blocked attempt is
        # not recorded.
        rows = (
            (
                await db_session.execute(
                    select(LoginAttempt).where(
                        LoginAttempt.username == "throttle_user",
                    ),
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == LOGIN_LOCKOUT_THRESHOLD
        assert all(not row.successful for row in rows)
        assert all(row.ip is not None for row in rows)


class TestLoginThrottleReset:
    """A successful login clears the accumulated failures."""

    USER_SPECS: ClassVar[list[dict[str, str]]] = [
        {"username": "reset_user", "password": "correct-horse-battery"},
    ]

    async def test_success_resets_failure_count(
        self,
        client: AsyncClient,
        setup_class_users: None,
    ) -> None:
        for _ in range(3):
            resp = await client.post(
                "/auth/login",
                data={"username": "reset_user", "password": "wrong-password"},
            )
            assert resp.status_code == 401

        ok = await client.post(
            "/auth/login",
            data={"username": "reset_user", "password": "correct-horse-battery"},
        )
        assert ok.status_code == 200

        # One below the lockout threshold; without the reset this would have
        # tripped on the 11th total failure instead.
        for _ in range(LOGIN_LOCKOUT_THRESHOLD - 1):
            resp = await client.post(
                "/auth/login",
                data={"username": "reset_user", "password": "wrong-password"},
            )
            assert resp.status_code == 401


class TestRegisterIpRateLimit:
    """The per-IP budget rejects a burst before any user is created."""

    async def test_register_burst_is_rate_limited(
        self,
        client: AsyncClient,
    ) -> None:
        # A short password is rejected with 422, but the rate-limit dependency
        # runs first, so each request still consumes the IP budget.
        payload = {"username": "ip_limit_user", "password": "12345"}
        for _ in range(REGISTER_IP_MAX_PER_HOUR):
            resp = await client.post("/auth/register", json=payload)
            assert resp.status_code == 422

        blocked = await client.post("/auth/register", json=payload)
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "RATE_LIMITED"
        assert int(blocked.headers["Retry-After"]) >= 1


class TestLoginIpRateLimit:
    """The login endpoint also enforces a per-IP request budget."""

    async def test_login_burst_is_rate_limited(
        self,
        client: AsyncClient,
    ) -> None:
        # Distinct usernames so the per-account throttle never fires; the
        # per-IP limiter is what must stop the burst.
        for index in range(LOGIN_IP_MAX_PER_MINUTE):
            resp = await client.post(
                "/auth/login",
                data={"username": f"ghost_{index}", "password": "whatever"},
            )
            assert resp.status_code == 401

        blocked = await client.post(
            "/auth/login",
            data={"username": "ghost_final", "password": "whatever"},
        )
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "RATE_LIMITED"
        assert int(blocked.headers["Retry-After"]) >= 1
