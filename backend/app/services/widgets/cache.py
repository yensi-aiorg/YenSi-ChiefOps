"""
Redis caching for widget query results.

Caches expensive query results with configurable TTL to avoid
repeated database hits for dashboard rendering.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from app.redis_client import get_redis_sync

logger = logging.getLogger(__name__)

# Cache key prefix
_CACHE_PREFIX = "chiefops:widget_cache:"

# Default TTL in seconds (5 minutes)
DEFAULT_TTL = 300


def _make_cache_key(query_hash: str) -> str:
    """Build a Redis key from a query hash."""
    return f"{_CACHE_PREFIX}{query_hash}"


def compute_query_hash(data_query: dict[str, Any]) -> str:
    """Compute a deterministic hash for a data query.

    The query dict is serialised with sorted keys to ensure
    identical queries produce the same hash.

    Args:
        data_query: The query specification dict.

    Returns:
        SHA-256 hex digest of the serialised query.
    """
    serialised = json.dumps(data_query, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


async def get_cached(query_hash: str) -> Optional[dict[str, Any]]:
    """Retrieve a cached query result.

    Args:
        query_hash: SHA-256 hash of the query specification.

    Returns:
        The cached result dict, or None if not found or cache unavailable.
    """
    try:
        redis = get_redis_sync()
        key = _make_cache_key(query_hash)
        cached = await redis.get(key)

        if cached is None:
            return None

        result = json.loads(cached)
        logger.debug("Cache hit for query %s", query_hash[:16])
        return result

    except RuntimeError:
        # Redis not initialised
        logger.debug("Redis not available for cache read")
        return None
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in cache for key %s", query_hash[:16])
        return None
    except Exception as exc:
        logger.warning("Cache read error: %s", exc)
        return None


async def set_cached(
    query_hash: str,
    data: dict[str, Any],
    ttl: int = DEFAULT_TTL,
) -> None:
    """Store a query result in the cache.

    Args:
        query_hash: SHA-256 hash of the query specification.
        data: The query result dict to cache.
        ttl: Time-to-live in seconds (default 300 = 5 minutes).
    """
    try:
        redis = get_redis_sync()
        key = _make_cache_key(query_hash)
        serialised = json.dumps(data, default=str)
        await redis.setex(key, ttl, serialised)
        logger.debug("Cached query %s (TTL=%ds)", query_hash[:16], ttl)
    except RuntimeError:
        logger.debug("Redis not available for cache write")
    except Exception as exc:
        logger.warning("Cache write error: %s", exc)


async def invalidate_all() -> None:
    """Invalidate all cached widget query results.

    Uses Redis SCAN to find and delete all keys with the widget
    cache prefix. This is called after data ingestion to ensure
    dashboards show fresh data.
    """
    try:
        redis = get_redis_sync()
        cursor: int = 0
        deleted = 0
        pattern = f"{_CACHE_PREFIX}*"

        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        if deleted > 0:
            logger.info("Invalidated %d cached widget queries", deleted)

    except RuntimeError:
        logger.debug("Redis not available for cache invalidation")
    except Exception as exc:
        logger.warning("Cache invalidation error: %s", exc)


async def invalidate_by_collection(collection: str) -> None:
    """Invalidate cached results for queries that target a specific collection.

    This is a best-effort operation -- since query hashes don't encode
    the collection name, we invalidate all caches. For more granular
    invalidation, a query-to-hash mapping would be needed.

    Args:
        collection: The collection name whose data changed.
    """
    logger.debug("Invalidating all caches due to %s data change", collection)
    await invalidate_all()
