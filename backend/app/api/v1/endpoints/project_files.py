"""
Per-project file upload, listing, and deletion endpoints.

Allows uploading files (Slack JSON, Jira XLSX, PDF, DOCX, MD, TXT) scoped
to a specific project. Uploads are queued and processed in background,
producing ``text_documents`` entries tagged with ``project_id``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import get_database, get_database_sync
from app.models.base import generate_uuid, utc_now
from app.services.ingestion.project_files import (
    ALLOWED_EXTENSIONS,
    process_project_file,
    process_project_note,
    retry_project_file_citex_index,
)

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/files", tags=["project-files"])
_upload_background_tasks: set[asyncio.Task] = set()  # type: ignore[type-arg]
_upload_tasks_by_job_id: dict[str, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ProjectFileResult(BaseModel):
    """Result for a single file processed during upload."""

    file_id: str = Field(..., description="Unique file identifier.")
    filename: str = Field(..., description="Original filename.")
    file_type: str = Field(..., description="Detected file type category.")
    status: str = Field(..., description="Processing status: completed, failed, or skipped.")
    records_created: int = Field(default=0, description="Number of records created.")
    citex_ingested: bool = Field(default=False, description="Whether content was ingested into Citex.")
    error_message: str | None = Field(default=None, description="Error details if failed or skipped.")


class ProjectFilesUploadResponse(BaseModel):
    """Aggregated response after uploading one or more files to a project."""

    project_id: str = Field(..., description="Target project ID.")
    files_processed: int = Field(default=0, description="Total files processed.")
    files_succeeded: int = Field(default=0, description="Files successfully processed.")
    files_failed: int = Field(default=0, description="Files that failed processing.")
    results: list[ProjectFileResult] = Field(default_factory=list, description="Per-file results.")


class ProjectFilesUploadTriggerResponse(BaseModel):
    """Response returned immediately after upload job is queued."""

    project_id: str = Field(..., description="Target project ID.")
    job_id: str = Field(..., description="Background upload job identifier.")
    status: str = Field(..., description="Job status.")
    message: str = Field(..., description="Human-readable status message.")


class ProjectFilesUploadJobResponse(BaseModel):
    """Status payload for a background project-file upload job."""

    project_id: str = Field(..., description="Target project ID.")
    job_id: str = Field(..., description="Background upload job identifier.")
    status: str = Field(..., description="Job status: pending, processing, completed, failed, cancelled.")
    files_processed: int = Field(default=0, description="Total files processed.")
    files_succeeded: int = Field(default=0, description="Files successfully processed.")
    files_failed: int = Field(default=0, description="Files that failed processing.")
    results: list[ProjectFileResult] = Field(default_factory=list, description="Per-file results.")
    error_message: str | None = Field(default=None, description="Error details when failed.")
    created_at: datetime = Field(..., description="Job creation timestamp.")
    updated_at: datetime = Field(..., description="Last status update timestamp.")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp.")


class ProjectFileInfo(BaseModel):
    """Metadata for a file uploaded to a project."""

    file_id: str = Field(..., description="Unique file identifier.")
    filename: str = Field(..., description="Original filename.")
    file_type: str = Field(..., description="Detected file type category.")
    content_type: str = Field(..., description="MIME content type.")
    file_size: int = Field(..., description="File size in bytes.")
    status: str = Field(..., description="Processing status.")
    citex_ingested: bool = Field(default=False, description="Whether content is in Citex.")
    error_message: str | None = Field(default=None, description="Error details if any.")
    created_at: datetime = Field(..., description="Upload timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class ProjectFileListResponse(BaseModel):
    """Paginated list of files uploaded to a project."""

    files: list[ProjectFileInfo] = Field(default_factory=list, description="List of files.")
    total: int = Field(default=0, description="Total number of files.")
    skip: int = Field(default=0, description="Number of records skipped.")
    limit: int = Field(default=20, description="Page size.")


class DeleteFileResponse(BaseModel):
    """Response after deleting a project file."""

    file_id: str = Field(..., description="Deleted file ID.")
    message: str = Field(..., description="Human-readable status message.")


class RetryIndexResponse(BaseModel):
    """Response after retrying Citex indexing for a project file."""

    file_id: str = Field(..., description="File identifier.")
    status: str = Field(..., description="Retry status.")
    message: str = Field(..., description="Human-readable result message.")
    citex_ingested: bool = Field(..., description="Whether the file is now indexed in Citex.")
    job_id: str | None = Field(default=None, description="Citex ingestion job id when available.")


class CancelUploadJobResponse(BaseModel):
    """Response after cancelling an upload/processing job."""

    project_id: str = Field(..., description="Target project ID.")
    job_id: str = Field(..., description="Background upload job identifier.")
    status: str = Field(..., description="Updated status after cancellation request.")
    message: str = Field(..., description="Human-readable status message.")


class ProjectNoteRequest(BaseModel):
    """Request body for pasted project notes."""

    title: str = Field(default="Project Note", max_length=300, description="Optional note title.")
    content: str = Field(..., min_length=1, max_length=100_000, description="Narrative note text.")


class ProjectNoteResponse(BaseModel):
    """Response after processing a project note."""

    project_id: str = Field(..., description="Project identifier.")
    status: str = Field(..., description="Processing status.")
    document_id: str | None = Field(default=None, description="Stored text document id.")
    insights_created: int = Field(default=0, description="Number of semantic insights extracted.")
    error_message: str | None = Field(default=None, description="Error message when failed.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_extension(filename: str) -> bool:
    """Check if the file extension is allowed for per-project upload."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Background upload runner
