"""Unit tests for the ALTCHA service itself (no HTTP, no database)."""

import pytest
from altcha import Payload, solve_challenge

from app.schemas.altcha import AltchaPurpose
from app.services.altcha import AltchaService
from app.services.errors import BadRequestError

_TEST_SECRET = b"test-altcha-secret"


def _solve(service: AltchaService, purpose: AltchaPurpose) -> str:
    challenge = service.create_challenge(purpose)
    solution = solve_challenge(challenge)
    assert solution is not None
    return Payload(challenge, solution).to_base64()


class TestStatelessIssuance:
    """Issuance keeps no state, so bulk issuance cannot evict anything.

    Regression guard for the review finding: the previous implementation
    stored every pending challenge in a capped map, so ~10k unauthenticated
    GETs within the TTL evicted all legitimately issued challenges and kept
    authentication unavailable. Only *consumed* signatures are tracked now.
    """

    def test_issuing_many_challenges_never_evicts_unsolved_ones(self) -> None:
        service = AltchaService(hmac_secret=_TEST_SECRET)
        payload = _solve(service, AltchaPurpose.login)

        # Well past the old pending-challenge cap; the first payload must
        # still verify because nothing was ever stored — or evicted.
        for _ in range(20_000):
            service.create_challenge(AltchaPurpose.login)

        service.verify(payload, AltchaPurpose.login)

    def test_solved_challenge_is_single_use(self) -> None:
        service = AltchaService(hmac_secret=_TEST_SECRET)
        payload = _solve(service, AltchaPurpose.login)

        service.verify(payload, AltchaPurpose.login)
        with pytest.raises(BadRequestError):
            service.verify(payload, AltchaPurpose.login)

    def test_challenges_from_other_secrets_are_rejected(self) -> None:
        issuer = AltchaService(hmac_secret=_TEST_SECRET)
        verifier = AltchaService(hmac_secret=b"different-secret")
        payload = _solve(issuer, AltchaPurpose.login)

        with pytest.raises(BadRequestError):
            verifier.verify(payload, AltchaPurpose.login)
