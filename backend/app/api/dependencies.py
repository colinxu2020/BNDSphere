from collections.abc import AsyncGenerator
from typing import Annotated, Protocol

from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.security import verify_access_token
from app.core.settings import deployment_settings
from app.models.clubmember import ClubMembershipEnum
from app.models.user import RoleEnum, User
from app.repositories.academic_term import AcademicTermRepository
from app.repositories.announcement import AnnouncementRepository
from app.repositories.club import (
    ClubMemberRepository,
    ClubMembershipRequestRepository,
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
from app.repositories.joint_activities import JointActivityRepository
from app.repositories.star_level import StarLevelRepository
from app.repositories.star_rating import StarRatingRepository
from app.repositories.user import UserRepository, UserUpdateRequestRepository
from app.services.academic_term import AcademicTermService
from app.services.announcement import AnnouncementService
from app.services.club import (
    ClubMemberService,
    ClubMembershipRequestService,
    ClubService,
    ClubUpdateRequestService,
)
from app.services.club_activity import (
    ClubActivityCreateRequestService,
    ClubActivityService,
    ClubActivityUpdateRequestService,
)
from app.services.deployment import DeploymentService
from app.services.errors import (
    AuthenticationError,
    ClubNotFoundError,
)
from app.services.general_activities import (
    ClubGeneralActivityService,
    GeneralActivityService,
)
from app.services.joint_activities import JointActivityService
from app.services.oss import ObjectStorageService
from app.services.policies import AccessPolicy
from app.services.star_level import StarLevelService
from app.services.star_rating import StarRatingService
from app.services.user import UserService, UserUpdateRequestService

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            if session.in_transaction():
                await session.rollback()


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
type ClubMembershipRequestServiceDep = Annotated[
    ClubMembershipRequestService,
    Depends(
        ServiceFactory(
            ClubMembershipRequestService,
            ClubMembershipRequestRepository,
        ),
    ),
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
type AnnouncementServiceDep = Annotated[
    AnnouncementService,
    Depends(ServiceFactory(AnnouncementService, AnnouncementRepository)),
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
type JointActivityServiceDep = Annotated[
    JointActivityService,
    Depends(ServiceFactory(JointActivityService, JointActivityRepository)),
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


def get_deployment_service() -> DeploymentService:
    settings = deployment_settings()
    return DeploymentService(
        app_version=settings.app_version,
        github_repo=settings.github_repo,
        github_token=settings.github_token,
        status_dir=settings.status_dir,
        deploy_workflow=settings.deploy_workflow,
        deploy_ref=settings.deploy_ref,
    )


type DeploymentServiceDep = Annotated[
    DeploymentService,
    Depends(get_deployment_service),
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

    AccessPolicy.ensure_user_active(user)
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        AccessPolicy.ensure_role_allowed(user, self.allowed_roles)
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
        membership = await club_member_service.get_by_club_user(club, user)
        AccessPolicy.ensure_club_role_allowed(
            user,
            club,
            membership,
            self.allowed_roles,
        )
        return user
