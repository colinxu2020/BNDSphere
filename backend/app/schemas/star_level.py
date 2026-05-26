from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.club import ClubStarLevelEnum
from app.models.user import AuditStatusEnum, UserGradeEnum
from app.schemas.generic import IdMixin
from app.schemas.user import UserInfo


class StarLevelApplicationBase(BaseModel):
    contest_attachment: HttpUrl | None = Field(None)
    requested_contest_score: int | None = Field(None)
    uniqueness_statement: str | None = Field(None)
    growth_story_url: HttpUrl | None = Field(None)
    target_grade_1: UserGradeEnum | None = Field(None)
    target_grade_2: UserGradeEnum | None = Field(None)


class StarLevelApplicationCreate(StarLevelApplicationBase):
    pass


class StarLevelApplicationUpdate(BaseModel):
    contest_attachment: HttpUrl | None = Field(None)
    requested_contest_score: int | None = Field(None)
    uniqueness_statement: str | None = Field(None)
    growth_story_url: HttpUrl | None = Field(None)
    target_grade_1: UserGradeEnum | None = Field(None)
    target_grade_2: UserGradeEnum | None = Field(None)


class StarLevelApplicationInfo(StarLevelApplicationBase, IdMixin):
    model_config = ConfigDict(from_attributes=True)

    club_id: int
    auditor: UserInfo | None
    audit_status: AuditStatusEnum | None
    final_contest_score: int | None
    uniqueness_approved: bool | None
    growth_story_approved: bool | None
    approved_score: int | None
    approved_level: ClubStarLevelEnum | None
