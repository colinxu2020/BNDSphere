from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from .settings import settings

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
