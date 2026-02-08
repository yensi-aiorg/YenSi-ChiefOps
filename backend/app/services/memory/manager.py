"""
MemoryManager -- coordinates the three-layer memory system.

Orchestrates hard facts, compacted summaries, recent turns, and
Citex RAG retrieval to build a complete context for the AI. Also
handles post-turn processing (fact extraction, compaction checks).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.services.memory.assembler import assemble_context
from app.services.memory.compactor import check_compaction_needed, compact
from app.services.memory.hard_facts import extract_facts

logger = logging.getLogger(__name__)


async def get_context(
    project_id: str,
    query: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> str:
    """Get assembled context for a conversation query.

    Coordinates all memory layers:
    1. Retrieves hard facts from the database.
    2. Loads compacted summary if available.
    3. Fetches recent conversation turns.
    4. Calls Citex for RAG chunk retrieval.

    Args:
        project_id: Project scope for the conversation.
        query: The user's current message.
        db: Motor database handle.
        ai_adapter: AI adapter instance (used for compaction if needed).

    Returns:
        Assembled context string ready for AI prompt injection.
    """
    # Retrieve RAG chunks from Citex
    rag_chunks = await _retrieve_rag_chunks(query, project_id)

    # Check if compaction is needed before assembly
    needs_compaction = await check_compaction_needed(project_id, db)
    if needs_compaction:
        logger.info("Compaction triggered for project %s", project_id)
        await compact(project_id, db, ai_adapter)

    # Assemble the full context
    context = await assemble_context(
        project_id=project_id,
        query=query,
        db=db,
        rag_chunks=rag_chunks,
    )

    return context


async def process_turn(
    turn_content: str,
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> None:
    """Post-turn processing: extract facts and check compaction.

    Called after each conversation turn is completed. Extracts any
    hard facts from the turn and checks if the conversation needs
    compaction.

    Args:
        turn_content: Combined user + assistant turn content.
        project_id: Project scope.
        db: Motor database handle.
        ai_adapter: AI adapter instance.
    """
    # Extract hard facts asynchronously
    try:
        await extract_facts(
            turn_content=turn_content,
            ai_adapter=ai_adapter,
            db=db,
            project_id=project_id,
        )
    except Exception as exc:
        logger.warning("Fact extraction failed for project %s: %s", project_id, exc)

    # Check compaction after fact extraction
    try:
        needs_compaction = await check_compaction_needed(project_id, db)
        if needs_compaction:
            await compact(project_id, db, ai_adapter)
    except Exception as exc:
        logger.warning("Compaction check failed for project %s: %s", project_id, exc)


async def _retrieve_rag_chunks(
    query: str,
    project_id: Optional[str] = None,
) -> list[str]:
    """Retrieve relevant document chunks from Citex.

    Makes an HTTP call to the Citex extraction service to find
    relevant passages for the given query.

    Args:
        query: Search query text.
        project_id: Optional project scope for filtering.

    Returns:
        List of relevant text chunks, or empty list on failure.
    """
    settings = get_settings()
    citex_url = settings.CITEX_API_URL

    if not citex_url:
        return []

    try:
        payload: dict[str, Any] = {
            "query": query,
            "top_k": 5,
        }
        if project_id:
            payload["filters"] = {"project_id": project_id}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{citex_url}/api/v1/search",
                json=payload,
            )

            if response.status_code != 200:
                logger.warning(
                    "Citex search returned status %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return []

            data = response.json()
            chunks: list[str] = []
            for result in data.get("results", []):
                text = result.get("text", "")
                if text:
                    source = result.get("source", "")
                    title = result.get("title", "")
                    header = f"[Source: {source} - {title}]" if source else ""
                    chunks.append(f"{header}\n{text}" if header else text)

            logger.debug("Citex returned %d chunks for query", len(chunks))
            return chunks

    except httpx.ConnectError:
        logger.debug("Citex service not available, skipping RAG retrieval")
        return []
    except Exception as exc:
        logger.warning("Citex retrieval failed: %s", exc)
        return []
