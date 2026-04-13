from fastapi import APIRouter

from app.api.dependencies import StarRatingServiceDep
from app.schemas.star_rating import StarRatingResponse

router = APIRouter(tags=["Club Star Rating"])


@router.get("/")
async def get_club_star_rating(
    club_id: int,
    service: StarRatingServiceDep,
) -> StarRatingResponse:
    return await service.calculate_score(club_id)
