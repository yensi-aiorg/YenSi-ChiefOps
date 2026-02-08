"""
Chunk audit logging for privacy compliance.

Records which data chunks (documents, messages, tasks) are accessed
during AI processing, who requested them, and what context they
were used in. This creates an audit trail for data access compliance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def log_chunk_access(
    request_id: str,
    chunks: list[dict[str, Any]],
    purpose: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    project_id: str | None = None,
    user_context: str | None = None,
) -> str:
    """Log the access of data chunks during AI processing.

    Creates an audit record that tracks which data was retrieved
    and sent to the AI model for processing.

    Args:
        request_id: UUID of the originating request.
        chunks: List of chunk metadata dicts with at least ``source``
                and ``document_id`` keys.
        purpose: Description of why the chunks were accessed
                 (e.g., "conversation_context", "report_generation").
        db: Motor database handle.
        project_id: Optional project scope.
        user_context: Optional description of the user's query.

    Returns:
        The audit log entry ID.
    """
    audit_id = generate_uuid()
    now = utc_now()

    # Build chunk references (stripped of content for storage efficiency)
    chunk_refs: list[dict[str, Any]] = []
    for chunk in chunks:
        ref: dict[str, Any] = {
            "source": chunk.get("source", "unknown"),
            "document_id": chunk.get("document_id", ""),
            "title": chunk.get("title", ""),
            "content_length": len(chunk.get("content", "")),
        }
        if "source_ref" in chunk:
            ref["source_ref"] = chunk["source_ref"]
        chunk_refs.append(ref)

    audit_doc: dict[str, Any] = {
        "audit_id": audit_id,
        "request_id": request_id,
        "action": "chunk_access",
        "purpose": purpose,
        "project_id": project_id,
        "user_context": user_context,
        "chunks_accessed": chunk_refs,
        "chunk_count": len(chunk_refs),
        "created_at": now,
    }

    await db.audit_log.insert_one(audit_doc)

    logger.debug(
        "Chunk access logged: %d chunks for %s (request: %s)",
        len(chunk_refs),
        purpose,
        request_id[:8],
    )

    return audit_id


async def log_ai_interaction(
    request_id: str,
    model: str,
    prompt_token_count: int,
    response_token_count: int,
    purpose: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    project_id: str | None = None,
    had_pii: bool = False,
) -> str:
    """Log an AI model interaction for audit purposes.

    Records metadata about AI calls without storing the actual
    prompt or response content.

    Args:
        request_id: UUID of the originating request.
        model: AI model identifier used.
        prompt_token_count: Approximate token count of the prompt.
        response_token_count: Approximate token count of the response.
        purpose: What the AI call was for.
        db: Motor database handle.
        project_id: Optional project scope.
        had_pii: Whether PII was detected in the input.

    Returns:
        The audit log entry ID.
    """
    audit_id = generate_uuid()

    audit_doc: dict[str, Any] = {
        "audit_id": audit_id,
        "request_id": request_id,
        "action": "ai_interaction",
        "model": model,
        "prompt_tokens": prompt_token_count,
        "response_tokens": response_token_count,
        "total_tokens": prompt_token_count + response_token_count,
        "purpose": purpose,
        "project_id": project_id,
        "had_pii_input": had_pii,
        "created_at": utc_now(),
    }

    await db.audit_log.insert_one(audit_doc)

    logger.debug(
        "AI interaction logged: %s model, %d total tokens (request: %s)",
        model,
        prompt_token_count + response_token_count,
        request_id[:8],
    )

    return audit_id


async def get_audit_trail(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    request_id: str | None = None,
    project_id: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Retrieve audit trail entries with optional filters.

    Args:
        db: Motor database handle.
        request_id: Filter by originating request.
        project_id: Filter by project scope.
        action: Filter by action type.
        since: Only include entries after this datetime.
        limit: Maximum number of entries to return.

    Returns:
        List of audit log entries, newest first.
    """
    query: dict[str, Any] = {}

    if request_id:
        query["request_id"] = request_id
    if project_id:
        query["project_id"] = project_id
    if action:
        query["action"] = action
    if since:
        query["created_at"] = {"$gte": since}

    entries: list[dict[str, Any]] = []
    async for doc in db.audit_log.find(query).sort("created_at", -1).limit(limit):
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        entries.append(doc)

    return entries


async def get_access_summary(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    since: datetime | None = None,
) -> dict[str, Any]:
    """Get a summary of data access patterns for compliance reporting.

    Args:
        db: Motor database handle.
        since: Only include entries after this datetime.

    Returns:
        Summary dict with access counts, unique sources, and AI usage.
    """
    match_stage: dict[str, Any] = {}
    if since:
        match_stage["created_at"] = {"$gte": since}

    # Chunk access summary
    chunk_pipeline: list[dict[str, Any]] = []
    if match_stage:
        chunk_pipeline.append({"$match": {**match_stage, "action": "chunk_access"}})
    else:
        chunk_pipeline.append({"$match": {"action": "chunk_access"}})

    chunk_pipeline.extend(
        [
            {
                "$group": {
                    "_id": None,
                    "total_accesses": {"$sum": 1},
                    "total_chunks": {"$sum": "$chunk_count"},
                }
            },
        ]
    )

    chunk_summary: dict[str, int] = {"total_accesses": 0, "total_chunks": 0}
    async for doc in db.audit_log.aggregate(chunk_pipeline):
        chunk_summary = {
            "total_accesses": doc.get("total_accesses", 0),
            "total_chunks": doc.get("total_chunks", 0),
        }

    # AI interaction summary
    ai_pipeline: list[dict[str, Any]] = []
    if match_stage:
        ai_pipeline.append({"$match": {**match_stage, "action": "ai_interaction"}})
    else:
        ai_pipeline.append({"$match": {"action": "ai_interaction"}})

    ai_pipeline.extend(
        [
            {
                "$group": {
                    "_id": None,
                    "total_interactions": {"$sum": 1},
                    "total_tokens": {"$sum": "$total_tokens"},
                    "pii_interactions": {"$sum": {"$cond": ["$had_pii_input", 1, 0]}},
                }
            },
        ]
    )

    ai_summary: dict[str, int] = {
        "total_interactions": 0,
        "total_tokens": 0,
        "pii_interactions": 0,
    }
    async for doc in db.audit_log.aggregate(ai_pipeline):
        ai_summary = {
            "total_interactions": doc.get("total_interactions", 0),
            "total_tokens": doc.get("total_tokens", 0),
            "pii_interactions": doc.get("pii_interactions", 0),
        }

    return {
        "chunk_access": chunk_summary,
        "ai_interactions": ai_summary,
        "period_start": since.isoformat() if since else "all_time",
    }
