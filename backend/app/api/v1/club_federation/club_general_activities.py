from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import ClubGeneralActivityServiceDep, get_current_user
from app.models.user import User
from app.schemas.general_activities import ClubGeneralActivityInfo, ScfRecordUpdate

router = APIRouter(tags=["Club General Activities"])


@router.patch("/{record_id}")
async def update_record(
    record_id: int,
    obj_in: ScfRecordUpdate,
    club_general_activities_service: ClubGeneralActivityServiceDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ClubGeneralActivityInfo:
    return await club_general_activities_service.review_record(record_id, obj_in, user)
