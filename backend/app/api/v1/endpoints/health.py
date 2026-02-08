"""
Health and readiness check endpoints.

Provides liveness and readiness probes for the ChiefOps backend,
verifying connectivity to MongoDB, Redis, and the Citex extraction service.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import get_settings
from app.database import get_database
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str = Field(..., description="Overall service status.")
    mongo: bool = Field(..., description="MongoDB connectivity.")
    redis: bool = Field(..., description="Redis connectivity.")
    citex: bool = Field(..., description="Citex extraction service connectivity.")


class DependencyDetail(BaseModel):
    """Detailed status for a single dependency."""

    healthy: bool = Field(..., description="Whether the dependency is reachable.")
    latency_ms: float = Field(..., description="Round-trip latency in milliseconds.")
    error: str | None = Field(default=None, description="Error message if unhealthy.")


class ReadinessResponse(BaseModel):
    """Detailed readiness check response."""

    status: str = Field(..., description="Overall readiness status: 'ready' or 'degraded'.")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of the check.")
    environment: str = Field(..., description="Deployment environment.")
    mongo: DependencyDetail = Field(..., description="MongoDB status detail.")
    redis: DependencyDetail = Field(..., description="Redis status detail.")
    citex: DependencyDetail = Field(..., description="Citex service status detail.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _check_mongo(db: AsyncIOMotorDatabase) -> tuple[bool, float, str | None]:  # type: ignore[type-arg]
    """Ping MongoDB and return (healthy, latency_ms, error)."""
    start = time.monotonic()
    try:
        await db.command("ping")
        latency = (time.monotonic() - start) * 1000
        return True, round(latency, 2), None
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.warning("MongoDB health check failed", exc_info=exc)
        return False, round(latency, 2), str(exc)


async def _check_redis(redis: Redis) -> tuple[bool, float, str | None]:  # type: ignore[type-arg]
    """Ping Redis and return (healthy, latency_ms, error)."""
    start = time.monotonic()
    try:
        await redis.ping()
        latency = (time.monotonic() - start) * 1000
        return True, round(latency, 2), None
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.warning("Redis health check failed", exc_info=exc)
        return False, round(latency, 2), str(exc)


async def _check_citex() -> tuple[bool, float, str | None]:
    """Hit the Citex /health endpoint and return (healthy, latency_ms, error)."""
    settings = get_settings()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.CITEX_API_URL}/health")
            latency = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                return True, round(latency, 2), None
            return False, round(latency, 2), f"HTTP {resp.status_code}"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.warning("Citex health check failed", exc_info=exc)
        return False, round(latency, 2), str(exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns the liveness status and connectivity of core dependencies.",
)
async def health_check(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> HealthResponse:
    mongo_ok, _, _ = await _check_mongo(db)
    redis_ok, _, _ = await _check_redis(redis)
    citex_ok, _, _ = await _check_citex()

    overall = "ok" if (mongo_ok and redis_ok) else "degraded"

    return HealthResponse(
        status=overall,
        mongo=mongo_ok,
        redis=redis_ok,
        citex=citex_ok,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Detailed readiness check",
    description="Returns detailed connectivity and latency information for all dependencies.",
)
async def readiness_check(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> ReadinessResponse:
    settings = get_settings()

    mongo_ok, mongo_lat, mongo_err = await _check_mongo(db)
    redis_ok, redis_lat, redis_err = await _check_redis(redis)
    citex_ok, citex_lat, citex_err = await _check_citex()

    all_healthy = mongo_ok and redis_ok and citex_ok
    overall = "ready" if all_healthy else "degraded"

    return ReadinessResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.ENVIRONMENT,
        mongo=DependencyDetail(healthy=mongo_ok, latency_ms=mongo_lat, error=mongo_err),
        redis=DependencyDetail(healthy=redis_ok, latency_ms=redis_lat, error=redis_err),
        citex=DependencyDetail(healthy=citex_ok, latency_ms=citex_lat, error=citex_err),
    )
