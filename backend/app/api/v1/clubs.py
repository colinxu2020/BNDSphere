from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import PERMISSION_DENIED_RESPONSE, TOKEN_INVALID_RESPONSE
from app.api.dependencies import (
    ClubMemberServiceDep,
    ClubRoleChecker,
    ClubServiceDep,
    ClubUpdateRequestServiceDep,
    get_current_user,
)
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club import (
    ClubCreate,
    ClubInfo,
    ClubMemberInfo,
    ClubUpdate,
    ClubUpdateRequestInfo,
)
from app.services.errors import (
    ClubNotFoundError,
    DuplicateClubNameError,
    DuplicateResourceError,
    ResourceForbiddenError,
    ResourceNotFoundError,
)

router = APIRouter(tags=["clubs"])


@router.get(
    "/{club_id}",
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_club_info(club_id: int, service: ClubServiceDep) -> ClubInfo:
    """Get information of a club by club id."""
    return ClubInfo.model_validate(await service.ensure_club_normal(club_id))


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE
    | {
        409: {
            "description": "Club with the same name already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Club with name HCC already exists."},
                },
            },
        },
    },
)
async def create_club(
    club: ClubCreate,
    service: ClubServiceDep,
    membership_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubInfo:
    """Create a new club. Club name must be unique among non-archived clubs."""
    try:
        club_created = await service.create(club)
    except DuplicateClubNameError:
        raise DuplicateResourceError(
            message_key="error.club.duplicate_club_name",
            error_code="DUPLICAE_CLUB_NAME",
        ) from None
    await membership_service.set_relationship(
        club_created,
        user,
        ClubMembershipEnum.president,
    )
    return ClubInfo.model_validate(club_created)


@router.patch(
    "/{club_id}",
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[Depends(ClubRoleChecker([ClubMembershipEnum.president]))],
)
async def update_club_info(
    club_id: int,
    club_update: ClubUpdate,
    service: ClubServiceDep,
    update_request_service: ClubUpdateRequestServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubUpdateRequestInfo:
    """Submit a club info update request for review.

    If a pending request already exists for this club, it will be updated
    with the new content instead of creating a new one.
    """
    club = await service.get(club_id)
    if club is None:
        raise ClubNotFoundError(club_id) from None
    request = await update_request_service.create_or_update_request(
        club,
        user,
        club_update,
    )
    return ClubUpdateRequestInfo.model_validate(request)


@router.get(
    "/{club_id}/update-requests",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[Depends(ClubRoleChecker([ClubMembershipEnum.president]))],
)
async def get_club_update_requests(
    club_id: int,
    service: ClubServiceDep,
    update_request_service: ClubUpdateRequestServiceDep,
) -> Page[ClubUpdateRequestInfo]:
    """Get all update requests for the specified club."""
    await service.ensure_club_normal(club_id)
    return Page[ClubUpdateRequestInfo].model_validate(
        await update_request_service.get_requests_by_club(club_id),
    )


@router.get(
    "/",
)
async def list_clubs(
    service: ClubServiceDep,
    search: str | None = None,
    category: ClubCategoryEnum | None = None,
) -> Page[ClubInfo]:
    """Search Clubs."""
    return Page[ClubInfo].model_validate(
        await service.get_multi(search, category, status=ClubStatusEnum.normal),
    )


@router.post(
    "/{club_id}/members",
    response_model=ClubMemberInfo,
    status_code=status.HTTP_201_CREATED,
    responses=TOKEN_INVALID_RESPONSE,
)
async def join_club(
    club_id: int,
    service: ClubServiceDep,
    membership_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubMemberInfo:
    """Join a club."""
    club = await service.ensure_club_normal(club_id)
    relationship = await membership_service.get_by_club_user(club, user)
    if relationship and relationship.membership != ClubMembershipEnum.left:
        raise DuplicateResourceError(
            message_key="error.club.duplicate_join_request",
            error_code="DUPLICAE_JOIN_REQUEST",
        ) from None
    return ClubMemberInfo.model_validate(
        await membership_service.set_relationship(
            club,
            user,
            ClubMembershipEnum.pending,
        ),
    )


@router.delete(
    "/{club_id}/members/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=TOKEN_INVALID_RESPONSE,
)
async def leave_club(
    club_id: int,
    service: ClubServiceDep,
    membership_service: ClubMemberServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Leave a club."""
    club = await service.ensure_club_normal(club_id)

    relationship = await membership_service.get_by_club_user(club, user)
    if relationship is None or relationship.membership == ClubMembershipEnum.left:
        raise ResourceNotFoundError(
            message_key="error.club.is_not_member",
            error_code="IS_NOT_MEMBER",
        ) from None
    if relationship.membership in {
        ClubMembershipEnum.vice,
        ClubMembershipEnum.president,
    }:
        raise ResourceForbiddenError(
            message_key="error.club.not_allowed_leave",
            error_code="NOT_ALLOWED_LEAVE_CLUB",
        ) from None

    await membership_service.set_relationship(
        club,
        user,
        ClubMembershipEnum.left,
    )
