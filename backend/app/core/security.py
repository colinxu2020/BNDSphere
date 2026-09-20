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
