from fastapi import APIRouter

from app.api.v1.admin.academic_terms import router as academic_terms_router

router = APIRouter(tags=["admin"])
router.include_router(academic_terms_router, prefix="/academic_terms")
