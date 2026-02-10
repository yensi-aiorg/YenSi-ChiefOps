"""COO summarization pipeline orchestrator.

Provides two entry points:
- ``start_file_summarization`` — kicks off a single file's Claude CLI
  summary as an ``asyncio.Task`` immediately after text extraction completes.
- ``finalize_coo_briefing`` — awaits all outstanding summary tasks, then
  generates the aggregated COO briefing.

Designed so that each file's summarization runs in parallel with the ongoing
file-processing loop (text extraction + Citex), not sequentially after it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from app.services.summarization.coo_aggregator import generate_coo_briefing
from app.services.summarization.file_summarizer import summarize_file

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def _resolve_text_content(
    *,
    project_id: str,
    file_id: str,
    filename: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str | None:
    """Look up the extracted text for a file from text_documents."""
    # Try lookup via project_files -> text_document_id
    pf = await db.project_files.find_one(
        {"file_id": file_id, "project_id": project_id},
        {"_id": 0, "text_document_id": 1},
    )
    if pf and pf.get("text_document_id"):
        text_doc = await db.text_documents.find_one(
            {"document_id": pf["text_document_id"]},
            {"_id": 0, "content": 1, "text": 1, "extracted_text": 1},
        )
    else:
        text_doc = None

    if not text_doc:
        # Fallback: try finding by file_id directly
        text_doc = await db.text_documents.find_one(
            {"file_id": file_id},
            {"_id": 0, "content": 1, "text": 1, "extracted_text": 1},
        )

    if not text_doc:
        return None

    text_content = (
        text_doc.get("content")
        or text_doc.get("text")
        or text_doc.get("extracted_text")
        or ""
    )

    return text_content if text_content.strip() else None


def start_file_summarization(
    *,
    project_id: str,
    file_id: str,
    filename: str,
    file_type: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> asyncio.Task[dict[str, Any]]:
    """Fire off a single file's summarization as a background asyncio.Task.

    Called immediately after ``process_project_file`` completes for each file.
    The returned Task can be awaited later (after all files are processed)
    to collect the result before generating the COO briefing.
    """

    async def _summarize() -> dict[str, Any]:
        try:
            text_content = await _resolve_text_content(
                project_id=project_id,
                file_id=file_id,
                filename=filename,
                db=db,
            )
            if not text_content:
                logger.warning(
                    "COO pipeline: no text found for file %s/%s, skipping summary.",
                    project_id,
                    filename,
                )
                return {"status": "skipped", "file_id": file_id, "filename": filename}

            return await summarize_file(
                project_id=project_id,
                file_id=file_id,
                filename=filename,
                file_type=file_type,
                text_content=text_content,
                db=db,
            )
        except Exception as exc:
            logger.warning(
                "COO pipeline: summarization failed for %s/%s: %s",
                project_id,
                filename,
                exc,
            )
            return {"status": "failed", "file_id": file_id, "filename": filename}

    return asyncio.create_task(_summarize())


async def finalize_coo_briefing(
    *,
    project_id: str,
    summary_tasks: list[asyncio.Task[dict[str, Any]]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Await all summary tasks and generate the aggregated COO briefing.

    Called once after the file-processing loop completes and the upload job
    is marked "completed". By this point the summary tasks have been running
    concurrently with file processing, so many may already be done.

    **Never propagates exceptions** to the caller.
    """
    try:
        if not summary_tasks:
            logger.info(
                "COO pipeline: no summary tasks for project %s, skipping briefing.",
                project_id,
            )
            return

        logger.info(
            "COO pipeline: waiting for %d file summaries for project %s.",
            len(summary_tasks),
            project_id,
        )

        # Wait for any remaining summaries to finish
        await asyncio.gather(*summary_tasks, return_exceptions=True)

        # Generate aggregated COO briefing
        logger.info(
            "COO pipeline: generating COO briefing for project %s.",
            project_id,
        )
        await generate_coo_briefing(project_id, db)

        logger.info(
            "COO pipeline: completed for project %s.",
            project_id,
        )

    except Exception as exc:
        logger.warning(
            "COO summarization pipeline error (non-fatal) for project %s: %s",
            project_id,
            exc,
        )
