from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import HTTPException, status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.security import verify_access_token
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.services.academic_term import AcademicTermService
from app.services.activity import ActivityService
from app.services.base import ServiceBase
from app.services.club import ClubMemberService, ClubService
from app.services.user import UserService

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    token: Annotated[str, Depends(oauth2_schema)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token is invalid or expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_access_token(token)
        if "sub" not in payload:
            raise exc
    except ValueError as err:
        raise exc from err

    user = await db.get(User, int(payload["sub"]))
    if user is None:
        raise exc

    # noinspection PyTypeChecker
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles and user.role != RoleEnum.dev:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return user


class ServiceFactory[Service: ServiceBase]:
    def __init__(self, typ: type[Service]) -> None:
        self.typ = typ

    def __call__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> Service:
        return self.typ(db)


type ClubServiceDep = Annotated[ClubService, Depends(ServiceFactory(ClubService))]
type ClubMemberServiceDep = Annotated[
    ClubMemberService,
    Depends(ServiceFactory(ClubMemberService)),
]
type UserServiceDep = Annotated[UserService, Depends(ServiceFactory(UserService))]
type ActivityServiceDep = Annotated[
    ActivityService,
    Depends(ServiceFactory(ActivityService)),
]
type AcademicTermServiceDep = Annotated[
    AcademicTermService,
    Depends(ServiceFactory(AcademicTermService)),
]


class ClubRoleChecker:
    def __init__(self, allowed_roles: list[ClubMembershipEnum]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        club_id: int,
        club_service: ClubServiceDep,
        club_member_service: ClubMemberServiceDep,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        club = await club_service.get(club_id)
        if club is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found",
            )
        if user.role in (RoleEnum.dev, RoleEnum.admin):
            return user
        membership = await club_member_service.get_by_club_user(club, user)
        if membership is not None and membership.membership in self.allowed_roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
