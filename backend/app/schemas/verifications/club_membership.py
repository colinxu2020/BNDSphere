from pydantic import BaseModel, Field

from app.schemas.verifications.verification_common import VerificationInfoBase


class ClubMembershipRequestBase(BaseModel):
    message: str | None = Field(None)


class ClubMembershipRequestInfo(VerificationInfoBase, ClubMembershipRequestBase):
    club_id: int = Field(...)


class ClubMembershipRequestCreatePublic(ClubMembershipRequestBase):
    pass


class ClubMembershipRequestCreate(ClubMembershipRequestCreatePublic):
    club_id: int = Field(...)
    applicant_id: int = Field(...)
