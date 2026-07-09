from pydantic import BaseModel, Field

from app.models.club import ClubStarLevelEnum


class StarRatingBreakdown(BaseModel):
    meeting_attendance: int = Field(
        ...,
        description="一、会议出勤 (0 或 10)",
    )
    activity_participation: int = Field(
        ...,
        description="二.1 校级/大型活动得分 (0-45)",
    )
    competition: int = Field(
        ...,
        description="二.1 竞赛得分 (与校级/大型活动合计上限 45)",
    )
    section_2_1_total: int = Field(
        ...,
        description="二.1 合计 (活动+竞赛, 上限 45)",
    )
    internal_activities: int = Field(
        ...,
        description="二.2 内部活动 (0-30)",
    )
    growth_story: int = Field(
        ...,
        description=(
            "三、成长故事 (0 或 5, 上限前原始值; "
            "此三项之和可能超过 special_bonuses 上限)"
        ),
    )
    cross_grade_influence: int = Field(
        ...,
        description="三、跨年级影响力 (0 或 5, 上限前原始值)",
    )
    club_history: int = Field(
        ...,
        description="三、社团历史 >=2年 (0 或 5, 上限前原始值)",
    )
    special_bonuses: int = Field(
        ...,
        description="三、特色加分合计 (上限 10)",
    )


class StarRatingResponse(BaseModel):
    club_id: int
    total_score: int = Field(..., description="总分 (上限 100)")
    star_level: ClubStarLevelEnum = Field(..., description="评定的星级")
    breakdown: StarRatingBreakdown = Field(..., description="分项明细")
    internal_activity_count: int = Field(
        ...,
        description="内部活动次数(供参考)",
    )
    has_federation_participation: bool = Field(
        ...,
        description="是否参与过社联会议",
    )
    club_age_years: float = Field(..., description="社团成立年数")
