from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import settings

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
