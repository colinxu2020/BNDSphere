from pydantic import BaseModel, Field

from app.schemas.verifications.verification_common import VerificationInfoBase


class ClubMembershipRequestBase(BaseModel):
    # Required field: clients must always send it, but an empty string is
    # accepted (an applicant may apply without writing anything).
    message: str = Field(...)


class ClubMembershipRequestInfo(VerificationInfoBase, ClubMembershipRequestBase):
    club_id: int = Field(...)


class ClubMembershipRequestCreatePublic(ClubMembershipRequestBase):
    pass


class ClubMembershipRequestCreate(ClubMembershipRequestCreatePublic):
    club_id: int = Field(...)
    applicant_id: int = Field(...)
