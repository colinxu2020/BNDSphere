from fastapi import APIRouter
from app.api.v1.users import router as users_router
from app.api.v1.auth import router as auth_router
from app.api.v1.clubs import router as clubs_router

router = APIRouter()
router.include_router(users_router, prefix="/users")
router.include_router(auth_router, prefix="/auth")
router.include_router(clubs_router, prefix="/clubs")
