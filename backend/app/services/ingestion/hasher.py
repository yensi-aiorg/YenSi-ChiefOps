"""
Content hashing service for deduplication during ingestion.

Computes SHA-256 hashes of file content to detect duplicates before
processing. Hashes are stored in the ``ingestion_hashes`` collection
so re-uploads of identical content are skipped.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


def compute_hash(content: bytes) -> str:
    """Compute a SHA-256 hex digest of the given content.

    Args:
        content: Raw bytes to hash.

    Returns:
        Lowercase hex string of the SHA-256 digest.
    """
    return hashlib.sha256(content).hexdigest()


async def check_duplicate(
    content_hash: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> bool:
    """Check whether a content hash already exists in the database.

    Args:
        content_hash: SHA-256 hex digest to look up.
        db: Motor database handle.

    Returns:
        True if the hash is already recorded (duplicate), False otherwise.
    """
    doc = await db.ingestion_hashes.find_one({"content_hash": content_hash})
    return doc is not None


async def record_hash(
    content_hash: str,
    filename: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Record a content hash for future duplicate detection.

    Uses upsert so calling with an existing hash is safe and simply
    updates the ``last_seen_at`` timestamp.

    Args:
        content_hash: SHA-256 hex digest.
        filename: Original filename that produced this hash.
        db: Motor database handle.
    """
    now = datetime.now(UTC)
    await db.ingestion_hashes.update_one(
        {"content_hash": content_hash},
        {
            "$set": {
                "content_hash": content_hash,
                "filename": filename,
                "last_seen_at": now,
            },
            "$setOnInsert": {
                "first_seen_at": now,
            },
        },
        upsert=True,
    )
    logger.debug("Recorded hash for %s: %s", filename, content_hash[:16])
