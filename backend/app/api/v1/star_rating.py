from fastapi import APIRouter

from app.api.dependencies import StarRatingServiceDep
from app.schemas.star_rating import StarRatingResponse

router = APIRouter(tags=["Club Star Rating"])


@router.get("/")
async def get_club_star_rating(
    club_id: int,
    service: StarRatingServiceDep,
) -> StarRatingResponse:
    """Calculate the estimated star-level rating score for a club.

    Scoring modules:
    - 一、会议出勤 (10): participated in any club_federation activity this term
    - 二.1 活动参与 (≤45): sum of approved school/large activity final_scores
    - 二.2 内部活动 (≤25): internal activity count thresholds
    - 三、社团历史 (5): club created more than 2 years ago

    Total is capped at 100.
    """
    return await service.calculate_score(club_id)
