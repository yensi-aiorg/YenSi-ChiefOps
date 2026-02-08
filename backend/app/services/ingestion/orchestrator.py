"""
Main ingestion coordinator.

Receives uploaded files, detects their types, dispatches to the correct
parser, tracks progress per file, and after all files are processed
triggers the people pipeline and project analysis.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now
from app.services.ingestion.detector import FileType, detect_file_type
from app.services.ingestion.drive import process_drive_files
from app.services.ingestion.jira_csv import parse_jira_csv
from app.services.ingestion.slack_admin import IngestionFileResult, parse_slack_admin_export
from app.services.ingestion.slack_api import parse_slack_api_extract

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class IngestionJob:
    """Tracks the overall status of a batch ingestion job."""

    __slots__ = (
        "completed_at",
        "errors",
        "file_results",
        "job_id",
        "processed_files",
        "started_at",
        "status",
        "total_files",
    )

    def __init__(self, total_files: int) -> None:
        self.job_id: str = generate_uuid()
        self.status: str = "processing"
        self.total_files: int = total_files
        self.processed_files: int = 0
        self.file_results: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.started_at: datetime = datetime.now(UTC)
        self.completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "file_results": self.file_results,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


async def process_upload(
    files: list[dict[str, Any]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> IngestionJob:
    """Process a batch of uploaded files through the ingestion pipeline.

    Each file dict must contain:
    - ``filename``: Original filename.
    - ``content``: Raw bytes of the file.

    After all files are processed, triggers the people pipeline and
    project analysis.

    Args:
        files: List of file dicts with ``filename`` and ``content`` keys.
        db: Motor database handle.

    Returns:
        An ``IngestionJob`` with per-file results and overall status.
    """
    job = IngestionJob(total_files=len(files))

    # Persist job record to MongoDB
    await db.ingestion_jobs.insert_one(
        {
            "job_id": job.job_id,
            "status": "processing",
            "total_files": job.total_files,
            "processed_files": 0,
            "file_results": [],
            "errors": [],
            "started_at": job.started_at,
            "completed_at": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    )

    logger.info("Starting ingestion job %s with %d files", job.job_id, len(files))

    drive_files: list[str] = []
    has_failures = False

    for file_info in files:
        filename = file_info.get("filename", "unknown")
        content = file_info.get("content", b"")

        if not content:
            result = IngestionFileResult(filename=filename, file_type="unknown")
            result.status = "failed"
            result.errors.append("File content is empty")
            job.file_results.append(result.to_dict())
            job.processed_files += 1
            has_failures = True
            await _update_job_progress(job, db)
            continue

        try:
            file_type = detect_file_type(filename, content)
            logger.info("Detected file type for '%s': %s", filename, file_type.value)

            file_result = await _dispatch_file(
                filename=filename,
                content=content,
                file_type=file_type,
                db=db,
                drive_files=drive_files,
            )

            if file_result is not None:
                job.file_results.append(file_result.to_dict())
                if file_result.status == "failed":
                    has_failures = True

        except Exception as exc:
            logger.exception("Error processing file '%s'", filename)
            error_result = IngestionFileResult(filename=filename, file_type="unknown")
            error_result.status = "failed"
            error_result.errors.append(f"Unexpected error: {exc}")
            job.file_results.append(error_result.to_dict())
            has_failures = True

        job.processed_files += 1
        await _update_job_progress(job, db)

    # Process any accumulated drive files
    if drive_files:
        try:
            drive_results = await process_drive_files(drive_files, db)
            for dr in drive_results:
                job.file_results.append(dr.to_dict())
                if dr.status == "failed":
                    has_failures = True
        except Exception as exc:
            logger.exception("Error processing drive files batch")
            job.errors.append(f"Drive files batch error: {exc}")
            has_failures = True
        finally:
            # Clean up temp files
            for fp in drive_files:
                with contextlib.suppress(OSError):
                    os.unlink(fp)

    # Trigger post-ingestion pipelines
    await _run_post_ingestion(db, job)

    # Finalise job status
    job.completed_at = datetime.now(UTC)
    job.status = "completed_with_errors" if has_failures else "completed"

    await db.ingestion_jobs.update_one(
        {"job_id": job.job_id},
        {
            "$set": {
                "status": job.status,
                "processed_files": job.processed_files,
                "file_results": job.file_results,
                "errors": job.errors,
                "completed_at": job.completed_at,
                "updated_at": utc_now(),
            }
        },
    )

    logger.info(
        "Ingestion job %s %s: %d files processed",
        job.job_id,
        job.status,
        job.processed_files,
    )
    return job


async def _dispatch_file(
    filename: str,
    content: bytes,
    file_type: FileType,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    drive_files: list[str],
) -> IngestionFileResult | None:
    """Route a file to the appropriate parser based on detected type.

    ZIP and CSV files are written to temporary files for parser consumption.
    Drive documents are accumulated in the ``drive_files`` list for batch
    processing later.

    Returns:
        An ``IngestionFileResult`` for ZIP/CSV types, or None for drive
        documents (which are batch-processed later).
    """
    if file_type == FileType.SLACK_ADMIN_EXPORT:
        tmp_path = _write_temp_file(content, suffix=".zip")
        try:
            return await parse_slack_admin_export(tmp_path, db)
        finally:
            _safe_unlink(tmp_path)

    if file_type == FileType.SLACK_API_EXTRACT:
        tmp_path = _write_temp_file(content, suffix=".zip")
        try:
            return await parse_slack_api_extract(tmp_path, db)
        finally:
            _safe_unlink(tmp_path)

    if file_type == FileType.JIRA_CSV:
        tmp_path = _write_temp_file(content, suffix=".csv")
        try:
            return await parse_jira_csv(tmp_path, db)
        finally:
            _safe_unlink(tmp_path)

    if file_type in (FileType.DRIVE_DOCUMENT, FileType.UNKNOWN):
        # Determine suffix from filename
        _, ext = os.path.splitext(filename)
        tmp_path = _write_temp_file(content, suffix=ext or ".bin")
        drive_files.append(tmp_path)
        return None

    # Fallback for any unhandled type
    result = IngestionFileResult(filename=filename, file_type=file_type.value)
    result.status = "skipped"
    result.errors.append(f"No parser available for file type: {file_type.value}")
    return result


async def _run_post_ingestion(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    job: IngestionJob,
) -> None:
    """Run post-ingestion pipelines: people identification and project analysis.

    Each pipeline is wrapped in try/except so failures in one pipeline
    do not prevent the other from running.
    """
    # People pipeline
    try:
        from app.services.people.pipeline import run_pipeline

        await run_pipeline(db, ai_adapter=None)
        logger.info("People pipeline completed for job %s", job.job_id)
    except ImportError:
        logger.warning("People pipeline module not available")
    except Exception as exc:
        logger.exception("People pipeline failed for job %s", job.job_id)
        job.errors.append(f"People pipeline error: {exc}")

    # Project analysis
    try:
        from app.services.projects.analyzer import analyze_all_projects

        await analyze_all_projects(db, ai_adapter=None)
        logger.info("Project analysis completed for job %s", job.job_id)
    except ImportError:
        logger.warning("Project analyzer module not available")
    except Exception as exc:
        logger.exception("Project analysis failed for job %s", job.job_id)
        job.errors.append(f"Project analysis error: {exc}")


async def _update_job_progress(
    job: IngestionJob,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Persist current job progress to MongoDB."""
    await db.ingestion_jobs.update_one(
        {"job_id": job.job_id},
        {
            "$set": {
                "processed_files": job.processed_files,
                "file_results": job.file_results,
                "errors": job.errors,
                "updated_at": utc_now(),
            }
        },
    )


def _write_temp_file(content: bytes, suffix: str = "") -> str:
    """Write content to a temporary file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="chiefops_ingest_")
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    return path


def _safe_unlink(path: str) -> None:
    """Delete a file, ignoring errors."""
    with contextlib.suppress(OSError):
        os.unlink(path)
