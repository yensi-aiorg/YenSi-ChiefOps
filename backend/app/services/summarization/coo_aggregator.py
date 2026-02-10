"""COO briefing aggregator.

Reads all completed file summaries for a project, sends them to Claude CLI
with a structured JSON schema, and stores the resulting 5-section COO briefing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.ai.adapter import AIRequest
from app.ai.cli_adapter import CLIAdapter
from app.config import get_settings
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

MAX_COMBINED_CHARS = 100_000

COO_SYSTEM_PROMPT = """\
You are a Chief Operating Officer's AI briefing assistant.
You have been given markdown summaries of multiple project files (Slack exports,
Jira data, documents, etc.). Your job is to synthesize them into a single
structured COO briefing.

Be direct, factual, and actionable. Do not invent information not supported
by the file summaries. If information is insufficient for a section, say so
rather than guessing."""

COO_BRIEFING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "executive_summary",
        "attention_items",
        "project_health",
        "team_capacity",
        "upcoming_deadlines",
        "recent_changes",
    ],
    "properties": {
        "executive_summary": {
            "type": "string",
            "description": "2-4 sentence high-level summary of overall project status.",
        },
        "attention_items": {
            "type": "array",
            "description": "Items requiring COO attention, ordered by severity.",
            "items": {
                "type": "object",
                "required": ["title", "severity", "details"],
                "properties": {
                    "title": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["red", "amber", "green"],
                    },
                    "details": {"type": "string"},
                },
            },
        },
        "project_health": {
            "type": "object",
            "required": ["status", "score", "rationale"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["red", "yellow", "green"],
                },
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                },
                "rationale": {"type": "string"},
            },
        },
        "team_capacity": {
            "type": "array",
            "description": "People identified from the files with capacity assessment.",
            "items": {
                "type": "object",
                "required": ["person", "status", "details"],
                "properties": {
                    "person": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["overloaded", "balanced", "underutilized"],
                    },
                    "details": {"type": "string"},
                },
            },
        },
        "upcoming_deadlines": {
            "type": "array",
            "description": "Deadlines and milestones identified from the files.",
            "items": {
                "type": "object",
                "required": ["item", "date", "status"],
                "properties": {
                    "item": {"type": "string"},
                    "date": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["on_track", "at_risk", "overdue"],
                    },
                },
            },
        },
        "recent_changes": {
            "type": "array",
            "description": "Notable recent changes, decisions, or events.",
            "items": {
                "type": "object",
                "required": ["change", "impact"],
                "properties": {
                    "change": {"type": "string"},
                    "impact": {"type": "string"},
                },
            },
        },
    },
}


async def generate_coo_briefing(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Aggregate file summaries into a structured COO briefing.

    Reads all completed ``file_summaries`` for the project, sends them
    to Claude CLI with a JSON schema, and stores the result in ``coo_briefings``.

    **Never raises** — catches all exceptions and writes failure to DB.
    """
    settings = get_settings()
    briefing_id = generate_uuid()
    now = utc_now()

    doc: dict[str, Any] = {
        "briefing_id": briefing_id,
        "project_id": project_id,
        "status": "processing",
        "briefing": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }

    try:
        # Fetch completed file summaries
        cursor = db.file_summaries.find(
            {"project_id": project_id, "status": "completed"},
            {"_id": 0, "filename": 1, "file_type": 1, "summary_markdown": 1},
        )
        summaries = await cursor.to_list(length=500)

        if not summaries:
            doc["status"] = "failed"
            doc["error_message"] = "No completed file summaries available to aggregate."
            await db.coo_briefings.insert_one(doc)
            return doc

        # Build combined text
        parts: list[str] = []
        for s in summaries:
            parts.append(
                f"### File: {s['filename']} (type: {s['file_type']})\n\n"
                f"{s['summary_markdown']}\n"
            )
        combined = "\n---\n\n".join(parts)
        if len(combined) > MAX_COMBINED_CHARS:
            combined = combined[:MAX_COMBINED_CHARS] + "\n\n[...truncated]"

        logger.info(
            "COO briefing: aggregating %d summaries (%d chars) for project %s",
            len(summaries),
            len(combined),
            project_id,
        )

        user_prompt = (
            f"Project ID: {project_id}\n"
            f"Number of file summaries: {len(summaries)}\n\n"
            f"--- FILE SUMMARIES ---\n\n{combined}\n\n--- END SUMMARIES ---\n\n"
            "Produce the COO briefing JSON based on the above file summaries."
        )

        adapter = CLIAdapter()
        adapter._timeout = settings.AI_SUMMARY_TIMEOUT

        request = AIRequest(
            system_prompt=COO_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=COO_BRIEFING_SCHEMA,
            temperature=0.1,
        )

        response = await adapter.generate_structured(request)
        briefing_data = response.parse_json()

        logger.info(
            "COO briefing: completed for project %s (%.0fms)",
            project_id,
            response.latency_ms,
        )

        doc["briefing"] = briefing_data
        doc["status"] = "completed"
        doc["updated_at"] = utc_now()

    except Exception as exc:
        logger.warning(
            "COO briefing generation failed for project %s: %s",
            project_id,
            exc,
        )
        doc["status"] = "failed"
        doc["error_message"] = str(exc)[:500]
        doc["updated_at"] = utc_now()

    await db.coo_briefings.insert_one(doc)
    return doc
