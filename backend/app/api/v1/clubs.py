from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common_responses import TOKEN_INVALID_RESPONSE
from app.api.dependencies import get_db
from app.schemas.club import ClubInfo
from app.models.club import Club

router = APIRouter()


@router.get(
    "/info/{club_id}",
    response_model=ClubInfo,
    status_code=status.HTTP_200_OK,
    responses=TOKEN_INVALID_RESPONSE,
)
async def get_club_info(club_id: int, db: AsyncSession = Depends(get_db)) -> Club:
    club = await db.get(Club, club_id)
    if club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Club with id {club_id} not found",
        )
    return club
