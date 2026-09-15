import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from starlette.requests import Request
from starlette.responses import JSONResponse

import app.models as _  # noqa: F401
from app.api.v1 import router as v1_router
from app.core.maintenance import prune_login_attempts, start_prune_task
from app.core.settings import web_settings
from app.services.errors import BusinessError

settings = web_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Retention sweep: once at startup, then daily. Failures are logged and
    # swallowed so a missing table (e.g. before the first migration) cannot
    # stop the app from booting.
    try:
        await prune_login_attempts()
    except Exception:
        logger.exception("Startup login-attempt prune failed")

    task = start_prune_task()
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="BNDSphere API",
    description="Backend Service for BNDSphere",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
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
        content={
            "message_key": exc.message_key,
            "error_code": exc.error_code,
            "details": exc.details,
        },
        headers=exc.headers,
    )


@app.get("/health", status_code=status.HTTP_204_NO_CONTENT)
async def health_check() -> None:
    pass
