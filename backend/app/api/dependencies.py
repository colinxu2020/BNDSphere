from collections.abc import AsyncGenerator
from typing import Annotated, Protocol

from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.security import verify_access_token
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.repositories.academic_term import AcademicTermRepository
from app.repositories.club import (
    ClubMemberRepository,
    ClubRepository,
    ClubUpdateRequestRepository,
)
from app.repositories.club_activity import (
    ClubActivityCreateRequestRepository,
    ClubActivityRepository,
    ClubActivityUpdateRequestRepository,
)
from app.repositories.general_activities import (
    ClubGeneralActivityRepository,
    GeneralActivityRepository,
)
from app.repositories.star_level import StarLevelRepository
from app.repositories.star_rating import StarRatingRepository
from app.repositories.user import UserRepository, UserUpdateRequestRepository
from app.services.academic_term import AcademicTermService
from app.services.club import ClubMemberService, ClubService, ClubUpdateRequestService
from app.services.club_activity import (
    ClubActivityCreateRequestService,
    ClubActivityService,
    ClubActivityUpdateRequestService,
)
from app.services.errors import (
    AuthenticationError,
    ClubNotFoundError,
    ResourceForbiddenError,
)
from app.services.general_activities import (
    ClubGeneralActivityService,
    GeneralActivityService,
)
from app.services.oss import ObjectStorageService
from app.services.star_level import StarLevelService
from app.services.star_rating import StarRatingService
from app.services.user import UserService, UserUpdateRequestService

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class RepositoryBuilder[Repository](Protocol):
    def __call__(self, db: AsyncSession) -> Repository: ...


class ServiceBuilder[Repository, Service](Protocol):
    def __call__(self, repository: Repository) -> Service: ...


class ServiceFactory[Service, Repository]:
    def __init__(
        self,
        service_type: ServiceBuilder[Repository, Service],
        repository_type: RepositoryBuilder[Repository],
    ) -> None:
        self.service_type = service_type
        self.repository_type = repository_type

    def __call__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> Service:
        return self.service_type(self.repository_type(db))


type ClubServiceDep = Annotated[
    ClubService,
    Depends(ServiceFactory(ClubService, ClubRepository)),
]
type ClubMemberServiceDep = Annotated[
    ClubMemberService,
    Depends(ServiceFactory(ClubMemberService, ClubMemberRepository)),
]
type ClubUpdateRequestServiceDep = Annotated[
    ClubUpdateRequestService,
    Depends(ServiceFactory(ClubUpdateRequestService, ClubUpdateRequestRepository)),
]
type UserServiceDep = Annotated[
    UserService,
    Depends(ServiceFactory(UserService, UserRepository)),
]
type UserUpdateRequestServiceDep = Annotated[
    UserUpdateRequestService,
    Depends(ServiceFactory(UserUpdateRequestService, UserUpdateRequestRepository)),
]
type ClubActivityServiceDep = Annotated[
    ClubActivityService,
    Depends(ServiceFactory(ClubActivityService, ClubActivityRepository)),
]
type ClubActivityCreateRequestServiceDep = Annotated[
    ClubActivityCreateRequestService,
    Depends(
        ServiceFactory(
            ClubActivityCreateRequestService,
            ClubActivityCreateRequestRepository,
        ),
    ),
]
type ClubActivityUpdateRequestServiceDep = Annotated[
    ClubActivityUpdateRequestService,
    Depends(
        ServiceFactory(
            ClubActivityUpdateRequestService,
            ClubActivityUpdateRequestRepository,
        ),
    ),
]
type AcademicTermServiceDep = Annotated[
    AcademicTermService,
    Depends(ServiceFactory(AcademicTermService, AcademicTermRepository)),
]
type GeneralActivityServiceDep = Annotated[
    GeneralActivityService,
    Depends(ServiceFactory(GeneralActivityService, GeneralActivityRepository)),
]
type ClubGeneralActivityServiceDep = Annotated[
    ClubGeneralActivityService,
    Depends(
        ServiceFactory(
            ClubGeneralActivityService,
            ClubGeneralActivityRepository,
        ),
    ),
]
type StarLevelServiceDep = Annotated[
    StarLevelService,
    Depends(ServiceFactory(StarLevelService, StarLevelRepository)),
]
type StarRatingServiceDep = Annotated[
    StarRatingService,
    Depends(ServiceFactory(StarRatingService, StarRatingRepository)),
]
type ObjectStorageServiceDep = Annotated[
    ObjectStorageService,
    Depends(ObjectStorageService),
]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_schema)],
    user_service: UserServiceDep,
) -> User:
    exc = AuthenticationError(
        "error.auth.token_invalid",
        "AUTH_TOKEN_INVALID",
    )
    try:
        payload = verify_access_token(token)
        if "sub" not in payload:
            raise exc
    except ValueError as err:
        raise exc from err

    user = await user_service.get(int(payload["sub"]))
    if user is None:
        raise exc

    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles and user.role != RoleEnum.dev:
            raise ResourceForbiddenError(
                "error.role.not_allowed",
                "ROLE_NOT_ALLOWED",
            ) from None
        return user


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
            raise ClubNotFoundError(club_id) from None
        if user.role in (RoleEnum.dev, RoleEnum.admin):
            return user
        membership = await club_member_service.get_by_club_user(club, user)
        if membership is not None and membership.membership in self.allowed_roles:
            return user
        raise ResourceForbiddenError(
            "error.club.role_not_allowed",
            "CLUB_ROLE_NOT_ALLOWED",
        ) from None
