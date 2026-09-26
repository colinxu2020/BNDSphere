import hashlib
import hmac
import time
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from threading import Lock

from altcha import Challenge, Payload, create_challenge, verify_solution

from app.core.settings import web_settings
from app.schemas.altcha import AltchaPurpose
from app.services.errors import BadRequestError

_ALGORITHM = "PBKDF2/SHA-256"
_COST = 5_000
_CHALLENGE_TTL = timedelta(minutes=2)
_HMAC_CONTEXT = b"bndsphere:altcha-core:v2"


class AltchaService:
    """Issue and verify ALTCHA Core proof-of-work challenges.

    Challenges are self-authenticating: the HMAC signature covers the expiry
    and the purpose, so issuance keeps no server-side state. Only *consumed*
    signatures are tracked, and only until the challenge would have expired
    anyway. Flooding the unauthenticated issuance endpoint therefore cannot
    evict live challenges (there is nothing to evict), and the consumed set
    can grow no faster than clients actually solve challenges — each entry
    costs the proof-of-work plus a trip through the rate-limited login or
    registration endpoint.
    """

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
        # Consumed signature -> challenge expiry. Challenges may be solved in
        # a different order from issuance, so insertion and expiry order can
        # differ.
        self._consumed: OrderedDict[str, int] = OrderedDict()
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
        return challenge

    def verify(self, encoded_payload: str, purpose: AltchaPurpose) -> None:
        try:
            payload = Payload.from_base64(encoded_payload)
        except (KeyError, TypeError, UnicodeDecodeError, ValueError) as exc:
            raise self._verification_error() from exc

        signature = payload.challenge.signature
        challenge_purpose = (payload.challenge.parameters.data or {}).get("purpose")
        expires_at = payload.challenge.parameters.expires_at
        if (
            not isinstance(signature, str)
            or challenge_purpose != purpose.value
            or not isinstance(expires_at, int)
        ):
            raise self._verification_error()

        # Stateless check: expiry, HMAC signature, and the proof-of-work
        # itself are all validated against the signed parameters.
        result = verify_solution(payload, self._hmac_secret)
        if not result.verified:
            raise self._verification_error()

        # Consume the signature atomically: if two requests race with the
        # same payload, exactly one can pass.
        with self._lock:
            self._prune_expired(time.time())
            if signature in self._consumed:
                raise self._verification_error()
            self._consumed[signature] = expires_at

    def _prune_expired(self, now: float) -> None:
        for signature, expires_at in list(self._consumed.items()):
            if expires_at < now:
                del self._consumed[signature]

    @staticmethod
    def _verification_error() -> BadRequestError:
        return BadRequestError(
            "error.altcha.verification_failed",
            "ALTCHA_VERIFICATION_FAILED",
        )
