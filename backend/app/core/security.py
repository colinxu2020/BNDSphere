from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
import jwt

from .settings import settings


pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode(data | {'exp': expire}, settings.secret_key, algorithm='HS256')

def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.InvalidTokenError:
        raise ValueError('Invalid token')
