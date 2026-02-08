"""
Report generation and management endpoints.

Reports are AI-generated documents (project status, team performance,
executive summaries, etc.) produced from natural language requests.
Supports generation, listing, NL editing, PDF export, and deletion.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReportStatus(str, Enum):
    """Report generation lifecycle."""

    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class ReportSection(BaseModel):
    """A single section within a report."""

    title: str = Field(..., description="Section heading.")
    content: str = Field(..., description="Section body (Markdown).")
    order: int = Field(default=0, ge=0, description="Display order.")
    charts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Embedded chart specifications for this section.",
    )


class ReportGenerateRequest(BaseModel):
    """Request to generate a report from natural language."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language description of the desired report.",
    )
    project_id: str | None = Field(
        default=None,
        description="Scope the report to a specific project.",
    )


class ReportEditRequest(BaseModel):
    """Request to edit a report via natural language."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language edit instruction.",
    )


class ReportSpec(BaseModel):
    """Full report specification."""

    report_id: str = Field(..., description="Unique report identifier.")
    title: str = Field(..., description="Report title.")
    summary: str = Field(default="", description="Executive summary.")
    status: ReportStatus = Field(..., description="Generation status.")
    project_id: str | None = Field(default=None, description="Associated project ID.")
    sections: list[ReportSection] = Field(default_factory=list, description="Report sections.")
    generated_from: str = Field(default="", description="Original NL request.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class ReportSummary(BaseModel):
    """Lightweight report record for list views."""

    report_id: str = Field(..., description="Unique report identifier.")
    title: str = Field(..., description="Report title.")
    summary: str = Field(default="", description="Executive summary.")
    status: ReportStatus = Field(..., description="Generation status.")
    project_id: str | None = Field(default=None, description="Associated project.")
    section_count: int = Field(default=0, description="Number of sections.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class ReportListResponse(BaseModel):
    """Paginated list of reports."""

    reports: list[ReportSummary] = Field(default_factory=list, description="Reports list.")
    total: int = Field(default=0, description="Total matching reports.")
    skip: int = Field(default=0, description="Records skipped.")
    limit: int = Field(default=20, description="Page size.")


class DeleteReportResponse(BaseModel):
    """Response after deleting a report."""

    report_id: str = Field(..., description="Deleted report ID.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["reports"]


def _build_markdown(report: dict) -> str:
    """Convert a report document into Markdown text for PDF rendering."""
    lines: list[str] = []
    lines.append(f"# {report.get('title', 'Untitled Report')}")
    lines.append("")

    summary = report.get("summary", "")
    if summary:
        lines.append(f"_{summary}_")
        lines.append("")

    for section in report.get("sections", []):
        lines.append(f"## {section.get('title', 'Section')}")
        lines.append("")
        lines.append(section.get("content", ""))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=ReportSpec,
    status_code=201,
    summary="Generate report from natural language",
    description="Describe the report you want in plain English. The AI will "
    "generate a structured report with sections, charts, and insights.",
)
async def generate_report(
    body: ReportGenerateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ReportSpec:
    collection = _get_collection(db)

    now = utc_now()
    report_id = generate_uuid()

    try:
        from app.services.reports.service import ReportService

        service = ReportService(db)
        result = await service.generate(
            message=body.message,
            project_id=body.project_id,
        )

        report_doc = {
            "report_id": report_id,
            "title": result.get("title", "Generated Report"),
            "summary": result.get("summary", ""),
            "status": ReportStatus.READY.value,
            "project_id": body.project_id,
            "sections": result.get("sections", []),
            "generated_from": body.message,
            "metadata": result.get("metadata", {}),
            "created_at": now,
            "updated_at": now,
        }
    except ImportError:
        logger.warning("Report service not yet implemented; creating placeholder report.")
        report_doc = {
            "report_id": report_id,
            "title": f"Report: {body.message[:100]}",
            "summary": "This report was created as a placeholder. The report generation service is being initialized.",
            "status": ReportStatus.READY.value,
            "project_id": body.project_id,
            "sections": [
                {
                    "title": "Overview",
                    "content": f"Report requested: {body.message}",
                    "order": 0,
                    "charts": [],
                }
            ],
            "generated_from": body.message,
            "metadata": {"placeholder": True},
            "created_at": now,
            "updated_at": now,
        }
    except Exception as exc:
        logger.error("Report generation failed", exc_info=exc)
        report_doc = {
            "report_id": report_id,
            "title": f"Report: {body.message[:100]}",
            "summary": "",
            "status": ReportStatus.FAILED.value,
            "project_id": body.project_id,
            "sections": [],
            "generated_from": body.message,
            "metadata": {"error": str(exc)},
            "created_at": now,
            "updated_at": now,
        }

    await collection.insert_one(report_doc)

    # Remove _id for response
    report_doc.pop("_id", None)
    return ReportSpec(**report_doc)


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List reports",
    description="Retrieve a paginated list of all generated reports.",
)
async def list_reports(
    skip: int = Query(default=0, ge=0, description="Records to skip."),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return."),
    project_id: str | None = Query(default=None, description="Filter by project ID."),
    status: ReportStatus | None = Query(default=None, description="Filter by status."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ReportListResponse:
    collection = _get_collection(db)

    query: dict = {}
    if project_id is not None:
        query["project_id"] = project_id
    if status is not None:
        query["status"] = status.value

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    reports = []
    for doc in docs:
        reports.append(
            ReportSummary(
                report_id=doc["report_id"],
                title=doc["title"],
                summary=doc.get("summary", ""),
                status=doc["status"],
                project_id=doc.get("project_id"),
                section_count=len(doc.get("sections", [])),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
            )
        )

    return ReportListResponse(reports=reports, total=total, skip=skip, limit=limit)


@router.get(
    "/{report_id}",
    response_model=ReportSpec,
    summary="Get report",
    description="Retrieve the full specification of a single report.",
)
async def get_report(
    report_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ReportSpec:
    collection = _get_collection(db)
    doc = await collection.find_one({"report_id": report_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    return ReportSpec(**doc)


@router.patch(
    "/{report_id}/edit",
    response_model=ReportSpec,
    summary="Edit report via natural language",
    description="Send a natural language instruction to modify an existing report.",
)
async def edit_report(
    report_id: str,
    body: ReportEditRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ReportSpec:
    collection = _get_collection(db)
    doc = await collection.find_one({"report_id": report_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    try:
        from app.services.reports.service import ReportService

        service = ReportService(db)
        updated = await service.edit(
            report_id=report_id,
            current_report=doc,
            message=body.message,
        )

        update_fields = {
            "title": updated.get("title", doc["title"]),
            "summary": updated.get("summary", doc.get("summary", "")),
            "sections": updated.get("sections", doc.get("sections", [])),
            "updated_at": utc_now(),
        }

        await collection.update_one(
            {"report_id": report_id},
            {"$set": update_fields},
        )

        updated_doc = await collection.find_one({"report_id": report_id}, {"_id": 0})
        return ReportSpec(**updated_doc)
    except ImportError:
        logger.warning("Report service not yet implemented; appending edit note.")
        now = utc_now()
        current_sections = doc.get("sections", [])
        current_sections.append(
            {
                "title": "Edit Note",
                "content": f"Requested edit: {body.message}",
                "order": len(current_sections),
                "charts": [],
            }
        )

        await collection.update_one(
            {"report_id": report_id},
            {"$set": {"sections": current_sections, "updated_at": now}},
        )

        updated_doc = await collection.find_one({"report_id": report_id}, {"_id": 0})
        return ReportSpec(**updated_doc)
    except Exception as exc:
        logger.error("Report edit failed", exc_info=exc)
        raise HTTPException(status_code=500, detail=f"Report edit failed: {exc}")


@router.post(
    "/{report_id}/export/pdf",
    summary="Export report as PDF",
    description="Generate a PDF file from the report and return it as a downloadable file.",
)
async def export_report_pdf(
    report_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> StreamingResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"report_id": report_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    if doc.get("status") != ReportStatus.READY.value:
        raise HTTPException(
            status_code=409,
            detail=f"Report is not ready for export (status: {doc.get('status')}).",
        )

    # Generate PDF content
    try:
        from app.services.reports.pdf_export import export_report_to_pdf

        pdf_bytes = await export_report_to_pdf(doc)
    except ImportError:
        logger.warning("PDF exporter not yet implemented; generating Markdown fallback.")
        markdown_text = _build_markdown(doc)
        pdf_bytes = markdown_text.encode("utf-8")
        # Return as a text file if PDF generation is unavailable
        safe_title = doc.get("title", "report").replace(" ", "_")[:50]
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.md"',
            },
        )
    except Exception as exc:
        logger.error("PDF export failed", exc_info=exc)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {exc}")

    safe_title = doc.get("title", "report").replace(" ", "_")[:50]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.pdf"',
        },
    )


@router.delete(
    "/{report_id}",
    response_model=DeleteReportResponse,
    summary="Delete report",
    description="Permanently delete a report.",
)
async def delete_report(
    report_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DeleteReportResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"report_id": report_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    await collection.delete_one({"report_id": report_id})

    return DeleteReportResponse(
        report_id=report_id,
        message="Report has been deleted.",
    )
