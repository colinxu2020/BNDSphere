"""RFC 6238 time-based one-time passwords, over the standard library.

A TOTP is ten lines of HMAC; every authenticator app on a phone implements
the same RFC, so there is nothing here a dependency would do differently.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from app.core import constants

# RFC 6238's defaults, and the only combination Google Authenticator, Authy,
# 1Password and the rest read off a QR code without being told. Changing any
# of them means every app needs the parameters spelled out in the URI and
# several still ignore them, so they are fixed rather than configurable.
_ALGORITHM = "SHA1"
_PERIOD_SECONDS = 30
# 160 bits, the shared-secret size RFC 4226 specifies for HMAC-SHA1.
_SECRET_BYTES = 20
# One step either side. Back covers a user who reads the code just before it
# rolls and types it just after; forward covers a phone whose clock runs
# fast. It also triples the number of codes that open the account at any
# moment — 3 in a million — which is why the login attempt cap matters.
_DRIFT_STEPS = (-1, 0, 1)


def generate_totp_secret() -> str:
    """Mint a fresh shared secret, base32 as authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(_SECRET_BYTES)).decode().rstrip("=")


def _hotp(secret: str, counter: int) -> str:
    """One RFC 4226 code for this counter value."""
    # Base32 decoding is strict about padding; the secret is stored without it
    # because that is the form apps display and users retype.
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    # SHA-1 is not a security choice here — it is what RFC 6238 specifies and
    # what every authenticator implements. HMAC-SHA1 has no practical break,
    # and the collision attacks that retired bare SHA-1 do not apply to it.
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    digits = constants.VERIFICATION_CODE_DIGITS
    return f"{truncated % 10**digits:0{digits}d}"


def verify_totp(secret: str, submitted: str, *, at: float | None = None) -> bool:
    """Report whether ``submitted`` is a live code for ``secret``.

    ``at`` is a Unix timestamp, for tests and for nothing else.
    """
    # ``compare_digest`` raises on non-ASCII, and the submitted value comes off
    # a request. ``isdigit`` alone is not that check — it is true of fullwidth
    # and superscript digits too, which would reach the compare and raise.
    if (
        len(submitted) != constants.VERIFICATION_CODE_DIGITS
        or not submitted.isascii()
        or not submitted.isdigit()
    ):
        return False
    counter = int((time.time() if at is None else at) // _PERIOD_SECONDS)
    return any(
        secrets.compare_digest(_hotp(secret, counter + drift), submitted)
        for drift in _DRIFT_STEPS
    )


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    """Build the ``otpauth://`` URI an authenticator app scans or is pasted.

    The parameters are spelled out even though they are the defaults: a few
    apps assume 6/30/SHA1 regardless, but the ones that do not would silently
    produce codes that never match.
    """
    label = quote(f"{issuer}:{account}", safe="")
    return (
        f"otpauth://totp/{label}"
        f"?secret={secret}"
        f"&issuer={quote(issuer, safe='')}"
        f"&algorithm={_ALGORITHM}"
        f"&digits={constants.VERIFICATION_CODE_DIGITS}"
        f"&period={_PERIOD_SECONDS}"
    )
