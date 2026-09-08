from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.club_activity_check_in import CheckInMethodEnum
from app.schemas.generic import IdMixin


class ClubActivityCheckInInfo(IdMixin):
    model_config = ConfigDict(from_attributes=True)

    club_activity_id: int
    user_id: int
    method: CheckInMethodEnum
    checked_in_at: datetime
    recorded_by_user_id: int


class ClubActivityCheckInCreate(BaseModel):
    """Internal create schema — fields are computed server-side, never taken
    directly from the client request.
    """

    club_activity_id: int
    user_id: int
    method: CheckInMethodEnum
    recorded_by_user_id: int


class ClubActivityManualCheckInRequest(BaseModel):
    """Request body for the president/vice-president manually recording the
    roster of members who attended.
    """

    user_ids: list[int] = Field(..., min_length=1)


class ClubActivityCheckInQrTokenInfo(BaseModel):
    token: str
    expires_at: datetime


class ClubActivityQrCheckInRequest(BaseModel):
    token: str
