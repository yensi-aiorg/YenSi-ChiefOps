from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_database: AsyncIOMotorDatabase | None = None  # type: ignore[type-arg]


async def connect_mongodb() -> None:
    """Create the Motor client and select the database.

    Called once during application startup.
    """
    global _client, _database  # noqa: PLW0603
    settings = get_settings()

    logger.info(
        "Connecting to MongoDB",
        extra={"mongo_url": _mask_url(settings.MONGO_URL), "db": settings.MONGO_DB_NAME},
    )

    _client = AsyncIOMotorClient(
        settings.MONGO_URL,
        maxPoolSize=50,
        minPoolSize=5,
        maxIdleTimeMS=30_000,
        connectTimeoutMS=5_000,
        serverSelectionTimeoutMS=5_000,
        retryWrites=True,
        retryReads=True,
    )

    _database = _client[settings.MONGO_DB_NAME]

    # Verify connectivity with a ping
    await _client.admin.command("ping")
    logger.info("MongoDB connection established")


async def close_mongodb() -> None:
    """Close the Motor client.

    Called once during application shutdown.
    """
    global _client, _database  # noqa: PLW0603
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")
    _client = None
    _database = None


def get_database_sync() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """Return the database instance directly (non-generator).

    Useful inside non-endpoint code (services, background tasks).
    Raises RuntimeError if the database has not been initialised.
    """
    if _database is None:
        raise RuntimeError("MongoDB is not initialised. Call connect_mongodb() first.")
    return _database


async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:  # type: ignore[type-arg]
    """FastAPI dependency that yields the database handle."""
    if _database is None:
        raise RuntimeError("MongoDB is not initialised. Call connect_mongodb() first.")
    yield _database


def _mask_url(url: str) -> str:
    """Replace password portion of a MongoDB URI for safe logging."""
    if "@" not in url:
        return url
    scheme_rest = url.split("://", 1)
    if len(scheme_rest) != 2:
        return "***"
    creds_host = scheme_rest[1].split("@", 1)
    if len(creds_host) != 2:
        return "***"
    return f"{scheme_rest[0]}://***:***@{creds_host[1]}"
