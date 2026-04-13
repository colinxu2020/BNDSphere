from pydantic import BaseModel, Field


class StarRatingBreakdown(BaseModel):
    meeting_attendance: int = Field(
        ...,
        description="一、会议出勤 (0 或 10)",
    )
    activity_participation: int = Field(
        ...,
        description="二.1 活动参与 (0-45)",
    )
    internal_activities: int = Field(
        ...,
        description="二.2 内部活动 (0-25)",
    )
    club_history: int = Field(
        ...,
        description="三、社团历史 ≥2年 (0 或 5)",
    )


class StarRatingResponse(BaseModel):
    club_id: int
    total_score: int = Field(..., description="总分 (上限 100)")
    breakdown: StarRatingBreakdown = Field(..., description="分项明细")
    internal_activity_count: int = Field(
        ...,
        description="内部活动次数（供参考）",  # noqa: RUF001
    )
    has_federation_participation: bool = Field(
        ...,
        description="是否参与过社联活动",
    )
    club_age_years: float = Field(..., description="社团成立年数")
