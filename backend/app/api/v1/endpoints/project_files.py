"""
Per-project file upload, listing, and deletion endpoints.

Allows uploading files (Slack JSON, Jira XLSX, PDF, DOCX, MD, TXT) scoped
to a specific project. Files are processed synchronously, producing
``text_documents`` entries tagged with ``project_id``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import get_database
from app.services.ingestion.project_files import (
    ALLOWED_EXTENSIONS,
    process_project_file,
    process_project_note,
)

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/files", tags=["project-files"])


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
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=ProjectFilesUploadResponse,
    status_code=201,
    summary="Upload files to a project",
    description="Upload one or more files scoped to a specific project. "
    "Supported formats: JSON (Slack), XLSX (Jira), PDF, DOCX, MD, TXT.",
)
async def upload_project_files(
    project_id: str,
    files: list[UploadFile] = File(..., description="Files to upload."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectFilesUploadResponse:
    # Validate project exists
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    settings = get_settings()
    results: list[ProjectFileResult] = []
    succeeded = 0
    failed = 0

    for upload in files:
        if not upload.filename:
            results.append(
                ProjectFileResult(
                    file_id="",
                    filename="(unnamed)",
                    file_type="unknown",
                    status="failed",
                    error_message="File is missing a filename.",
                )
            )
            failed += 1
            continue

        if not _validate_extension(upload.filename):
            results.append(
                ProjectFileResult(
                    file_id="",
                    filename=upload.filename,
                    file_type="unknown",
                    status="failed",
                    error_message=f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )
            )
            failed += 1
            continue

        content = await upload.read()

        if len(content) == 0:
            results.append(
                ProjectFileResult(
                    file_id="",
                    filename=upload.filename,
                    file_type="unknown",
                    status="failed",
                    error_message="File is empty.",
                )
            )
            failed += 1
            continue

        if len(content) > settings.upload_max_file_size_bytes:
            results.append(
                ProjectFileResult(
                    file_id="",
                    filename=upload.filename,
                    file_type="unknown",
                    status="failed",
                    error_message=f"File exceeds maximum size of {settings.UPLOAD_MAX_FILE_SIZE_MB} MB.",
                )
            )
            failed += 1
            continue

        # Process the file
        result = await process_project_file(
            project_id=project_id,
            filename=upload.filename,
            content=content,
            db=db,
        )

        file_result = ProjectFileResult(**result)
        results.append(file_result)

        if file_result.status == "completed":
            succeeded += 1
        elif file_result.status == "failed":
            failed += 1
        # "skipped" counts as neither succeeded nor failed

    return ProjectFilesUploadResponse(
        project_id=project_id,
        files_processed=len(results),
        files_succeeded=succeeded,
        files_failed=failed,
        results=results,
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
