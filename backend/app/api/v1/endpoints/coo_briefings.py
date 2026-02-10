"""Endpoints for COO briefings and file summaries.

Serves the frontend COO Briefing tab with pipeline status,
individual file summaries, the aggregated briefing, and a
regenerate trigger.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_database

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}", tags=["coo-briefings"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class FileSummaryInfo(BaseModel):
    summary_id: str = Field(..., description="Unique summary identifier.")
    file_id: str = Field(..., description="Source file identifier.")
    filename: str = Field(..., description="Original filename.")
    file_type: str = Field(..., description="Detected file type.")
    status: str = Field(..., description="Summary status: completed, failed, processing.")
    summary_markdown: str | None = Field(default=None, description="Markdown summary text.")
    error_message: str | None = Field(default=None, description="Error details if failed.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class FileSummaryListResponse(BaseModel):
    summaries: list[FileSummaryInfo] = Field(default_factory=list)
    total: int = Field(default=0)
    skip: int = Field(default=0)
    limit: int = Field(default=50)


class AttentionItem(BaseModel):
    title: str
    severity: str
    details: str


class ProjectHealthInfo(BaseModel):
    status: str
    score: int
    rationale: str


class TeamCapacityItem(BaseModel):
    person: str
    status: str
    details: str


class DeadlineItem(BaseModel):
    item: str
    date: str
    status: str


class RecentChangeItem(BaseModel):
    change: str
    impact: str


class COOBriefingData(BaseModel):
    executive_summary: str = Field(default="")
    attention_items: list[AttentionItem] = Field(default_factory=list)
    project_health: ProjectHealthInfo | None = Field(default=None)
    team_capacity: list[TeamCapacityItem] = Field(default_factory=list)
    upcoming_deadlines: list[DeadlineItem] = Field(default_factory=list)
    recent_changes: list[RecentChangeItem] = Field(default_factory=list)


class COOBriefingResponse(BaseModel):
    briefing_id: str = Field(..., description="Unique briefing identifier.")
    project_id: str = Field(..., description="Project identifier.")
    status: str = Field(..., description="Briefing status: completed, failed, processing.")
    briefing: COOBriefingData | None = Field(default=None, description="Structured briefing data.")
    error_message: str | None = Field(default=None, description="Error details if failed.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class COOBriefingStatusResponse(BaseModel):
    project_id: str = Field(..., description="Project identifier.")
    pipeline_status: str = Field(
        ...,
        description="Overall pipeline status: idle, processing, completed, failed.",
    )
    summaries_total: int = Field(default=0, description="Total file summaries.")
    summaries_completed: int = Field(default=0, description="Completed summaries.")
    summaries_failed: int = Field(default=0, description="Failed summaries.")
    summaries_processing: int = Field(default=0, description="In-progress summaries.")
    briefing_status: str | None = Field(
        default=None,
        description="Status of the latest COO briefing.",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/file-summaries",
    response_model=FileSummaryListResponse,
    summary="List file summaries",
    description="Retrieve paginated list of per-file summaries for a project.",
)
async def list_file_summaries(
    project_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> FileSummaryListResponse:
    query: dict[str, Any] = {"project_id": project_id}
    total = await db.file_summaries.count_documents(query)
    cursor = (
        db.file_summaries.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    summaries = [FileSummaryInfo(**d) for d in docs]
    return FileSummaryListResponse(
        summaries=summaries, total=total, skip=skip, limit=limit
    )


@router.get(
    "/coo-briefing",
    response_model=COOBriefingResponse,
    summary="Get latest COO briefing",
    description="Retrieve the most recent COO briefing for a project.",
)
async def get_coo_briefing(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> COOBriefingResponse:
    doc = await db.coo_briefings.find_one(
        {"project_id": project_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"No COO briefing found for project '{project_id}'.",
        )
    return COOBriefingResponse(**doc)


@router.get(
    "/coo-briefing/status",
    response_model=COOBriefingStatusResponse,
    summary="Get COO pipeline status",
    description="Check the progress of the summarization pipeline.",
)
async def get_coo_briefing_status(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> COOBriefingStatusResponse:
    # Count summaries by status
    pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    counts: dict[str, int] = {}
    async for doc in db.file_summaries.aggregate(pipeline):
        counts[doc["_id"]] = doc["count"]

    total = sum(counts.values())
    completed = counts.get("completed", 0)
    failed = counts.get("failed", 0)
    processing = counts.get("processing", 0)

    # Get latest briefing status
    latest_briefing = await db.coo_briefings.find_one(
        {"project_id": project_id},
        {"_id": 0, "status": 1},
        sort=[("created_at", -1)],
    )
    briefing_status = latest_briefing["status"] if latest_briefing else None

    # Determine overall pipeline status
    if total == 0 and briefing_status is None:
        pipeline_status = "idle"
    elif processing > 0:
        pipeline_status = "processing"
    elif briefing_status == "processing":
        pipeline_status = "processing"
    elif briefing_status == "completed":
        pipeline_status = "completed"
    elif briefing_status == "failed" and completed > 0:
        pipeline_status = "failed"
    elif total > 0 and completed + failed == total and briefing_status is None:
        # Summaries done but briefing not started yet — still processing
        pipeline_status = "processing"
    else:
        pipeline_status = "processing" if total > 0 else "idle"

    return COOBriefingStatusResponse(
        project_id=project_id,
        pipeline_status=pipeline_status,
        summaries_total=total,
        summaries_completed=completed,
        summaries_failed=failed,
        summaries_processing=processing,
        briefing_status=briefing_status,
    )


class RegenerateBriefingResponse(BaseModel):
    project_id: str = Field(..., description="Project identifier.")
    status: str = Field(..., description="Regeneration status: started or error.")
    message: str = Field(..., description="Human-readable status message.")


@router.post(
    "/coo-briefing/regenerate",
    response_model=RegenerateBriefingResponse,
    status_code=202,
    summary="Regenerate COO briefing",
    description="Re-run the COO briefing aggregation using existing file summaries. "
    "Does NOT re-upload or re-summarize files.",
)
async def regenerate_coo_briefing(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> RegenerateBriefingResponse:
    # Check that we have completed summaries to aggregate
    completed_count = await db.file_summaries.count_documents(
        {"project_id": project_id, "status": "completed"}
    )
    if completed_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No completed file summaries to aggregate. Upload files first.",
        )

    # Fire the aggregation as a background task
    async def _run_aggregation() -> None:
        try:
            from app.services.summarization.coo_aggregator import generate_coo_briefing

            logger.info("COO regenerate: starting for project %s (%d summaries)", project_id, completed_count)
            result = await generate_coo_briefing(project_id, db)
            logger.info("COO regenerate: finished for project %s → %s", project_id, result.get("status"))
        except Exception as exc:
            logger.warning("COO regenerate failed for project %s: %s", project_id, exc)

    asyncio.create_task(_run_aggregation())

    return RegenerateBriefingResponse(
        project_id=project_id,
        status="started",
        message=f"Regenerating COO briefing from {completed_count} file summaries.",
    )