# ---------------------------------------------------------------------------


async def _process_one_file(
    *,
    project_id: str,
    filename: str,
    content: bytes,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    settings: object,
) -> tuple[dict, asyncio.Task | None]:
    """Validate and process a single file. Returns (result, optional_summary_task).

    Runs independently so multiple files can be processed in parallel via
    ``asyncio.gather``.
    """
    # --- quick validation (no I/O) ---
    if not filename:
        return (
            {
                "file_id": "",
                "filename": "(unnamed)",
                "file_type": "unknown",
                "status": "failed",
                "records_created": 0,
                "citex_ingested": False,
                "error_message": "File is missing a filename.",
            },
            None,
        )

    if not _validate_extension(filename):
        return (
            {
                "file_id": "",
                "filename": filename,
                "file_type": "unknown",
                "status": "failed",
                "records_created": 0,
                "citex_ingested": False,
                "error_message": (
                    "File type not allowed. Supported: "
                    + ", ".join(sorted(ALLOWED_EXTENSIONS))
                ),
            },
            None,
        )

    if len(content) == 0:
        return (
            {
                "file_id": "",
                "filename": filename,
                "file_type": "unknown",
                "status": "failed",
                "records_created": 0,
                "citex_ingested": False,
                "error_message": "File is empty.",
            },
            None,
        )

    if len(content) > settings.upload_max_file_size_bytes:  # type: ignore[attr-defined]
        return (
            {
                "file_id": "",
                "filename": filename,
                "file_type": "unknown",
                "status": "failed",
                "records_created": 0,
                "citex_ingested": False,
                "error_message": (
                    f"File exceeds maximum size of {settings.UPLOAD_MAX_FILE_SIZE_MB} MB."  # type: ignore[attr-defined]
                ),
            },
            None,
        )

    # --- actual processing (text extraction + semantic insights + Citex) ---
    logger.info("Parallel upload: starting process_project_file for %s/%s", project_id, filename)
    result = await process_project_file(
        project_id=project_id,
        filename=filename,
        content=content,
        db=db,
    )
    logger.info("Parallel upload: finished process_project_file for %s/%s → %s", project_id, filename, result.get("status"))

    # Fire COO summarization immediately (runs concurrently)
    summary_task: asyncio.Task | None = None
    if result.get("status") == "completed" and result.get("file_id"):
        try:
            from app.services.summarization.pipeline import start_file_summarization

            summary_task = start_file_summarization(
                project_id=project_id,
                file_id=result["file_id"],
                filename=result.get("filename", filename),
                file_type=result.get("file_type", "documentation"),
                db=db,
            )
        except Exception as exc:
            logger.warning("COO file summarization start error (non-fatal): %s", exc)

    return (result, summary_task)


