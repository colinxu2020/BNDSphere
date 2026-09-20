from collections.abc import Awaitable, Callable, Sequence
from math import ceil

from fastapi import Request

from app.core.constants import (
    AUTH_GLOBAL_MAX_PER_MINUTE,
    CHALLENGE_IP_MAX_PER_HOUR,
    CHALLENGE_IP_MAX_PER_MINUTE,
    LOGIN_IP_MAX_PER_HOUR,
    LOGIN_IP_MAX_PER_MINUTE,
    PASSWORD_RESET_IP_MAX_PER_DAY,
    PASSWORD_RESET_IP_MAX_PER_HOUR,
    REGISTER_IP_MAX_PER_DAY,
    REGISTER_IP_MAX_PER_HOUR,
)
from app.core.rate_limit import InMemoryRateLimiter, RateLimitRule
from app.core.settings import web_settings
from app.services.errors import RateLimitError

auth_rate_limiter = InMemoryRateLimiter()

_GLOBAL_RULES: Sequence[RateLimitRule] = (
    RateLimitRule(AUTH_GLOBAL_MAX_PER_MINUTE, 60),
)
_LOGIN_RULES: Sequence[RateLimitRule] = (
    RateLimitRule(LOGIN_IP_MAX_PER_MINUTE, 60),
    RateLimitRule(LOGIN_IP_MAX_PER_HOUR, 3600),
)
_REGISTER_RULES: Sequence[RateLimitRule] = (
    RateLimitRule(REGISTER_IP_MAX_PER_HOUR, 3600),
    RateLimitRule(REGISTER_IP_MAX_PER_DAY, 86400),
)
_PASSWORD_RESET_RULES: Sequence[RateLimitRule] = (
    RateLimitRule(PASSWORD_RESET_IP_MAX_PER_HOUR, 3600),
    RateLimitRule(PASSWORD_RESET_IP_MAX_PER_DAY, 86400),
)
_CHALLENGE_RULES: Sequence[RateLimitRule] = (
    RateLimitRule(CHALLENGE_IP_MAX_PER_MINUTE, 60),
    RateLimitRule(CHALLENGE_IP_MAX_PER_HOUR, 3600),
)


def client_ip(request: Request) -> str:
    """Resolve the client IP from the proxy-set header, never from XFF.

    Caddy overwrites ``X-Real-IP`` with the peer address (see infra/Caddyfile),
    so a client-supplied value cannot survive. ``X-Forwarded-For`` is not
    consulted because Caddy *appends* to it rather than replacing it.
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def ip_rate_limit_enabled() -> bool:
    """Whether the per-IP budgets run (``AUTH_IP_RATE_LIMIT_ENABLED``).

    Read per request through the cached settings so the switch is a deploy-time
    env change rather than something baked into the module at import.
    """
    return web_settings().auth_ip_rate_limit_enabled


def rate_limit(
    scope: str,
    rules: Sequence[RateLimitRule],
) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        # The process-wide breaker is unconditional; only the per-IP budget is
        # switchable, so disabling it leaves the shared circuit breaker in
        # place rather than turning the endpoint wide open.
        entries: list[tuple[str, Sequence[RateLimitRule]]] = [
            ("auth:global", _GLOBAL_RULES),
        ]
        if ip_rate_limit_enabled():
            entries.append((f"{scope}:{client_ip(request)}", rules))
        retry_after = await auth_rate_limiter.hit(entries)
        if retry_after is not None:
            raise RateLimitError(retry_after=max(1, ceil(retry_after)))

    return dependency


login_rate_limit = rate_limit("auth:login", _LOGIN_RULES)
register_rate_limit = rate_limit("auth:register", _REGISTER_RULES)
challenge_rate_limit = rate_limit("auth:challenge", _CHALLENGE_RULES)
password_reset_rate_limit = rate_limit(
    "auth:password_reset",
    _PASSWORD_RESET_RULES,
)
