from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from app.api.common_responses import (
    PERMISSION_DENIED_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    TOKEN_INVALID_RESPONSE,
)
from app.api.dependencies import (
    ClubRoleChecker,
    ClubServiceDep,
    get_current_user,
)
from app.models.club import ClubCategoryEnum, ClubStatusEnum
from app.models.clubmember import ClubMembershipEnum
from app.models.user import User
from app.schemas.club import (
    ClubCreate,
    ClubInfo,
    ClubSummaryInfo,
    ClubMemberInfo,
)
from app.schemas.moderations.club import (
    ClubUpdateRequestCreatePublic,
    ClubUpdateRequestInfo,
)
from app.services.errors import (
    DuplicateClubNameError,
    DuplicateResourceError,
)

router = APIRouter(tags=["Clubs"])


@router.get(
    "/summary",
)
async def list_clubs_summary(
    service: ClubServiceDep,
    search: str | None = None,
    category: ClubCategoryEnum | None = None,
) -> Page[ClubSummaryInfo]:
    """Search clubs, card/list representation.

    Same filters and ordering as GET /clubs/, but returns member_count instead of
    the nested members, club_activities and general_activity_records collections —
    a browse grid needs the count, not the collections.

    Declared before /{club_id} on purpose: that route takes an int, so a request
    for /clubs/summary would otherwise be rejected as an invalid id rather than
    reaching this handler.
    """
    return await service.get_multi_summary(
        search,
        category,
        status=ClubStatusEnum.normal,
    )


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
    user: Annotated[User, Depends(get_current_user)],
) -> ClubInfo:
    """Create a new club. Club name must be unique among non-archived clubs."""
    try:
        club_created = await service.create_club(club, user)
    except DuplicateClubNameError:
        raise DuplicateResourceError(
            message_key="error.club.duplicate_club_name",
            error_code="DUPLICATE_CLUB_NAME",
        ) from None
    return ClubInfo.model_validate(club_created)


@router.post(
    "/{club_id}/update-requests",
    responses=TOKEN_INVALID_RESPONSE | PERMISSION_DENIED_RESPONSE,
    dependencies=[
        Depends(
            ClubRoleChecker(
                [ClubMembershipEnum.president, ClubMembershipEnum.vice_president],
            ),
        ),
    ],
)
async def update_request(
    club_id: int,
    obj_in: ClubUpdateRequestCreatePublic,
    service: ClubServiceDep,
    requestor: Annotated[User, Depends(get_current_user)],
) -> ClubUpdateRequestInfo:
    return ClubUpdateRequestInfo.model_validate(
        await service.request_club_update(club_id, obj_in, requestor),
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
    user: Annotated[User, Depends(get_current_user)],
) -> ClubMemberInfo:
    """Join a club."""
    return ClubMemberInfo.model_validate(await service.join_club(club_id, user))


@router.delete(
    "/{club_id}/members/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=TOKEN_INVALID_RESPONSE | RESOURCE_NOT_FOUND_RESPONSE,
)
async def leave_club(
    club_id: int,
    service: ClubServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Leave a club."""
    await service.leave_club(club_id, user)
