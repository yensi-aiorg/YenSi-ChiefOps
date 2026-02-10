"""
Project-scoped conversation helpers.

Handles:
- Appending conversation turns to a per-project markdown transcript.
- Detecting and applying briefing updates from conversation content.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from app.ai.adapter import AIAdapter

logger = logging.getLogger(__name__)

# Keywords that suggest the user wants a briefing update
_UPDATE_KEYWORDS = re.compile(
    r"\b(update|change|modify|revise|rewrite|edit|adjust)\b",
    re.IGNORECASE,
)
_BRIEFING_KEYWORDS = re.compile(
    r"\b(briefing|summary|executive\s+summary|executive|report)\b",
    re.IGNORECASE,
)


async def append_to_transcript(
    project_id: str,
    user_msg: str,
    assistant_msg: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Append a conversation exchange to the project transcript.

    Uses upsert: creates the document on first call, appends on subsequent calls.
    Stores both raw turns array and a rendered markdown string.
    """
    now = utc_now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M UTC")

    turn_entry = {
        "user": user_msg,
        "assistant": assistant_msg,
        "timestamp": now,
    }

    markdown_block = (
        f"\n## {timestamp_str}\n\n"
        f"**COO:** {user_msg}\n\n"
        f"**ChiefOps:** {assistant_msg}\n\n"
        "---\n"
    )

    # Check if transcript exists
    existing = await db.project_transcripts.find_one(
        {"project_id": project_id},
        {"content_markdown": 1, "turn_count": 1},
    )

    if existing:
        # Append to existing transcript
        new_markdown = (existing.get("content_markdown") or "") + markdown_block
        new_count = (existing.get("turn_count") or 0) + 1
        await db.project_transcripts.update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "content_markdown": new_markdown,
                    "turn_count": new_count,
                    "updated_at": now,
                },
                "$push": {"turns": turn_entry},
            },
        )
    else:
        # Create new transcript
        header = "# Project Conversation Log\n\n"
        await db.project_transcripts.insert_one(
            {
                "project_id": project_id,
                "content_markdown": header + markdown_block,
                "turns": [turn_entry],
                "turn_count": 1,
                "created_at": now,
                "updated_at": now,
            }
        )

    logger.debug("Transcript updated for project %s", project_id)


async def check_and_apply_briefing_update(
    user_msg: str,
    assistant_msg: str,
    project_id: str | None,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    adapter: AIAdapter,
) -> dict[str, Any] | None:
    """Detect if the conversation implies a briefing update request.

    If detected, generates an updated briefing via the AI adapter and
    inserts it as a new versioned document in coo_briefings.

    Returns metadata dict with briefing_updated flag, or None.
    """
    if not project_id:
        return None

    # Simple heuristic: user message must contain both update + briefing keywords
    if not (_UPDATE_KEYWORDS.search(user_msg) and _BRIEFING_KEYWORDS.search(user_msg)):
        return None

    logger.info("Briefing update detected in conversation for project %s", project_id)

    # Fetch the current briefing to use as a base
    current_briefing = await db.coo_briefings.find_one(
        {"project_id": project_id, "status": "completed"},
        sort=[("created_at", -1)],
    )

    if not current_briefing:
        logger.info("No existing briefing to update for project %s", project_id)
        return None

    current_data = current_briefing.get("briefing") or {}

    # Build a prompt for the adapter to produce an updated briefing
    from app.ai.adapter import AIRequest

    update_prompt = (
        "You are updating a COO briefing based on a conversation request.\n\n"
        f"Current briefing data:\n```json\n{json.dumps(current_data, indent=2, default=str)}\n```\n\n"
        f"The COO said: {user_msg}\n\n"
        f"Your previous response: {assistant_msg}\n\n"
        "Produce an updated briefing JSON with the same schema. "
        "Only modify the sections that the COO requested changes to. "
        "Return ONLY valid JSON with these keys: "
        "executive_summary, attention_items, project_health, "
        "team_capacity, upcoming_deadlines, recent_changes."
    )

    request = AIRequest(
        system_prompt="You are a briefing editor. Return only valid JSON.",
        user_prompt=update_prompt,
        max_tokens=4096,
        temperature=0.2,
    )

    try:
        response = await adapter.generate(request)
        updated_briefing = response.parse_json()
    except Exception as exc:
        logger.warning("Failed to generate briefing update: %s", exc)
        return None

    # Insert as a new briefing version
    now = utc_now()
    new_briefing_id = generate_uuid()

    await db.coo_briefings.insert_one(
        {
            "briefing_id": new_briefing_id,
            "project_id": project_id,
            "status": "completed",
            "briefing": updated_briefing,
            "source": "conversation_update",
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    logger.info(
        "New briefing version %s created for project %s",
        new_briefing_id,
        project_id,
    )

    return {"briefing_updated": True, "briefing_id": new_briefing_id}
