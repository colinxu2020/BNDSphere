from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from starlette.requests import Request
from starlette.responses import JSONResponse

import app.models as _  # noqa: F401
from app.api.v1 import router as v1_router
from app.core.settings import settings
from app.services.errors import BusinessError

app = FastAPI(
    title="BNDSphere API",
    description="Backend Service for BNDSphere",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.debug = settings.debug

app.include_router(v1_router, prefix="/api/v1")
add_pagination(app)


@app.exception_handler(BusinessError)
async def business_exception_handler(
    _request: Request,
    exc: BusinessError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )
