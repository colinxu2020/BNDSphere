from pydantic import BaseModel, ConfigDict, Field

from app.core import constants
from app.schemas.generic import IdMixin
from app.schemas.verifications.verification_common import VerificationInfoBase


class ClubClaimRequestBase(BaseModel):
    message: str = Field(..., max_length=constants.CLUB_CLAIM_MAX_MESSAGE_LENGTH)


class ClubClaimRequestCreatePublic(ClubClaimRequestBase):
    message: str = Field(default="", max_length=constants.CLUB_CLAIM_MAX_MESSAGE_LENGTH)


class ClubClaimRequestCreate(ClubClaimRequestCreatePublic):
    club_id: int
    applicant_id: int


class ClubClaimRequestInfo(VerificationInfoBase, ClubClaimRequestBase):
    club_id: int


class ClubClaimClubInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class ClubClaimApplicantInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str


class ClubClaimRequestReviewInfo(ClubClaimRequestInfo):
    club: ClubClaimClubInfo
    applicant: ClubClaimApplicantInfo
