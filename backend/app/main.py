from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.api.v1 import router as v1_router

app = FastAPI(
    title = "BNDSphere API",
    description = "Backend Service for BNDSphere",
    version = "0.1.0",
    docs_url='/api/docs',
    openapi_url='/api/openapi.json'
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)
app.debug = settings.debug

app.include_router(v1_router, prefix='/api/v1')
