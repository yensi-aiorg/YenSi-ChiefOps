"""COO summarization pipeline orchestrator.

Runs after a project file upload job completes. For each successfully
processed file, spawns a parallel summarization task, then aggregates
all summaries into a single COO briefing.
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


async def run_coo_summarization_pipeline(
    *,
    project_id: str,
    file_results: list[dict[str, Any]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Run the full COO summarization pipeline.

    1. For each completed file, look up its extracted text and summarize in parallel.
    2. After all summaries finish, generate the aggregated COO briefing.

    **Never propagates exceptions** to the caller.
    """
    try:
        # Filter to completed files only
        completed = [r for r in file_results if r.get("status") == "completed"]
        if not completed:
            logger.info(
                "COO pipeline: no completed files for project %s, skipping.",
                project_id,
            )
            return

        # Build coroutines for parallel summarization
        tasks: list[asyncio.Task[dict[str, Any]]] = []
        for result in completed:
            file_id = result.get("file_id", "")
            filename = result.get("filename", "unknown")
            file_type = result.get("file_type", "documentation")

            if not file_id:
                continue

            # Look up extracted text from text_documents
            text_doc = await db.text_documents.find_one(
                {"file_id": file_id},
                {"_id": 0, "content": 1, "text": 1, "extracted_text": 1},
            )

            if not text_doc:
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

            if not text_doc:
                logger.warning(
                    "COO pipeline: no text found for file %s/%s, skipping.",
                    project_id,
                    filename,
                )
                continue

            # text_documents may store content under different field names
            text_content = (
                text_doc.get("content")
                or text_doc.get("text")
                or text_doc.get("extracted_text")
                or ""
            )

            if not text_content.strip():
                logger.warning(
                    "COO pipeline: empty text for file %s/%s, skipping.",
                    project_id,
                    filename,
                )
                continue

            tasks.append(
                asyncio.create_task(
                    summarize_file(
                        project_id=project_id,
                        file_id=file_id,
                        filename=filename,
                        file_type=file_type,
                        text_content=text_content,
                        db=db,
                    )
                )
            )

        if not tasks:
            logger.info(
                "COO pipeline: no files with text content for project %s.",
                project_id,
            )
            return

        logger.info(
            "COO pipeline: summarizing %d files in parallel for project %s.",
            len(tasks),
            project_id,
        )

        # Run all summarizations in parallel — failures are caught per-file
        await asyncio.gather(*tasks, return_exceptions=True)

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
