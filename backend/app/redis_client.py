from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_redis: Redis | None = None  # type: ignore[type-arg]


async def connect_redis() -> None:
    """Create the async Redis connection pool.

    Called once during application startup.
    """
    global _pool, _redis
    settings = get_settings()

    logger.info(
        "Connecting to Redis",
        extra={"redis_url": _mask_redis_url(settings.REDIS_URL)},
    )

    _pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    _redis = Redis(connection_pool=_pool)

    # Verify connectivity
    await _redis.ping()
    logger.info("Redis connection established")


async def close_redis() -> None:
    """Close the Redis client and underlying pool.

    Called once during application shutdown.
    """
    global _pool, _redis
    if _redis is not None:
        await _redis.aclose()
        logger.info("Redis connection closed")
    if _pool is not None:
        await _pool.aclose()
    _redis = None
    _pool = None


def get_redis_sync() -> Redis:  # type: ignore[type-arg]
    """Return the Redis instance directly (non-generator).

    Useful inside non-endpoint code (services, background tasks).
    Raises RuntimeError if Redis has not been initialised.
    """
    if _redis is None:
        raise RuntimeError("Redis is not initialised. Call connect_redis() first.")
    return _redis


async def get_redis() -> AsyncGenerator[Redis, None]:  # type: ignore[type-arg]
    """FastAPI dependency that yields the Redis client."""
    if _redis is None:
        raise RuntimeError("Redis is not initialised. Call connect_redis() first.")
    yield _redis


def _mask_redis_url(url: str) -> str:
    """Replace password portion of a Redis URI for safe logging."""
    if "@" not in url:
        return url
    scheme_rest = url.split("://", 1)
    if len(scheme_rest) != 2:
        return "***"
    creds_host = scheme_rest[1].split("@", 1)
    if len(creds_host) != 2:
        return "***"
    return f"{scheme_rest[0]}://***@{creds_host[1]}"
