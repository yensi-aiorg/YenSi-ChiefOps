"""
Progressive summary compaction.

When the conversation grows beyond the recent window (10 turns), older
turns are summarised into a running compacted summary. This keeps the
context window manageable while preserving essential information.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.base import generate_uuid, utc_now

logger = logging.getLogger(__name__)

# Number of recent turns to keep in full
RECENT_WINDOW = 10

# Maximum number of turns before compaction is triggered
COMPACTION_TRIGGER = 15


async def check_compaction_needed(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> bool:
    """Check whether compaction is needed for a project's conversation.

    Compaction is triggered when the total turn count exceeds
    ``COMPACTION_TRIGGER`` and there are more than ``RECENT_WINDOW``
    un-compacted turns.

    Args:
        project_id: Project identifier.
        db: Motor database handle.

    Returns:
        True if compaction should be performed.
    """
    total_turns = await db.conversation_turns.count_documents(
        {"project_id": project_id}
    )

    if total_turns <= COMPACTION_TRIGGER:
        return False

    # Check if there are turns beyond the recent window that haven't been compacted
    compacted_summary = await db.compacted_summaries.find_one(
        {"project_id": project_id},
        sort=[("last_compacted_turn", -1)],
    )

    last_compacted_turn = 0
    if compacted_summary:
        last_compacted_turn = compacted_summary.get("last_compacted_turn", 0)

    uncompacted_count = await db.conversation_turns.count_documents({
        "project_id": project_id,
        "turn_number": {"$gt": last_compacted_turn},
    })

    return uncompacted_count > COMPACTION_TRIGGER


async def compact(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Compact old conversation turns into a running summary.

    Takes all turns older than the recent window and asks the AI to
    produce a concise summary. This summary is then stored and
    used in place of the individual turns.

    Args:
        project_id: Project identifier.
        db: Motor database handle.
        ai_adapter: AI adapter instance with ``generate_text`` method.

    Returns:
        The compacted summary document.
    """
    # Get all turns sorted by turn number
    all_turns: list[dict[str, Any]] = []
    async for turn in db.conversation_turns.find(
        {"project_id": project_id}
    ).sort("turn_number", 1):
        all_turns.append(turn)

    if len(all_turns) <= RECENT_WINDOW:
        logger.debug("Not enough turns to compact for project %s", project_id)
        return {}

    # Turns to compact are everything except the last RECENT_WINDOW turns
    turns_to_compact = all_turns[:-RECENT_WINDOW]
    last_compacted_turn = turns_to_compact[-1].get("turn_number", 0)

    # Get existing compacted summary
    existing_summary = await db.compacted_summaries.find_one(
        {"project_id": project_id},
        sort=[("last_compacted_turn", -1)],
    )
    previous_summary = existing_summary.get("summary", "") if existing_summary else ""

    # Build the text to summarise
    turn_texts: list[str] = []
    if previous_summary:
        turn_texts.append(f"Previous summary:\n{previous_summary}\n")

    for turn in turns_to_compact:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        turn_num = turn.get("turn_number", "?")
        turn_texts.append(f"Turn {turn_num} ({role}): {content}")

    combined = "\n\n".join(turn_texts)

    # Generate summary
    if ai_adapter is not None:
        summary_text = await _ai_summarise(combined, ai_adapter)
    else:
        summary_text = _fallback_summarise(turns_to_compact)

    # Store the compacted summary
    summary_doc: dict[str, Any] = {
        "summary_id": generate_uuid(),
        "project_id": project_id,
        "summary": summary_text,
        "turns_compacted": len(turns_to_compact),
        "last_compacted_turn": last_compacted_turn,
        "created_at": utc_now(),
    }

    await db.compacted_summaries.update_one(
        {"project_id": project_id},
        {"$set": summary_doc},
        upsert=True,
    )

    logger.info(
        "Compacted %d turns for project %s (up to turn %d)",
        len(turns_to_compact),
        project_id,
        last_compacted_turn,
    )

    return summary_doc


async def _ai_summarise(text: str, ai_adapter: Any) -> str:
    """Use the AI adapter to produce a summary."""
    prompt = (
        "Summarize the following conversation history concisely. "
        "Preserve key decisions, action items, important context, and "
        "any corrections or clarifications made. Keep the summary under "
        "500 words but ensure no critical information is lost.\n\n"
        f"{text}"
    )

    try:
        result = await ai_adapter.generate_text(
            prompt=prompt,
            system=(
                "You are a conversation summarizer for a project management tool. "
                "Produce concise but complete summaries that preserve all actionable information."
            ),
        )
        return result.strip()
    except Exception as exc:
        logger.warning("AI summarisation failed: %s", exc)
        return _fallback_summarise_text(text)


def _fallback_summarise(turns: list[dict[str, Any]]) -> str:
    """Produce a simple extractive summary without AI."""
    lines: list[str] = []
    for turn in turns:
        content = turn.get("content", "")
        role = turn.get("role", "unknown")
        turn_num = turn.get("turn_number", "?")

        # Keep first 200 chars of each turn
        preview = content[:200]
        if len(content) > 200:
            preview += "..."
        lines.append(f"[Turn {turn_num}] {role}: {preview}")

    return "\n".join(lines)


def _fallback_summarise_text(text: str) -> str:
    """Produce a simple truncated summary from raw text."""
    # Keep first 2000 chars
    if len(text) > 2000:
        return text[:2000] + "\n... [truncated]"
    return text
