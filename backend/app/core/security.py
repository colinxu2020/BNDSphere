from datetime import UTC, datetime, timedelta
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


def create_access_token(data: dict[str, Any]) -> str:
    expire = datetime.now(UTC) + timedelta(days=7)
    return jwt.encode(data | {"exp": expire}, settings.secret_key, algorithm="HS256")


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as err:
        raise ValueError("Token has expired") from err
    except jwt.InvalidTokenError as err:
        raise ValueError("Invalid token") from err


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
