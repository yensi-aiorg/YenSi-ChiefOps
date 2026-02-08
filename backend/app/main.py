from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.database import close_mongodb, connect_mongodb, get_database_sync
from app.db.indexes import create_indexes
from app.redis_client import close_redis, connect_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of external connections."""
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)

    logger.info(
        "Starting ChiefOps backend",
        extra={"environment": settings.ENVIRONMENT},
    )

    # --- Startup ---
    await connect_mongodb()
    await connect_redis()

    # Create indexes after MongoDB is connected
    db = get_database_sync()
    await create_indexes(db)

    logger.info("ChiefOps backend ready")

    yield

    # --- Shutdown ---
    logger.info("Shutting down ChiefOps backend")
    await close_redis()
    await close_mongodb()
    logger.info("ChiefOps backend stopped")


def create_application() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="ChiefOps API",
        description="AI-powered project management backend",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
    )

    # --- CORS ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers ---
    @application.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> ORJSONResponse:
        logger.warning(
            "Application error: %s",
            exc.message,
            extra={"error_code": exc.error_code, "status_code": exc.status_code},
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> ORJSONResponse:
        logger.exception("Unhandled exception: %s", str(exc))
        return ORJSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )

    # --- Routers ---
    application.include_router(v1_router, prefix="/api/v1")

    return application


app = create_application()
