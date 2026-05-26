from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.common_responses import RESOURCE_NOT_FOUND_RESPONSE
from app.api.dependencies import ClubGeneralActivityServiceDep, get_current_user
from app.models.user import User
from app.schemas.general_activities import (
    ClubGeneralActivityInfo,
    FederationRecordUpdate,
)
from app.services.errors import ResourceNotFoundError

router = APIRouter(tags=["Club General Activities"])


@router.patch(
    "/{record_id}",
    responses=RESOURCE_NOT_FOUND_RESPONSE,
)
async def update_record(
    record_id: int,
    obj_in: FederationRecordUpdate,
    club_general_activities_service: ClubGeneralActivityServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubGeneralActivityInfo:
    record = await club_general_activities_service.get(record_id)
    if record is None:
        raise ResourceNotFoundError(
            "error.club_general_activity_record.not_found",
            "CLUB_GENERAL_ACTIVITY_RECORD_NOT_FOUND",
        ) from None

    return ClubGeneralActivityInfo.model_validate(
        await club_general_activities_service.review_record(record_id, obj_in, user),
    )
