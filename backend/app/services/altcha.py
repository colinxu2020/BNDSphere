import hashlib
import hmac
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock

from altcha import Challenge, Payload, create_challenge, verify_solution

from app.core.settings import web_settings
from app.schemas.altcha import AltchaPurpose
from app.services.errors import BadRequestError

_ALGORITHM = "PBKDF2/SHA-256"
_COST = 5_000
_CHALLENGE_TTL = timedelta(minutes=2)
_MAX_PENDING_CHALLENGES = 10_000
_HMAC_CONTEXT = b"bndsphere:altcha-core:v2"


@dataclass(frozen=True)
class _PendingChallenge:
    expires_at: int
    purpose: AltchaPurpose


class AltchaService:
    def __init__(
        self,
        *,
        hmac_secret: bytes | None = None,
        cost: int = _COST,
    ) -> None:
        if hmac_secret is None:
            root_secret = web_settings().secret_key.encode()
            hmac_secret = hmac.digest(
                root_secret,
                _HMAC_CONTEXT,
                hashlib.sha256,
            )
        self._hmac_secret = hmac_secret
        self._cost = cost
        self._pending: OrderedDict[str, _PendingChallenge] = OrderedDict()
        self._lock = Lock()

    def create_challenge(self, purpose: AltchaPurpose) -> Challenge:
        expires_at = datetime.now(tz=UTC) + _CHALLENGE_TTL
        challenge = create_challenge(
            _ALGORITHM,
            self._cost,
            expires_at=expires_at,
            data={"purpose": purpose.value},
            hmac_secret=self._hmac_secret,
        )
        if challenge.signature is None or challenge.parameters.expires_at is None:
            raise RuntimeError("ALTCHA created an unsigned or non-expiring challenge")

        pending = _PendingChallenge(challenge.parameters.expires_at, purpose)
        with self._lock:
            self._prune_expired(time.time())
            while len(self._pending) >= _MAX_PENDING_CHALLENGES:
                self._pending.popitem(last=False)
            self._pending[challenge.signature] = pending
        return challenge

    def verify(self, encoded_payload: str, purpose: AltchaPurpose) -> None:
        try:
            payload = Payload.from_base64(encoded_payload)
        except (KeyError, TypeError, UnicodeDecodeError, ValueError) as exc:
            raise self._verification_error() from exc

        signature = payload.challenge.signature
        challenge_purpose = (payload.challenge.parameters.data or {}).get("purpose")
        if not isinstance(signature, str) or challenge_purpose != purpose.value:
            raise self._verification_error()

        with self._lock:
            self._prune_expired(time.time())
            pending = self._pending.get(signature)
        if pending is None or pending.purpose != purpose:
            raise self._verification_error()

        result = verify_solution(payload, self._hmac_secret)
        if not result.verified:
            raise self._verification_error()

        # A solved challenge is consumed atomically. If two requests race with
        # the same payload, exactly one can pass.
        with self._lock:
            if self._pending.pop(signature, None) != pending:
                raise self._verification_error()

    def _prune_expired(self, now: float) -> None:
        while self._pending:
            _signature, pending = next(iter(self._pending.items()))
            if pending.expires_at >= now:
                break
            self._pending.popitem(last=False)

    @staticmethod
    def _verification_error() -> BadRequestError:
        return BadRequestError(
            "error.altcha.verification_failed",
            "ALTCHA_VERIFICATION_FAILED",
        )
