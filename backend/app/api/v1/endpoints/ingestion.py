"""
Data ingestion endpoints.

Handles file uploads (Slack JSON exports, Jira CSV exports, Google Drive
document dumps) and ingestion job lifecycle management. Files are validated
for type and size before being handed to the ingestion orchestrator.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: set[str] = {
    ".json",
    ".csv",
    ".xlsx",
    ".xls",
    ".zip",
    ".tar",
    ".gz",
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".doc",
    ".html",
    ".xml",
    ".eml",
}

ALLOWED_CONTENT_TYPES: set[str] = {
    "application/json",
    "text/csv",
    "text/plain",
    "text/markdown",
    "text/html",
    "text/xml",
    "application/xml",
    "application/pdf",
    "application/zip",
    "application/gzip",
    "application/x-tar",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",
    "message/rfc822",
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class IngestionJobStatus(str, Enum):
    """Status states for an ingestion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileInfo(BaseModel):
    """Metadata for a single uploaded file."""

    filename: str = Field(..., description="Original filename.")
    size_bytes: int = Field(..., description="File size in bytes.")
    content_type: str = Field(..., description="MIME content type.")


class IngestionJobResponse(BaseModel):
    """Response for a single ingestion job."""

    job_id: str = Field(..., description="Unique job identifier.")
    status: IngestionJobStatus = Field(..., description="Current job status.")
    files: list[FileInfo] = Field(default_factory=list, description="Files in this job.")
    total_files: int = Field(default=0, description="Number of files in the job.")
    files_processed: int = Field(default=0, description="Number of files processed so far.")
    error_message: str | None = Field(default=None, description="Error details if failed.")
    created_at: datetime = Field(..., description="Job creation timestamp.")
    updated_at: datetime = Field(..., description="Last status update timestamp.")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp.")


class UploadResponse(BaseModel):
    """Response after successful file upload."""

    ingestion_job_id: str = Field(..., description="ID of the created ingestion job.")
    files_accepted: int = Field(..., description="Number of files accepted for processing.")
    total_size_bytes: int = Field(..., description="Total size of all accepted files.")
    message: str = Field(..., description="Human-readable status message.")


class IngestionJobListResponse(BaseModel):
    """Paginated list of ingestion jobs."""

    jobs: list[IngestionJobResponse] = Field(default_factory=list, description="List of jobs.")
    total: int = Field(default=0, description="Total number of jobs.")
    skip: int = Field(default=0, description="Number of records skipped.")
    limit: int = Field(default=20, description="Page size.")


