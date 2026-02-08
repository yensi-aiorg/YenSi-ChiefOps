"""
People directory endpoints.

Manages the unified people directory built from cross-referencing identities
across Slack, Jira, and Google Drive. Supports listing, filtering, manual
COO corrections, and triggering reprocessing of the people pipeline.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import utc_now
from app.models.person import ActivityLevel, RoleSource

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/people", tags=["people"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PersonSummary(BaseModel):
    """Lightweight person record for list views."""

    person_id: str = Field(..., description="Unique person identifier.")
    name: str = Field(..., description="Display name.")
    email: str | None = Field(default=None, description="Email address.")
    role: str = Field(..., description="Job role.")
    role_source: RoleSource = Field(..., description="How the role was determined.")
    department: str | None = Field(default=None, description="Department name.")
    activity_level: ActivityLevel = Field(..., description="Computed activity level.")
    last_active_date: datetime = Field(..., description="Most recent activity.")
    tasks_assigned: int = Field(default=0, description="Tasks currently assigned.")
    tasks_completed: int = Field(default=0, description="Tasks completed.")
    projects: list[str] = Field(default_factory=list, description="Project IDs involved in.")


class PersonDetail(BaseModel):
    """Full person detail including engagement metrics and source references."""

    person_id: str
    name: str
    email: str | None = None
    role: str
    role_source: RoleSource
    department: str | None = None
    activity_level: ActivityLevel
    last_active_date: datetime
    avatar_url: str | None = None
    slack_user_id: str | None = None
    jira_username: str | None = None
    tasks_assigned: int = 0
    tasks_completed: int = 0
    engagement_metrics: dict = Field(default_factory=dict, description="Slack engagement stats.")
    source_ids: list[dict] = Field(default_factory=list, description="Source system references.")
    projects: list[str] = Field(default_factory=list, description="Project IDs.")
    created_at: datetime = Field(..., description="Record creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class PersonListResponse(BaseModel):
    """Paginated list of people."""

    people: list[PersonSummary] = Field(default_factory=list, description="List of people.")
    total: int = Field(default=0, description="Total matching records.")
    skip: int = Field(default=0, description="Records skipped.")
    limit: int = Field(default=50, description="Page size.")


class PersonUpdateRequest(BaseModel):
    """Request body for COO corrections to a person record."""

    name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Corrected name."
    )
    role: str | None = Field(default=None, min_length=1, description="Corrected role.")
    department: str | None = Field(default=None, description="Corrected department.")


class PersonUpdateResponse(BaseModel):
    """Response after updating a person record."""

    person_id: str = Field(..., description="Updated person ID.")
    updated_fields: list[str] = Field(default_factory=list, description="Fields that were changed.")
    message: str = Field(..., description="Human-readable status message.")


class ReprocessResponse(BaseModel):
    """Response after triggering people pipeline reprocessing."""

    status: str = Field(..., description="Reprocessing status.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    """Return the people collection."""
    return db["people"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=PersonListResponse,
    summary="List people",
    description="Retrieve a paginated list of all people in the directory, "
    "with optional filters by activity level, department, or project.",
)
async def list_people(
    skip: int = Query(default=0, ge=0, description="Records to skip."),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return."),
    activity_level: ActivityLevel | None = Query(
        default=None, description="Filter by activity level."
    ),
    department: str | None = Query(default=None, description="Filter by department."),
    project_id: str | None = Query(default=None, description="Filter by project involvement."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> PersonListResponse:
    collection = _get_collection(db)

    query: dict = {}
    if activity_level is not None:
        query["activity_level"] = activity_level.value
    if department is not None:
        query["department"] = {"$regex": department, "$options": "i"}
    if project_id is not None:
        query["projects"] = project_id

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    people = []
    for doc in docs:
        people.append(
            PersonSummary(
                person_id=doc["person_id"],
                name=doc["name"],
                email=doc.get("email"),
                role=doc["role"],
                role_source=doc.get("role_source", RoleSource.AI_IDENTIFIED.value),
                department=doc.get("department"),
                activity_level=doc.get("activity_level", ActivityLevel.MODERATE.value),
                last_active_date=doc.get("last_active_date", doc.get("created_at")),
                tasks_assigned=doc.get("tasks_assigned", 0),
                tasks_completed=doc.get("tasks_completed", 0),
                projects=doc.get("projects", []),
            )
        )

    return PersonListResponse(people=people, total=total, skip=skip, limit=limit)


@router.get(
    "/{person_id}",
    response_model=PersonDetail,
    summary="Get person detail",
    description="Retrieve the full detail of a single person, including engagement "
    "metrics and source system references.",
)
async def get_person(
    person_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> PersonDetail:
    collection = _get_collection(db)
    doc = await collection.find_one({"person_id": person_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' not found.")

    engagement = doc.get("engagement_metrics", {})
    if isinstance(engagement, dict):
        engagement_dict = engagement
    else:
        engagement_dict = engagement if hasattr(engagement, "__dict__") else {}

    return PersonDetail(
        person_id=doc["person_id"],
        name=doc["name"],
        email=doc.get("email"),
        role=doc["role"],
        role_source=doc.get("role_source", RoleSource.AI_IDENTIFIED.value),
        department=doc.get("department"),
        activity_level=doc.get("activity_level", ActivityLevel.MODERATE.value),
        last_active_date=doc.get("last_active_date", doc.get("created_at")),
        avatar_url=doc.get("avatar_url"),
        slack_user_id=doc.get("slack_user_id"),
        jira_username=doc.get("jira_username"),
        tasks_assigned=doc.get("tasks_assigned", 0),
        tasks_completed=doc.get("tasks_completed", 0),
        engagement_metrics=engagement_dict,
        source_ids=doc.get("source_ids", []),
        projects=doc.get("projects", []),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.patch(
    "/{person_id}",
    response_model=PersonUpdateResponse,
    summary="Update person (COO correction)",
    description="Manually correct a person's name, role, or department. "
    "Updates are flagged as COO-corrected so they persist through reprocessing.",
)
async def update_person(
    person_id: str,
    body: PersonUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> PersonUpdateResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"person_id": person_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' not found.")

    update_fields: dict = {"updated_at": utc_now()}
    changed: list[str] = []

    if body.name is not None and body.name != doc.get("name"):
        update_fields["name"] = body.name
        changed.append("name")

    if body.role is not None and body.role != doc.get("role"):
        update_fields["role"] = body.role
        update_fields["role_source"] = RoleSource.COO_CORRECTED.value
        changed.append("role")

    if body.department is not None and body.department != doc.get("department"):
        update_fields["department"] = body.department
        changed.append("department")

    if not changed:
        return PersonUpdateResponse(
            person_id=person_id,
            updated_fields=[],
            message="No changes detected.",
        )

    await collection.update_one({"person_id": person_id}, {"$set": update_fields})

    return PersonUpdateResponse(
        person_id=person_id,
        updated_fields=changed,
        message=f"Updated {len(changed)} field(s): {', '.join(changed)}.",
    )


@router.post(
    "/reprocess",
    response_model=ReprocessResponse,
    summary="Reprocess people pipeline",
    description="Trigger re-running the people identity resolution and analysis pipeline. "
    "COO-corrected fields are preserved.",
)
async def reprocess_people(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ReprocessResponse:
    try:
        from app.services.people.service import PeopleService

        service = PeopleService(db)
        await service.reprocess_all()
        return ReprocessResponse(
            status="started",
            message="People pipeline reprocessing has been initiated.",
        )
    except ImportError:
        logger.warning("People service not yet implemented.")
        return ReprocessResponse(
            status="unavailable",
            message="People service is not yet available. Pipeline reprocessing cannot be started.",
        )
    except Exception as exc:
        logger.error("Failed to start people reprocessing", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start people reprocessing: {exc}",
        )
