from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generic import IdMixin
from app.schemas.verifications.verification_common import VerificationInfoBase


class ClubClaimRequestBase(BaseModel):
    message: str = Field(..., max_length=1000)


class ClubClaimRequestCreatePublic(ClubClaimRequestBase):
    message: str = Field(default="", max_length=1000)


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