class DeleteJobResponse(BaseModel):
    """Response after deleting/cancelling a job."""

    job_id: str = Field(..., description="ID of the affected job.")
    status: str = Field(..., description="New status of the job.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_file_extension(filename: str) -> bool:
    """Check if the file extension is in the allowed set."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    """Return the ingestion_jobs collection."""
    return db["ingestion_jobs"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload files for ingestion",
    description="Upload one or more files for data extraction and analysis. "
    "Files are validated for type and size before processing begins.",
)
async def upload_files(
    files: list[UploadFile] = File(..., description="Files to ingest."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> UploadResponse:
    settings = get_settings()

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Validate each file
    accepted_files: list[FileInfo] = []
    file_contents: list[bytes] = []
    total_size = 0

    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="A file is missing a filename.")

        if not _validate_file_extension(upload.filename):
            raise HTTPException(
                status_code=422,
                detail=f"File type not allowed: '{upload.filename}'. "
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        content = await upload.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=422,
                detail=f"File '{upload.filename}' is empty.",
            )

        if file_size > settings.upload_max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload.filename}' exceeds maximum size of "
                f"{settings.UPLOAD_MAX_FILE_SIZE_MB} MB.",
            )

        total_size += file_size
        if total_size > settings.upload_max_batch_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Total batch size exceeds maximum of "
                f"{settings.UPLOAD_MAX_BATCH_SIZE_MB} MB.",
            )

        accepted_files.append(
            FileInfo(
                filename=upload.filename,
                size_bytes=file_size,
                content_type=upload.content_type or "application/octet-stream",
            )
        )
        file_contents.append(content)

    # Create the ingestion job record
    now = utc_now()
    job_id = generate_uuid()
    job_doc = {
        "job_id": job_id,
        "status": IngestionJobStatus.PENDING.value,
        "files": [f.model_dump() for f in accepted_files],
        "total_files": len(accepted_files),
        "files_processed": 0,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }

    collection = _get_collection(db)
    await collection.insert_one(job_doc)

    # Store raw file data for the orchestrator to pick up
    file_store = db["ingestion_file_store"]
    for file_info, content in zip(accepted_files, file_contents, strict=False):
        await file_store.insert_one(
            {
                "job_id": job_id,
                "filename": file_info.filename,
                "content_type": file_info.content_type,
                "data": content,
                "created_at": now,
            }
        )

    # Trigger the ingestion orchestrator asynchronously
    try:
        from app.services.ingestion.orchestrator import start_ingestion_job

        await start_ingestion_job(job_id)
    except ImportError:
        logger.warning(
            "Ingestion orchestrator not yet implemented; job created but not started.",
            extra={"job_id": job_id},
        )
    except Exception as exc:
        logger.error(
            "Failed to start ingestion job",
            extra={"job_id": job_id},
            exc_info=exc,
        )
        await collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": IngestionJobStatus.FAILED.value,
                    "error_message": str(exc),
                    "updated_at": utc_now(),
                }
            },
        )
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {exc}")

    return UploadResponse(
        ingestion_job_id=job_id,
        files_accepted=len(accepted_files),
        total_size_bytes=total_size,
        message=f"Ingestion job created with {len(accepted_files)} file(s).",
    )


@router.get(
    "/jobs",
    response_model=IngestionJobListResponse,
    summary="List ingestion jobs",
    description="Retrieve a paginated list of all ingestion jobs ordered by creation time.",
)
async def list_jobs(
    skip: int = Query(default=0, ge=0, description="Number of records to skip."),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return."),
    status: IngestionJobStatus | None = Query(default=None, description="Filter by status."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> IngestionJobListResponse:
    collection = _get_collection(db)

    query: dict = {}
    if status is not None:
        query["status"] = status.value

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    jobs = [IngestionJobResponse(**doc) for doc in docs]

    return IngestionJobListResponse(jobs=jobs, total=total, skip=skip, limit=limit)


@router.get(
    "/jobs/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get ingestion job detail",
    description="Retrieve the full details of a single ingestion job.",
)
async def get_job(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> IngestionJobResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"job_id": job_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Ingestion job '{job_id}' not found.")

    return IngestionJobResponse(**doc)


@router.delete(
    "/jobs/{job_id}",
    response_model=DeleteJobResponse,
    summary="Cancel or delete an ingestion job",
    description="Cancel a running job or delete a completed/failed job record.",
)
async def delete_job(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DeleteJobResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"job_id": job_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Ingestion job '{job_id}' not found.")

    current_status = doc.get("status", "")

    if current_status in (
        IngestionJobStatus.PENDING.value,
        IngestionJobStatus.PROCESSING.value,
        IngestionJobStatus.EXTRACTING.value,
        IngestionJobStatus.ANALYZING.value,
    ):
        # Cancel running/pending job
        await collection.update_one(
            {"job_id": job_id},
            {"$set": {"status": IngestionJobStatus.CANCELLED.value, "updated_at": utc_now()}},
        )

        try:
            from app.services.ingestion.orchestrator import cancel_ingestion_job

            await cancel_ingestion_job(job_id)
        except (ImportError, Exception) as exc:
            logger.warning(
                "Could not signal orchestrator to cancel job",
                extra={"job_id": job_id},
                exc_info=exc,
            )

        return DeleteJobResponse(
            job_id=job_id,
            status=IngestionJobStatus.CANCELLED.value,
            message="Ingestion job has been cancelled.",
        )

    # For completed/failed/cancelled jobs, remove entirely
    await collection.delete_one({"job_id": job_id})

    # Clean up stored file data
    file_store = db["ingestion_file_store"]
    await file_store.delete_many({"job_id": job_id})

    return DeleteJobResponse(
        job_id=job_id,
        status="deleted",
        message="Ingestion job record has been deleted.",
    )
