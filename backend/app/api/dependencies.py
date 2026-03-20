from typing import Annotated, AsyncGenerator

from fastapi import HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, verify_access_token
from app.models.user import User, RoleEnum

oauth2_schema = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession() as session:
        yield session

async def get_current_user(
        token: Annotated[str, Depends(oauth2_schema)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Password or username incorrent.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_access_token(token)
        if 'sub' not in payload:
            raise exc
    except ValueError:
        raise exc

    user = await db.get(User, int(payload['sub']))
    if user is None:
        raise exc

    return user

class RoleChecker():
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles and user.role != RoleEnum.dev:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')
        return user


