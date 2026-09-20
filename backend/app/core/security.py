import hashlib
import secrets
from datetime import datetime
from typing import Any

import jwt
from passlib.context import CryptContext

from .settings import web_settings

settings = web_settings()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_session_token() -> str:
    """Mint the opaque token a client presents to prove it holds a session."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hash a session token for storage.

    Plain SHA-256 rather than a password KDF: the token is 256 bits of CSPRNG
    output, so there is no low-entropy guess to slow down, and this runs on
    every authenticated request. Hashing at all is what stops a dump of
    ``user_sessions`` from being replayed as a set of live logins.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def hash_verification_code(code: str) -> str:
    """Hash a one-time verification code for storage.

    Same SHA-256 as ``hash_session_token`` but a different bargain: a
    six-digit code is only ~20 bits, so anyone holding the table can recover
    it by exhaustion in microseconds. This is not the defence — the minutes-
    long expiry and the attempt cap are. Hashing is here so a leaked backup
    or a log line does not hand over codes that are still live, and it is
    kept as a separate function from the session one so neither docstring has
    to claim a guarantee the other's callers do not get.
    """
    return hashlib.sha256(code.encode()).hexdigest()


_CHECK_IN_TOKEN_TYPE = "club_activity_check_in"  # noqa: S105 -- not a password


def create_check_in_token(activity_id: int, expires_at: datetime) -> str:
    """Sign a short-lived token scoped to one club activity's check-in QR code.

    Carries no user identity (meant to be displayed/scanned by anyone),
    expires with the activity rather than after a fixed duration, and is
    tagged with a ``typ`` claim so it can't be replayed as a login access
    token.
    """
    payload = {
        "typ": _CHECK_IN_TOKEN_TYPE,
        "activity_id": activity_id,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_check_in_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as err:
        raise ValueError("Token has expired") from err
    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid token") from err
    if payload.get("typ") != _CHECK_IN_TOKEN_TYPE:
        raise ValueError("Invalid token type")
    return payload


def generate_recovery_code() -> str:
    """One recovery code: 64 bits of CSPRNG, grouped so it can be read aloud."""
    raw = secrets.token_hex(8)
    return "-".join(raw[i : i + 4] for i in range(0, len(raw), 4))


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code for storage, normalizing how it was typed.

    Grouping hyphens, case and surrounding space are presentation, so they are
    stripped on both sides of the comparison — someone reading a code off a
    printout should not fail because they left the dashes out.

    SHA-256 rather than a password KDF, for the same reason as
    ``hash_session_token``: 64 bits of CSPRNG has no low-entropy guess to slow
    down, and the hash exists so a dumped table is not a list of live codes.
    """
    normalized = "".join(char for char in code.lower() if char.isalnum())
    return hashlib.sha256(normalized.encode()).hexdigest()


_TWO_FACTOR_TOKEN_TYPE = "two_factor"  # noqa: S105 -- a claim value, not a password


def create_two_factor_token(user_id: int, expires_at: datetime) -> str:
    """Sign the short-lived ticket that stands between a password and a session.

    Stateless on purpose: its bearer has already proved they know the password,
    so replaying it within its few minutes buys nothing a second login would
    not. It only names *whose* second factor is being answered.

    ponytail: not revocable, so a password change does not invalidate a
    challenge already in flight. Making it revocable means a row per
    challenge; the short expiry is what bounds it until that is worth it.
    """
    payload = {
        "typ": _TWO_FACTOR_TOKEN_TYPE,
        "sub": str(user_id),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_two_factor_token(token: str) -> int:
    """Return the user id the challenge names, or raise ``ValueError``."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid token") from err
    # Without this a check-in token — signed with the same key — would be
    # accepted here as a second factor for whatever user id it happened to
    # decode to.
    if payload.get("typ") != _TWO_FACTOR_TOKEN_TYPE:
        raise ValueError("Invalid token type")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("Invalid token subject") from err
