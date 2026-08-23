from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.club import ClubCategoryEnum, ClubStarLevelEnum, ClubStatusEnum
from app.models.user import AuditStatusEnum, UserGradeEnum
from app.schemas.academic_terms import AcademicTermInfo
from app.schemas.generic import IdMixin
from app.schemas.upload import ApplicationFileUri


class StarLevelApplicationBase(BaseModel):
    contest_attachment: HttpUrl | None = Field(None)
    requested_contest_score: int | None = Field(None)
    uniqueness_statement: str | None = Field(None)
    growth_story_url: HttpUrl | None = Field(None)
    target_grade_1: UserGradeEnum | None = Field(None)
    target_grade_2: UserGradeEnum | None = Field(None)


class StarLevelApplicationCreate(StarLevelApplicationBase):
    contest_attachment: ApplicationFileUri = Field(None)
    growth_story_url: ApplicationFileUri = Field(None)


class StarLevelApplicationUpdate(BaseModel):
    contest_attachment: ApplicationFileUri = Field(None)
    requested_contest_score: int | None = Field(None)
    uniqueness_statement: str | None = Field(None)
    growth_story_url: ApplicationFileUri = Field(None)
    target_grade_1: UserGradeEnum | None = Field(None)
    target_grade_2: UserGradeEnum | None = Field(None)


class StarLevelApplicationReview(BaseModel):
    audit_status: AuditStatusEnum = Field(...)
    final_contest_score: int | None = Field(None)
    uniqueness_approved: bool | None = Field(None)
    growth_story_approved: bool | None = Field(None)


class StarLevelApplicationReviewPreview(BaseModel):
    approved_score: int | None
    approved_level: ClubStarLevelEnum | None


class StarLevelApplicationInfo(StarLevelApplicationBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    club_id: int
    auditor_id: int | None
    audit_status: AuditStatusEnum | None
    final_contest_score: int | None
    uniqueness_approved: bool | None
    growth_story_approved: bool | None
    approved_score: int | None
    approved_level: ClubStarLevelEnum | None


class StarLevelClubInfo(IdMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    category: ClubCategoryEnum
    logo_uri: HttpUrl | None
    status: ClubStatusEnum
    star_level: ClubStarLevelEnum


class StarLevelApplicationPublicInfo(StarLevelApplicationBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    club_id: int
    club: StarLevelClubInfo
    academic_term: AcademicTermInfo
    audit_status: AuditStatusEnum | None
    final_contest_score: int | None
    uniqueness_approved: bool | None
    growth_story_approved: bool | None
    approved_score: int | None
    approved_level: ClubStarLevelEnum | None
    created_at: datetime
