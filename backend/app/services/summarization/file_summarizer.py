"""Per-file summarization using Claude CLI.

Each uploaded project file gets a file-type-aware markdown summary
stored in the ``file_summaries`` collection.
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

MAX_INPUT_CHARS = 80_000

# ---------------------------------------------------------------------------
# File-type-aware prompt templates
# ---------------------------------------------------------------------------

SLACK_PROMPT = """\
You are an operations analyst summarizing Slack messages for a COO.
Analyze the following Slack export text and produce a clear, structured markdown summary.

Use these sections:
## People Involved
List the key people who participated, with their roles if apparent.

## Topics Discussed
Major topics and threads of conversation.

## Decisions Made
Any decisions that were explicitly agreed upon.

## Blockers & Issues
Problems raised, blockers mentioned, or unresolved concerns.

## Jira / Ticket References
Any Jira ticket keys, PR numbers, or external references mentioned.

## Action Items
Specific action items, who is responsible, and any deadlines mentioned.

## Summary
A 2-3 sentence executive summary of what happened in this conversation.

Be concise. Use bullet points. Do not invent information not present in the text."""

JIRA_PROMPT = """\
You are an operations analyst summarizing Jira data for a COO.
Analyze the following Jira export data and produce a clear, structured markdown summary.

Use these sections:
## Total Tickets
Total count of tickets in this export.

## Status Breakdown
How many tickets are in each status (To Do, In Progress, Done, Blocked, etc.).

## Priority Distribution
Breakdown by priority level (Critical, High, Medium, Low).

## Assignees
List of assignees and how many tickets each person has.

## Blocked / Critical Items
Any blocked or critical-priority tickets that need attention, with their keys and summaries.

## Summary
A 2-3 sentence executive summary of the project's task health.

Be concise. Use bullet points. Do not invent information not present in the data."""

DOC_PROMPT = """\
You are an operations analyst summarizing a document for a COO.
Analyze the following document text and produce a clear, structured markdown summary.

Use these sections:
## Document Purpose
What this document is about and why it exists.

## Key Information
The most important facts, figures, and details.

## Decisions & Outcomes
Any decisions documented or outcomes described.

## Risks & Concerns
Any risks, concerns, or caveats mentioned.

## People Referenced
People mentioned in the document and their relevance.

## Summary
A 2-3 sentence executive summary of this document.

Be concise. Use bullet points. Do not invent information not present in the text."""


def _get_prompt_for_file_type(file_type: str) -> str:
    """Return the appropriate prompt template based on file type."""
    ft = file_type.lower()
    if "slack" in ft or ft == "slack_json":
        return SLACK_PROMPT
    if "jira" in ft or "xlsx" in ft or "csv" in ft:
        return JIRA_PROMPT
    return DOC_PROMPT


async def summarize_file(
    *,
    project_id: str,
    file_id: str,
    filename: str,
    file_type: str,
    text_content: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Summarize a single file's text content using Claude CLI.

    Writes the result to the ``file_summaries`` collection.
    **Never raises** — catches all exceptions and writes failure to DB.
    """
    settings = get_settings()
    summary_id = generate_uuid()
    now = utc_now()

    doc: dict[str, Any] = {
        "summary_id": summary_id,
        "project_id": project_id,
        "file_id": file_id,
        "filename": filename,
        "file_type": file_type,
        "status": "processing",
        "summary_markdown": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }

    try:
        # Truncate input
        truncated = text_content[:MAX_INPUT_CHARS]
        if not truncated.strip():
            doc["status"] = "failed"
            doc["error_message"] = "No text content to summarize."
            await db.file_summaries.insert_one(doc)
            return doc

        logger.info(
            "COO summarize: starting Claude CLI for %s (%s, %d chars)",
            filename,
            file_type,
            len(truncated),
        )

        system_prompt = _get_prompt_for_file_type(file_type)
        user_prompt = (
            f"File: {filename} (type: {file_type})\n\n"
            f"--- BEGIN CONTENT ---\n{truncated}\n--- END CONTENT ---"
        )

        adapter = CLIAdapter()
        adapter._timeout = settings.AI_SUMMARY_TIMEOUT

        request = AIRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        response = await adapter.generate(request)

        logger.info(
            "COO summarize: completed %s (%.0fms, %d bytes output)",
            filename,
            response.latency_ms,
            len(response.content),
        )

        doc["summary_markdown"] = response.content
        doc["status"] = "completed"
        doc["updated_at"] = utc_now()

    except Exception as exc:
        logger.warning(
            "File summarization failed for %s/%s: %s",
            project_id,
            filename,
            exc,
        )
        doc["status"] = "failed"
        doc["error_message"] = str(exc)[:500]
        doc["updated_at"] = utc_now()

    # Upsert so re-uploads replace old summaries for the same file
    await db.file_summaries.update_one(
        {"project_id": project_id, "file_id": file_id},
        {"$set": doc},
        upsert=True,
    )

    return doc
