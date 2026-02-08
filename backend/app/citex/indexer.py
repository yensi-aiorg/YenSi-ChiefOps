"""
Document indexing helpers for the Citex RAG service.

Transforms raw data from Slack messages, Jira tasks, and Drive documents
into Citex-compatible document payloads and handles chunking of large
content to stay within Citex's optimal chunk size (~600 characters).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.citex.client import CitexClient

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 600  # characters per chunk (Citex optimal window)
_CHUNK_OVERLAP = 50  # overlap between consecutive chunks


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks of approximately ``chunk_size`` characters.

    Tries to break on sentence boundaries (period, newline) within the
    chunk window to avoid cutting mid-sentence.

    Args:
        text: The full text to chunk.
        chunk_size: Target size per chunk in characters.
        overlap: Number of characters to overlap between consecutive chunks.

    Returns:
        List of text chunks. Returns ``[text]`` if the text is shorter
        than ``chunk_size``.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Try to find a sentence boundary near the end of the chunk
            search_region = text[max(start, end - 100) : end]
            # Look for last period followed by space/newline, or last newline
            best_break = -1
            for sep in [". ", ".\n", "\n\n", "\n"]:
                idx = search_region.rfind(sep)
                if idx != -1:
                    candidate = max(start, end - 100) + idx + len(sep)
                    if candidate > best_break:
                        best_break = candidate

            if best_break > start:
                end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < len(text) else len(text)

    return chunks


def _format_timestamp(ts: Any) -> str:
    """Safely format a timestamp value to ISO-8601 string."""
    if isinstance(ts, datetime):
        return ts.isoformat()
    if isinstance(ts, str):
        return ts
    return str(ts)


async def index_slack_messages(
    messages: list[dict[str, Any]],
    channel: str,
    project_id: str,
    citex_client: CitexClient,
) -> int:
    """Index a batch of Slack messages into Citex.

    Groups messages into chunks of approximately ``_CHUNK_SIZE`` characters
    for optimal retrieval performance. Each chunk includes message metadata
    (author, timestamp, channel) for traceability.

    Args:
        messages: List of message dicts with ``user_name``, ``text``,
                  ``timestamp`` keys.
        channel: Slack channel name.
        project_id: Project ID to scope the documents.
        citex_client: Citex client instance.

    Returns:
        Number of chunks successfully ingested.
    """
    if not messages:
        return 0

    # Build a combined transcript for the channel
    lines: list[str] = []
    for msg in messages:
        user = msg.get("user_name", msg.get("user_id", "unknown"))
        text = msg.get("text", "")
        ts = _format_timestamp(msg.get("timestamp", ""))
        if text.strip():
            lines.append(f"[{ts}] {user}: {text}")

    full_text = "\n".join(lines)
    chunks = _chunk_text(full_text)
    ingested = 0

    for i, chunk in enumerate(chunks):
        metadata = {
            "source": "slack",
            "channel": channel,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "message_count": len(messages),
        }
        result = await citex_client.ingest_document(
            project_id=project_id,
            content=chunk,
            metadata=metadata,
            filename=f"slack_{channel}_chunk_{i}.txt",
        )
        if result:
            ingested += 1

    logger.info(
        "Indexed %d/%d Slack chunks for channel=%s project=%s",
        ingested,
        len(chunks),
        channel,
        project_id,
    )
    return ingested


async def index_jira_tasks(
    tasks: list[dict[str, Any]],
    project_id: str,
    citex_client: CitexClient,
) -> int:
    """Index a batch of Jira tasks into Citex.

    Each task is formatted as a structured text block containing the
    task key, summary, description, status, assignee, and other fields.
    Large descriptions are chunked.

    Args:
        tasks: List of task dicts with Jira fields (``task_key``,
               ``summary``, ``description``, ``status``, etc.).
        project_id: Project ID to scope the documents.
        citex_client: Citex client instance.

    Returns:
        Number of chunks successfully ingested.
    """
    if not tasks:
        return 0

    ingested = 0

    for task in tasks:
        task_key = task.get("task_key", "UNKNOWN")
        summary = task.get("summary", "")
        description = task.get("description", "")
        status = task.get("status", "Unknown")
        assignee = task.get("assignee", "Unassigned")
        priority = task.get("priority", "Medium")
        sprint = task.get("sprint", "")
        labels = ", ".join(task.get("labels", []))

        text_parts = [
            f"Task: {task_key} - {summary}",
            f"Status: {status}",
            f"Assignee: {assignee}",
            f"Priority: {priority}",
        ]
        if sprint:
            text_parts.append(f"Sprint: {sprint}")
        if labels:
            text_parts.append(f"Labels: {labels}")
        if description:
            text_parts.append(f"Description: {description}")

        comments = task.get("comments", [])
        if comments:
            text_parts.append("Comments:")
            for comment in comments:
                text_parts.append(f"  - {comment}")

        full_text = "\n".join(text_parts)
        chunks = _chunk_text(full_text)

        for i, chunk in enumerate(chunks):
            metadata = {
                "source": "jira",
                "task_key": task_key,
                "status": status,
                "assignee": assignee,
                "priority": priority,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            result = await citex_client.ingest_document(
                project_id=project_id,
                content=chunk,
                metadata=metadata,
                filename=f"jira_{task_key}_chunk_{i}.txt",
            )
            if result:
                ingested += 1

    logger.info(
        "Indexed %d Jira chunks from %d tasks for project=%s",
        ingested,
        len(tasks),
        project_id,
    )
    return ingested


async def index_drive_document(
    content: str,
    filename: str,
    project_id: str,
    citex_client: CitexClient,
) -> int:
    """Index a Google Drive document into Citex.

    The document content is chunked into segments of approximately
    ``_CHUNK_SIZE`` characters with overlapping boundaries for better
    retrieval coverage.

    Args:
        content: Extracted text content of the document.
        filename: Original filename.
        project_id: Project ID to scope the document.
        citex_client: Citex client instance.

    Returns:
        Number of chunks successfully ingested.
    """
    if not content.strip():
        logger.warning("Skipping empty Drive document: %s", filename)
        return 0

    chunks = _chunk_text(content)
    ingested = 0

    for i, chunk in enumerate(chunks):
        metadata = {
            "source": "gdrive",
            "filename": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        result = await citex_client.ingest_document(
            project_id=project_id,
            content=chunk,
            metadata=metadata,
            filename=f"{filename}_chunk_{i}",
        )
        if result:
            ingested += 1

    logger.info(
        "Indexed %d/%d chunks for Drive document=%s project=%s",
        ingested,
        len(chunks),
        filename,
        project_id,
    )
    return ingested
