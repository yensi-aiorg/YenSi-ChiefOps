"""
Project management endpoints.

Manages projects detected from ingested data or created manually by the COO.
Each project tracks health scores, deadlines, team members, and AI-generated
analysis results.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ProjectHealthScore(str, Enum):
    """Overall project health classification."""

    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectCreateRequest(BaseModel):
    """Request body for creating a project manually."""

    name: str = Field(..., min_length=1, max_length=300, description="Project name.")
    description: str = Field(default="", max_length=5000, description="Project description.")
    deadline: datetime | None = Field(default=None, description="Project deadline (UTC).")


class ProjectUpdateRequest(BaseModel):
    """Request body for updating project metadata."""

    name: str | None = Field(
        default=None, min_length=1, max_length=300, description="Updated name."
    )
    description: str | None = Field(
        default=None, max_length=5000, description="Updated description."
    )
    deadline: datetime | None = Field(default=None, description="Updated deadline.")
    status: ProjectStatus | None = Field(default=None, description="Updated status.")


class ProjectSummary(BaseModel):
    """Lightweight project record for list views."""

    project_id: str = Field(..., description="Unique project identifier.")
    name: str = Field(..., description="Project name.")
    description: str = Field(default="", description="Project description.")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, description="Current status.")
    health_score: ProjectHealthScore = Field(
        default=ProjectHealthScore.UNKNOWN, description="Overall health."
    )
    deadline: datetime | None = Field(default=None, description="Project deadline.")
    team_size: int = Field(default=0, description="Number of team members.")
    open_tasks: int = Field(default=0, description="Number of open tasks.")
    completed_tasks: int = Field(default=0, description="Number of completed tasks.")
    created_at: datetime = Field(..., description="Project creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class ProjectDetail(BaseModel):
    """Full project detail including analysis and team information."""

    project_id: str
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    health_score: ProjectHealthScore = ProjectHealthScore.UNKNOWN
    deadline: datetime | None = None
    team_members: list[str] = Field(
        default_factory=list, description="List of person_ids on the team."
    )
    open_tasks: int = 0
    completed_tasks: int = 0
    total_tasks: int = 0
    key_risks: list[str] = Field(default_factory=list, description="Identified risks.")
    key_milestones: list[dict] = Field(default_factory=list, description="Project milestones.")
    recent_activity: list[dict] = Field(default_factory=list, description="Recent activity feed.")
    last_analysis_at: datetime | None = Field(
        default=None, description="When last analysis was run."
    )
    created_at: datetime = Field(..., description="Project creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    projects: list[ProjectSummary] = Field(default_factory=list, description="List of projects.")
    total: int = Field(default=0, description="Total matching projects.")
    skip: int = Field(default=0, description="Records skipped.")
    limit: int = Field(default=20, description="Page size.")


class ProjectAnalysisResponse(BaseModel):
    """Full AI-generated analysis result for a project."""

    project_id: str = Field(..., description="Project identifier.")
    health_score: ProjectHealthScore = Field(..., description="Computed health score.")
    summary: str = Field(default="", description="Executive summary of project state.")
    risks: list[dict] = Field(default_factory=list, description="Identified risks with severity.")
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations."
    )
    team_dynamics: dict = Field(default_factory=dict, description="Team collaboration analysis.")
    velocity_trend: str = Field(
        default="stable", description="Work velocity trend: improving, stable, declining."
    )
    analyzed_at: datetime = Field(..., description="When the analysis was performed.")


class AnalyzeTriggerResponse(BaseModel):
    """Response after triggering a fresh analysis."""

    project_id: str = Field(..., description="Project identifier.")
    status: str = Field(..., description="Analysis trigger status.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    """Return the projects collection."""
    return db["projects"]


def _get_analysis_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    """Return the project_analyses collection."""
    return db["project_analyses"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List projects",
    description="Retrieve a paginated list of all projects with summary health scores.",
)
async def list_projects(
    skip: int = Query(default=0, ge=0, description="Records to skip."),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return."),
    status: ProjectStatus | None = Query(default=None, description="Filter by status."),
    health: ProjectHealthScore | None = Query(default=None, description="Filter by health score."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectListResponse:
    collection = _get_collection(db)

    query: dict = {}
    if status is not None:
        query["status"] = status.value
    if health is not None:
        query["health_score"] = health.value

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    projects = []
    for doc in docs:
        projects.append(
            ProjectSummary(
                project_id=doc["project_id"],
                name=doc["name"],
                description=doc.get("description", ""),
                status=doc.get("status", ProjectStatus.ACTIVE.value),
                health_score=doc.get("health_score", ProjectHealthScore.UNKNOWN.value),
                deadline=doc.get("deadline"),
                team_size=len(doc.get("team_members", [])),
                open_tasks=doc.get("open_tasks", 0),
                completed_tasks=doc.get("completed_tasks", 0),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
            )
        )

    return ProjectListResponse(projects=projects, total=total, skip=skip, limit=limit)


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Get project detail",
    description="Retrieve the full detail of a single project including team, tasks, and analysis.",
)
async def get_project(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectDetail:
    collection = _get_collection(db)
    doc = await collection.find_one({"project_id": project_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    return ProjectDetail(
        project_id=doc["project_id"],
        name=doc["name"],
        description=doc.get("description", ""),
        status=doc.get("status", ProjectStatus.ACTIVE.value),
        health_score=doc.get("health_score", ProjectHealthScore.UNKNOWN.value),
        deadline=doc.get("deadline"),
        team_members=doc.get("team_members", []),
        open_tasks=doc.get("open_tasks", 0),
        completed_tasks=doc.get("completed_tasks", 0),
        total_tasks=doc.get("total_tasks", 0),
        key_risks=doc.get("key_risks", []),
        key_milestones=doc.get("key_milestones", []),
        recent_activity=doc.get("recent_activity", []),
        last_analysis_at=doc.get("last_analysis_at"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post(
    "/",
    response_model=ProjectDetail,
    status_code=201,
    summary="Create project",
    description="Create a new project manually with a name, description, and optional deadline.",
)
async def create_project(
    body: ProjectCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectDetail:
    collection = _get_collection(db)

    now = utc_now()
    project_id = generate_uuid()

    project_doc = {
        "project_id": project_id,
        "name": body.name,
        "description": body.description,
        "status": ProjectStatus.ACTIVE.value,
        "health_score": ProjectHealthScore.UNKNOWN.value,
        "deadline": body.deadline,
        "team_members": [],
        "open_tasks": 0,
        "completed_tasks": 0,
        "total_tasks": 0,
        "key_risks": [],
        "key_milestones": [],
        "recent_activity": [],
        "last_analysis_at": None,
        "created_at": now,
        "updated_at": now,
    }

    await collection.insert_one(project_doc)

    return ProjectDetail(
        project_id=project_id,
        name=body.name,
        description=body.description,
        status=ProjectStatus.ACTIVE,
        health_score=ProjectHealthScore.UNKNOWN,
        deadline=body.deadline,
        team_members=[],
        open_tasks=0,
        completed_tasks=0,
        total_tasks=0,
        key_risks=[],
        key_milestones=[],
        recent_activity=[],
        last_analysis_at=None,
        created_at=now,
        updated_at=now,
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectDetail,
    summary="Update project metadata",
    description="Update a project's name, description, deadline, or status.",
)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectDetail:
    collection = _get_collection(db)
    doc = await collection.find_one({"project_id": project_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    update_fields: dict = {"updated_at": utc_now()}

    if body.name is not None:
        update_fields["name"] = body.name
    if body.description is not None:
        update_fields["description"] = body.description
    if body.deadline is not None:
        update_fields["deadline"] = body.deadline
    if body.status is not None:
        update_fields["status"] = body.status.value

    await collection.update_one({"project_id": project_id}, {"$set": update_fields})

    updated_doc = await collection.find_one({"project_id": project_id}, {"_id": 0})

    return ProjectDetail(
        project_id=updated_doc["project_id"],
        name=updated_doc["name"],
        description=updated_doc.get("description", ""),
        status=updated_doc.get("status", ProjectStatus.ACTIVE.value),
        health_score=updated_doc.get("health_score", ProjectHealthScore.UNKNOWN.value),
        deadline=updated_doc.get("deadline"),
        team_members=updated_doc.get("team_members", []),
        open_tasks=updated_doc.get("open_tasks", 0),
        completed_tasks=updated_doc.get("completed_tasks", 0),
        total_tasks=updated_doc.get("total_tasks", 0),
        key_risks=updated_doc.get("key_risks", []),
        key_milestones=updated_doc.get("key_milestones", []),
        recent_activity=updated_doc.get("recent_activity", []),
        last_analysis_at=updated_doc.get("last_analysis_at"),
        created_at=updated_doc["created_at"],
        updated_at=updated_doc["updated_at"],
    )


@router.get(
    "/{project_id}/analysis",
    response_model=ProjectAnalysisResponse,
    summary="Get project analysis",
    description="Retrieve the most recent AI-generated analysis for a project.",
)
async def get_project_analysis(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ProjectAnalysisResponse:
    # Verify project exists
    projects = _get_collection(db)
    project_doc = await projects.find_one({"project_id": project_id})
    if project_doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    analyses = _get_analysis_collection(db)
    analysis_doc = await analyses.find_one(
        {"project_id": project_id},
        {"_id": 0},
        sort=[("analyzed_at", -1)],
    )

    if analysis_doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for project '{project_id}'. Trigger one with POST /{project_id}/analyze.",
        )

    return ProjectAnalysisResponse(
        project_id=analysis_doc["project_id"],
        health_score=analysis_doc.get("health_score", ProjectHealthScore.UNKNOWN.value),
        summary=analysis_doc.get("summary", ""),
        risks=analysis_doc.get("risks", []),
        recommendations=analysis_doc.get("recommendations", []),
        team_dynamics=analysis_doc.get("team_dynamics", {}),
        velocity_trend=analysis_doc.get("velocity_trend", "stable"),
        analyzed_at=analysis_doc["analyzed_at"],
    )


@router.post(
    "/{project_id}/analyze",
    response_model=AnalyzeTriggerResponse,
    summary="Trigger project analysis",
    description="Trigger a fresh AI-powered analysis of the project's health, risks, "
    "and team dynamics.",
)
async def trigger_analysis(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> AnalyzeTriggerResponse:
    projects = _get_collection(db)
    project_doc = await projects.find_one({"project_id": project_id})
    if project_doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    try:
        from app.services.projects.service import ProjectService

        service = ProjectService(db)
        await service.analyze_project(project_id)

        # Update the project's last_analysis_at
        await projects.update_one(
            {"project_id": project_id},
            {"$set": {"last_analysis_at": utc_now(), "updated_at": utc_now()}},
        )

        return AnalyzeTriggerResponse(
            project_id=project_id,
            status="started",
            message="Project analysis has been initiated.",
        )
    except ImportError:
        logger.warning("Project service not yet implemented.")
        return AnalyzeTriggerResponse(
            project_id=project_id,
            status="unavailable",
            message="Project analysis service is not yet available.",
        )
    except Exception as exc:
        logger.error("Failed to trigger project analysis", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger analysis: {exc}",
        )