async def _run_project_files_upload_background(
    *,
    job_id: str,
    project_id: str,
    files_payload: list[tuple[str, bytes]],
) -> None:
    """Process uploaded files **in parallel** and update job status."""
    db = get_database_sync()
    jobs = db["project_file_upload_jobs"]
    settings = get_settings()

    existing_job = await jobs.find_one({"job_id": job_id, "project_id": project_id}, {"status": 1, "_id": 0})
    if str((existing_job or {}).get("status", "")).lower() == "cancelled":
        return

    await jobs.update_one(
        {"job_id": job_id, "project_id": project_id, "status": {"$ne": "cancelled"}},
        {"$set": {"status": "processing", "updated_at": utc_now()}},
    )

    results: list[dict] = []
    succeeded = 0
    failed = 0
    summary_tasks: list[asyncio.Task] = []

    try:
        logger.info(
            "Parallel upload: launching %d files concurrently for project %s",
            len(files_payload),
            project_id,
        )

        # --- process ALL files in parallel ---
        outcomes = await asyncio.gather(
            *[
                _process_one_file(
                    project_id=project_id,
                    filename=fn,
                    content=ct,
                    db=db,
                    settings=settings,
                )
                for fn, ct in files_payload
            ],
            return_exceptions=True,
        )

        # --- collect results ---
        for i, outcome in enumerate(outcomes):
            if isinstance(outcome, BaseException):
                fn = files_payload[i][0] or "(unnamed)"
                logger.warning("Parallel upload: file %s raised exception: %s", fn, outcome)
                result = {
                    "file_id": "",
                    "filename": fn,
                    "file_type": "unknown",
                    "status": "failed",
                    "records_created": 0,
                    "citex_ingested": False,
                    "error_message": str(outcome)[:500],
                }
                results.append(result)
                failed += 1
            else:
                result, task = outcome
                results.append(result)
                if result.get("status") == "completed":
                    succeeded += 1
                elif result.get("status") == "failed":
                    failed += 1
                if task is not None:
                    summary_tasks.append(task)

        logger.info(
            "Parallel upload: all %d files done for project %s (succeeded=%d, failed=%d)",
            len(files_payload),
            project_id,
            succeeded,
            failed,
        )

        await jobs.update_one(
            {"job_id": job_id, "project_id": project_id, "status": {"$ne": "cancelled"}},
            {
                "$set": {
                    "status": "completed",
                    "updated_at": utc_now(),
                    "completed_at": utc_now(),
                    "files_processed": len(results),
                    "files_succeeded": succeeded,
                    "files_failed": failed,
                    "results": results,
                }
            },
        )

        # Finalize COO briefing: await remaining summaries + generate aggregation
        if summary_tasks:
            try:
                from app.services.summarization.pipeline import finalize_coo_briefing

                asyncio.create_task(
                    finalize_coo_briefing(
                        project_id=project_id,
                        summary_tasks=summary_tasks,
                        db=db,
                    )
                )
            except Exception as exc:
                logger.warning("COO briefing finalization error (non-fatal): %s", exc)

    except asyncio.CancelledError:
        await jobs.update_one(
            {"job_id": job_id, "project_id": project_id},
            {
                "$set": {
                    "status": "cancelled",
                    "error_message": "Upload cancelled by user.",
                    "updated_at": utc_now(),
                    "completed_at": utc_now(),
                    "files_processed": len(results),
                    "files_succeeded": succeeded,
                    "files_failed": failed,
                    "results": results,
                }
            },
        )
        raise
    except Exception as exc:
        logger.exception("Project file upload job failed: %s", exc)
        await jobs.update_one(
            {"job_id": job_id, "project_id": project_id, "status": {"$ne": "cancelled"}},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(exc),
                    "updated_at": utc_now(),
                    "completed_at": utc_now(),
                    "files_processed": len(results),
                    "files_succeeded": succeeded,
                    "files_failed": failed,
                    "results": results,
                }
            },
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=ProjectFilesUploadTriggerResponse,
    status_code=202,
    summary="Upload files to a project",
    description="Upload one or more files scoped to a specific project. "
    "Supported formats: JSON (Slack), XLSX (Jira), PDF, DOCX, MD, TXT. "
    "Returns a background job id; poll upload-jobs endpoint for completion.",
)
async def upload_project_files(
    project_id: str,
    files: list[UploadFile] = File(..., description="Files to upload."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectFilesUploadTriggerResponse:
    # Validate project exists
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    files_payload: list[tuple[str, bytes]] = []

    for upload in files:
        files_payload.append((upload.filename or "", await upload.read()))

    now = utc_now()
    job_id = generate_uuid()
    await db["project_file_upload_jobs"].insert_one(
        {
            "job_id": job_id,
            "project_id": project_id,
            "status": "pending",
            "files_processed": 0,
            "files_succeeded": 0,
            "files_failed": 0,
            "results": [],
            "error_message": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
    )

    task = asyncio.create_task(
        _run_project_files_upload_background(
            job_id=job_id,
            project_id=project_id,
            files_payload=files_payload,
        )
    )
    _upload_background_tasks.add(task)
    _upload_tasks_by_job_id[job_id] = task

    def _cleanup_upload_task(done_task: asyncio.Task) -> None:
        _upload_background_tasks.discard(done_task)
        _upload_tasks_by_job_id.pop(job_id, None)

    task.add_done_callback(_cleanup_upload_task)

    return ProjectFilesUploadTriggerResponse(
        project_id=project_id,
        job_id=job_id,
        status="pending",
        message="Project file upload has been queued.",
    )


@router.get(
    "/upload-jobs/{job_id}",
    response_model=ProjectFilesUploadJobResponse,
    summary="Poll project file upload job",
    description="Check status/results of a background project file upload job.",
)
async def get_project_file_upload_job(
    project_id: str,
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectFilesUploadJobResponse:
    doc = await db["project_file_upload_jobs"].find_one(
        {"job_id": job_id, "project_id": project_id},
        {"_id": 0},
    )
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Upload job '{job_id}' not found.")
    return ProjectFilesUploadJobResponse(**doc)


@router.post(
    "/upload-jobs/{job_id}/cancel",
    response_model=CancelUploadJobResponse,
    summary="Cancel project file upload job",
    description="Cancel an in-flight upload/processing job and stop polling.",
)
async def cancel_project_file_upload_job(
    project_id: str,
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> CancelUploadJobResponse:
    doc = await db["project_file_upload_jobs"].find_one(
        {"job_id": job_id, "project_id": project_id},
        {"_id": 0, "status": 1},
    )
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Upload job '{job_id}' not found.")

    current_status = str(doc.get("status", "pending")).lower()
    if current_status in {"completed", "failed", "cancelled"}:
        return CancelUploadJobResponse(
            project_id=project_id,
            job_id=job_id,
            status=current_status,
            message=f"Job is already {current_status}.",
        )

    await db["project_file_upload_jobs"].update_one(
        {"job_id": job_id, "project_id": project_id},
        {"$set": {"status": "cancelled", "error_message": "Upload cancelled by user.", "updated_at": utc_now(), "completed_at": utc_now()}},
    )

    task = _upload_tasks_by_job_id.get(job_id)
    if task is not None and not task.done():
        task.cancel()

    return CancelUploadJobResponse(
        project_id=project_id,
        job_id=job_id,
        status="cancelled",
        message="Upload cancellation requested.",
    )


@router.post(
    "/notes",
    response_model=ProjectNoteResponse,
    summary="Submit project note text",
    description="Submit free-form narrative text (meeting notes, decisions, direction changes). "
    "The system stores the note and extracts semantic operational insights.",
)
async def submit_project_note(
    project_id: str,
    body: ProjectNoteRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectNoteResponse:
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    result = await process_project_note(
        project_id=project_id,
        title=body.title,
        content=body.content,
        db=db,
    )
    return ProjectNoteResponse(
        project_id=project_id,
        status=result.get("status", "failed"),
        document_id=result.get("document_id"),
        insights_created=int(result.get("insights_created", 0)),
        error_message=result.get("error_message"),
    )


@router.get(
    "",
    response_model=ProjectFileListResponse,
    summary="List project files",
    description="Retrieve a paginated list of files uploaded to a project.",
)
async def list_project_files(
    project_id: str,
    skip: int = Query(default=0, ge=0, description="Number of records to skip."),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectFileListResponse:
    query = {"project_id": project_id}

    total = await db.project_files.count_documents(query)
    cursor = (
        db.project_files.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    files = [ProjectFileInfo(**doc) for doc in docs]

    return ProjectFileListResponse(files=files, total=total, skip=skip, limit=limit)


@router.delete(
    "/{file_id}",
    response_model=DeleteFileResponse,
    summary="Delete a project file",
    description="Delete a file record and its associated text_document.",
)
async def delete_project_file(
    project_id: str,
    file_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DeleteFileResponse:
    file_doc = await db.project_files.find_one(
        {"file_id": file_id, "project_id": project_id}
    )

    if not file_doc:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_id}' not found in project '{project_id}'.",
        )

    # Delete associated text_document if it exists
    text_doc_id = file_doc.get("text_document_id")
    if text_doc_id:
        await db.text_documents.delete_one({"document_id": text_doc_id})

    # Delete the file record
    await db.project_files.delete_one({"file_id": file_id, "project_id": project_id})

    return DeleteFileResponse(
        file_id=file_id,
        message=f"File '{file_doc.get('filename', file_id)}' deleted successfully.",
    )


@router.post(
    "/{file_id}/retry-index",
    response_model=RetryIndexResponse,
    summary="Retry Citex indexing",
    description="Retry sending an already-uploaded file's extracted content to Citex for indexing.",
)
async def retry_project_file_index(
    project_id: str,
    file_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> RetryIndexResponse:
    project = await db.projects.find_one({"project_id": project_id}, {"_id": 0, "project_id": 1})
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    result = await retry_project_file_citex_index(
        project_id=project_id,
        file_id=file_id,
        db=db,
    )
    return RetryIndexResponse(file_id=file_id, **result)
