"""
Dashboard management endpoints.

Dashboards are collections of widgets that visualize project and
organizational data. Supports CRUD operations and project-scoped filtering.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LayoutItem(BaseModel):
    """Position and size of a widget on the dashboard grid."""

    widget_id: str = Field(..., description="Widget identifier.")
    x: int = Field(default=0, ge=0, description="Grid column position.")
    y: int = Field(default=0, ge=0, description="Grid row position.")
    w: int = Field(default=4, ge=1, description="Width in grid units.")
    h: int = Field(default=3, ge=1, description="Height in grid units.")


class DashboardCreateRequest(BaseModel):
    """Request body for creating a dashboard."""

    name: str = Field(..., min_length=1, max_length=200, description="Dashboard name.")
    description: str = Field(default="", max_length=2000, description="Dashboard description.")
    project_id: str | None = Field(default=None, description="Scope this dashboard to a project.")
    layout: list[LayoutItem] = Field(default_factory=list, description="Initial widget layout.")


class DashboardUpdateRequest(BaseModel):
    """Request body for updating a dashboard."""

    name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Updated name."
    )
    description: str | None = Field(
        default=None, max_length=2000, description="Updated description."
    )
    layout: list[LayoutItem] | None = Field(default=None, description="Updated layout.")


class DashboardSummary(BaseModel):
    """Lightweight dashboard record for list views."""

    dashboard_id: str = Field(..., description="Unique dashboard identifier.")
    name: str = Field(..., description="Dashboard name.")
    description: str = Field(default="", description="Dashboard description.")
    project_id: str | None = Field(default=None, description="Associated project ID.")
    widget_count: int = Field(default=0, description="Number of widgets on this dashboard.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class DashboardDetail(BaseModel):
    """Full dashboard detail including layout and widget specs."""

    dashboard_id: str = Field(..., description="Unique dashboard identifier.")
    name: str = Field(..., description="Dashboard name.")
    description: str = Field(default="", description="Dashboard description.")
    project_id: str | None = Field(default=None, description="Associated project ID.")
    layout: list[LayoutItem] = Field(
        default_factory=list, description="Widget positions and sizes."
    )
    widget_ids: list[str] = Field(default_factory=list, description="Ordered list of widget IDs.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class DashboardListResponse(BaseModel):
    """Paginated list of dashboards."""

    dashboards: list[DashboardSummary] = Field(default_factory=list, description="Dashboard list.")
    total: int = Field(default=0, description="Total matching dashboards.")
    skip: int = Field(default=0, description="Records skipped.")
    limit: int = Field(default=20, description="Page size.")


class DeleteDashboardResponse(BaseModel):
    """Response after deleting a dashboard."""

    dashboard_id: str = Field(..., description="Deleted dashboard ID.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["dashboards"]


def _get_widgets_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["widgets"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=DashboardListResponse,
    summary="List dashboards",
    description="Retrieve all dashboards, optionally filtered by project.",
)
async def list_dashboards(
    skip: int = Query(default=0, ge=0, description="Records to skip."),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return."),
    project_id: str | None = Query(default=None, description="Filter by project ID."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DashboardListResponse:
    collection = _get_collection(db)

    query: dict = {}
    if project_id is not None:
        query["project_id"] = project_id

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    dashboards = []
    for doc in docs:
        dashboards.append(
            DashboardSummary(
                dashboard_id=doc["dashboard_id"],
                name=doc["name"],
                description=doc.get("description", ""),
                project_id=doc.get("project_id"),
                widget_count=len(doc.get("widget_ids", [])),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
            )
        )

    return DashboardListResponse(dashboards=dashboards, total=total, skip=skip, limit=limit)


@router.get(
    "/{dashboard_id}",
    response_model=DashboardDetail,
    summary="Get dashboard detail",
    description="Retrieve a single dashboard with its layout and widget specifications.",
)
async def get_dashboard(
    dashboard_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DashboardDetail:
    collection = _get_collection(db)
    doc = await collection.find_one({"dashboard_id": dashboard_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")

    layout_raw = doc.get("layout", [])
    layout = [LayoutItem(**item) if isinstance(item, dict) else item for item in layout_raw]

    return DashboardDetail(
        dashboard_id=doc["dashboard_id"],
        name=doc["name"],
        description=doc.get("description", ""),
        project_id=doc.get("project_id"),
        layout=layout,
        widget_ids=doc.get("widget_ids", []),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post(
    "/",
    response_model=DashboardDetail,
    status_code=201,
    summary="Create dashboard",
    description="Create a new custom dashboard.",
)
async def create_dashboard(
    body: DashboardCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DashboardDetail:
    collection = _get_collection(db)

    now = utc_now()
    dashboard_id = generate_uuid()

    # Extract widget IDs from layout if provided
    widget_ids = [item.widget_id for item in body.layout]

    dashboard_doc = {
        "dashboard_id": dashboard_id,
        "name": body.name,
        "description": body.description,
        "project_id": body.project_id,
        "layout": [item.model_dump() for item in body.layout],
        "widget_ids": widget_ids,
        "created_at": now,
        "updated_at": now,
    }

    await collection.insert_one(dashboard_doc)

    return DashboardDetail(
        dashboard_id=dashboard_id,
        name=body.name,
        description=body.description,
        project_id=body.project_id,
        layout=body.layout,
        widget_ids=widget_ids,
        created_at=now,
        updated_at=now,
    )


@router.patch(
    "/{dashboard_id}",
    response_model=DashboardDetail,
    summary="Update dashboard",
    description="Update a dashboard's name, description, or widget layout.",
)
async def update_dashboard(
    dashboard_id: str,
    body: DashboardUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DashboardDetail:
    collection = _get_collection(db)
    doc = await collection.find_one({"dashboard_id": dashboard_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")

    update_fields: dict = {"updated_at": utc_now()}

    if body.name is not None:
        update_fields["name"] = body.name
    if body.description is not None:
        update_fields["description"] = body.description
    if body.layout is not None:
        update_fields["layout"] = [item.model_dump() for item in body.layout]
        update_fields["widget_ids"] = [item.widget_id for item in body.layout]

    await collection.update_one({"dashboard_id": dashboard_id}, {"$set": update_fields})

    updated_doc = await collection.find_one({"dashboard_id": dashboard_id}, {"_id": 0})

    layout_raw = updated_doc.get("layout", [])
    layout = [LayoutItem(**item) if isinstance(item, dict) else item for item in layout_raw]

    return DashboardDetail(
        dashboard_id=updated_doc["dashboard_id"],
        name=updated_doc["name"],
        description=updated_doc.get("description", ""),
        project_id=updated_doc.get("project_id"),
        layout=layout,
        widget_ids=updated_doc.get("widget_ids", []),
        created_at=updated_doc["created_at"],
        updated_at=updated_doc["updated_at"],
    )


@router.delete(
    "/{dashboard_id}",
    response_model=DeleteDashboardResponse,
    summary="Delete dashboard",
    description="Delete a custom dashboard and optionally its associated widgets.",
)
async def delete_dashboard(
    dashboard_id: str,
    delete_widgets: bool = Query(
        default=False,
        description="Also delete all widgets belonging to this dashboard.",
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DeleteDashboardResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"dashboard_id": dashboard_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")

    if delete_widgets:
        widget_ids = doc.get("widget_ids", [])
        if widget_ids:
            widgets_col = _get_widgets_collection(db)
            await widgets_col.delete_many({"widget_id": {"$in": widget_ids}})

    await collection.delete_one({"dashboard_id": dashboard_id})

    return DeleteDashboardResponse(
        dashboard_id=dashboard_id,
        message="Dashboard has been deleted.",
    )
