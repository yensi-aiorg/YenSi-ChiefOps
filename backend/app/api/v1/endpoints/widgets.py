"""
Widget management endpoints.

Widgets are the building blocks of dashboards. Each widget has a specification
(WidgetSpec) that defines its type, data query, and rendering options.
Supports natural-language widget generation and editing via AI.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widgets", tags=["widgets"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WidgetType(str, Enum):
    """Supported widget visualization types."""

    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"
    TEXT = "text"
    LIST = "list"


class DataQuery(BaseModel):
    """Specification for how a widget retrieves its data."""

    collection: str = Field(..., description="MongoDB collection to query.")
    pipeline: list[dict] = Field(
        default_factory=list,
        description="MongoDB aggregation pipeline stages.",
    )
    refresh_interval_seconds: int = Field(
        default=300,
        ge=0,
        description="How often to refresh data (0 = manual only).",
    )


class WidgetSpec(BaseModel):
    """Full specification for a widget."""

    widget_id: str = Field(default_factory=generate_uuid, description="Unique widget identifier.")
    title: str = Field(..., min_length=1, max_length=200, description="Widget display title.")
    description: str = Field(default="", max_length=1000, description="Widget description.")
    widget_type: WidgetType = Field(..., description="Visualization type.")
    data_query: DataQuery = Field(..., description="Data retrieval specification.")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific rendering configuration (colors, labels, axes, etc.).",
    )
    dashboard_id: str | None = Field(default=None, description="Dashboard this widget belongs to.")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp.")
    updated_at: datetime = Field(default_factory=utc_now, description="Last update timestamp.")


class WidgetDataResponse(BaseModel):
    """Response containing executed query results for a widget."""

    widget_id: str = Field(..., description="Widget identifier.")
    title: str = Field(..., description="Widget title.")
    widget_type: WidgetType = Field(..., description="Widget type.")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Query result rows.")
    row_count: int = Field(default=0, description="Number of result rows.")
    executed_at: datetime = Field(..., description="When the query was executed.")


class WidgetGenerateRequest(BaseModel):
    """Request for natural-language widget generation."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language description of the desired widget.",
    )
    dashboard_id: str = Field(..., description="Dashboard to associate the widget with.")


class WidgetAddRequest(BaseModel):
    """Request to add a widget to a dashboard from a WidgetSpec."""

    title: str = Field(..., min_length=1, max_length=200, description="Widget title.")
    description: str = Field(default="", max_length=1000, description="Widget description.")
    widget_type: WidgetType = Field(..., description="Visualization type.")
    data_query: DataQuery = Field(..., description="Data retrieval specification.")
    config: dict[str, Any] = Field(default_factory=dict, description="Rendering configuration.")
    x: int = Field(default=0, ge=0, description="Grid column position.")
    y: int = Field(default=0, ge=0, description="Grid row position.")
    w: int = Field(default=4, ge=1, description="Width in grid units.")
    h: int = Field(default=3, ge=1, description="Height in grid units.")


class WidgetUpdateRequest(BaseModel):
    """Request to update widget properties."""

    title: str | None = Field(
        default=None, min_length=1, max_length=200, description="Updated title."
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Updated description."
    )
    widget_type: WidgetType | None = Field(default=None, description="Updated type.")
    data_query: DataQuery | None = Field(default=None, description="Updated data query.")
    config: dict[str, Any] | None = Field(default=None, description="Updated config.")


class WidgetNLEditRequest(BaseModel):
    """Request for natural-language widget editing."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language edit instruction.",
    )


class DeleteWidgetResponse(BaseModel):
    """Response after deleting a widget."""

    widget_id: str = Field(..., description="Deleted widget ID.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["widgets"]


def _get_dashboards_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["dashboards"]


async def _execute_widget_query(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    data_query: DataQuery,
) -> list[dict[str, Any]]:
    """Execute a widget's data query and return results."""
    try:
        target_collection = db[data_query.collection]
        pipeline = data_query.pipeline

        if not pipeline:
            # If no pipeline, just return recent documents
            cursor = target_collection.find({}, {"_id": 0}).limit(100)
            return await cursor.to_list(length=100)

        # Add $limit if not already present to prevent unbounded queries
        has_limit = any("$limit" in stage for stage in pipeline)
        if not has_limit:
            pipeline = [*pipeline, {"$limit": 1000}]

        # Remove _id from projection if $project is present
        safe_pipeline = []
        for stage in pipeline:
            if "$project" in stage and "_id" not in stage["$project"]:
                stage = dict(stage)
                stage["$project"] = {**stage["$project"], "_id": 0}
            safe_pipeline.append(stage)

        cursor = target_collection.aggregate(safe_pipeline)
        return await cursor.to_list(length=1000)
    except Exception as exc:
        logger.error("Widget query execution failed", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute widget query: {exc}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{widget_id}",
    response_model=WidgetSpec,
    summary="Get widget spec",
    description="Retrieve the full specification of a single widget.",
)
async def get_widget(
    widget_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> WidgetSpec:
    collection = _get_collection(db)
    doc = await collection.find_one({"widget_id": widget_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")

    return WidgetSpec(**doc)


@router.get(
    "/{widget_id}/data",
    response_model=WidgetDataResponse,
    summary="Get widget data",
    description="Execute the widget's DataQuery and return the results.",
)
async def get_widget_data(
    widget_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> WidgetDataResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"widget_id": widget_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")

    data_query = DataQuery(**doc["data_query"])
    results = await _execute_widget_query(db, data_query)

    return WidgetDataResponse(
        widget_id=widget_id,
        title=doc["title"],
        widget_type=doc["widget_type"],
        data=results,
        row_count=len(results),
        executed_at=utc_now(),
    )


@router.post(
    "/generate",
    response_model=WidgetSpec,
    status_code=201,
    summary="Generate widget from natural language",
    description="Describe a widget in plain English and receive a generated WidgetSpec. "
    "Uses AI to translate the description into a data query and visualization config.",
)
async def generate_widget(
    body: WidgetGenerateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> WidgetSpec:
    # Verify dashboard exists
    dashboards = _get_dashboards_collection(db)
    dashboard_doc = await dashboards.find_one({"dashboard_id": body.dashboard_id})
    if dashboard_doc is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{body.dashboard_id}' not found.")

    try:
        from app.services.widgets.service import WidgetService

        service = WidgetService(db)
        return await service.generate_from_nl(
            description=body.description,
            dashboard_id=body.dashboard_id,
        )
    except ImportError:
        logger.warning("Widget service not yet implemented; returning placeholder spec.")
        now = utc_now()
        widget_id = generate_uuid()
        placeholder_spec = WidgetSpec(
            widget_id=widget_id,
            title=f"Generated: {body.description[:80]}",
            description=body.description,
            widget_type=WidgetType.METRIC_CARD,
            data_query=DataQuery(
                collection="projects",
                pipeline=[{"$count": "total"}],
                refresh_interval_seconds=300,
            ),
            config={"generated_from": body.description},
            dashboard_id=body.dashboard_id,
            created_at=now,
            updated_at=now,
        )

        # Persist the generated widget
        collection = _get_collection(db)
        await collection.insert_one(placeholder_spec.model_dump())

        # Add widget to dashboard
        await dashboards.update_one(
            {"dashboard_id": body.dashboard_id},
            {
                "$push": {"widget_ids": widget_id},
                "$set": {"updated_at": now},
            },
        )

        return placeholder_spec
    except Exception as exc:
        logger.error("Widget generation failed", exc_info=exc)
        raise HTTPException(status_code=500, detail=f"Widget generation failed: {exc}")


@router.post(
    "/{dashboard_id}/add",
    response_model=WidgetSpec,
    status_code=201,
    summary="Add widget to dashboard",
    description="Add a new widget to a dashboard from a widget specification.",
)
async def add_widget_to_dashboard(
    dashboard_id: str,
    body: WidgetAddRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> WidgetSpec:
    dashboards = _get_dashboards_collection(db)
    dashboard_doc = await dashboards.find_one({"dashboard_id": dashboard_id})
    if dashboard_doc is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")

    now = utc_now()
    widget_id = generate_uuid()

    spec = WidgetSpec(
        widget_id=widget_id,
        title=body.title,
        description=body.description,
        widget_type=body.widget_type,
        data_query=body.data_query,
        config=body.config,
        dashboard_id=dashboard_id,
        created_at=now,
        updated_at=now,
    )

    # Persist the widget
    collection = _get_collection(db)
    await collection.insert_one(spec.model_dump())

    # Add to dashboard's widget list and layout
    layout_item = {
        "widget_id": widget_id,
        "x": body.x,
        "y": body.y,
        "w": body.w,
        "h": body.h,
    }
    await dashboards.update_one(
        {"dashboard_id": dashboard_id},
        {
            "$push": {
                "widget_ids": widget_id,
                "layout": layout_item,
            },
            "$set": {"updated_at": now},
        },
    )

    return spec


@router.patch(
    "/{widget_id}",
    response_model=WidgetSpec,
    summary="Update widget",
    description="Update a widget's title, description, type, data query, or config.",
)
async def update_widget(
    widget_id: str,
    body: WidgetUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> WidgetSpec:
    collection = _get_collection(db)
    doc = await collection.find_one({"widget_id": widget_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")

    update_fields: dict = {"updated_at": utc_now()}

    if body.title is not None:
        update_fields["title"] = body.title
    if body.description is not None:
        update_fields["description"] = body.description
    if body.widget_type is not None:
        update_fields["widget_type"] = body.widget_type.value
    if body.data_query is not None:
        update_fields["data_query"] = body.data_query.model_dump()
    if body.config is not None:
        update_fields["config"] = body.config

    await collection.update_one({"widget_id": widget_id}, {"$set": update_fields})

    updated_doc = await collection.find_one({"widget_id": widget_id}, {"_id": 0})

    return WidgetSpec(**updated_doc)


@router.patch(
    "/{widget_id}/nl-edit",
    response_model=WidgetSpec,
    summary="Edit widget via natural language",
    description="Send a natural language instruction to modify a widget. "
    "The AI interprets the instruction and updates the widget spec.",
)
async def nl_edit_widget(
    widget_id: str,
    body: WidgetNLEditRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> WidgetSpec:
    collection = _get_collection(db)
    doc = await collection.find_one({"widget_id": widget_id}, {"_id": 0})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")

    current_spec = WidgetSpec(**doc)

    try:
        from app.services.widgets.service import WidgetService

        service = WidgetService(db)
        updated_spec = await service.edit_from_nl(
            widget_id=widget_id,
            current_spec=current_spec,
            message=body.message,
        )

        # Persist the updated spec
        await collection.update_one(
            {"widget_id": widget_id},
            {"$set": updated_spec.model_dump()},
        )

        return updated_spec
    except ImportError:
        logger.warning("Widget service not yet implemented; returning spec unchanged.")
        now = utc_now()
        await collection.update_one(
            {"widget_id": widget_id},
            {
                "$set": {
                    "description": f"{current_spec.description} [NL edit requested: {body.message}]",
                    "updated_at": now,
                }
            },
        )

        updated_doc = await collection.find_one({"widget_id": widget_id}, {"_id": 0})
        return WidgetSpec(**updated_doc)
    except Exception as exc:
        logger.error("NL widget edit failed", exc_info=exc)
        raise HTTPException(status_code=500, detail=f"NL widget edit failed: {exc}")


@router.delete(
    "/{widget_id}",
    response_model=DeleteWidgetResponse,
    summary="Delete widget",
    description="Remove a widget and clean up its reference from any dashboard.",
)
async def delete_widget(
    widget_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DeleteWidgetResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"widget_id": widget_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")

    # Remove from parent dashboard
    dashboard_id = doc.get("dashboard_id")
    if dashboard_id:
        dashboards = _get_dashboards_collection(db)
        await dashboards.update_one(
            {"dashboard_id": dashboard_id},
            {
                "$pull": {
                    "widget_ids": widget_id,
                    "layout": {"widget_id": widget_id},
                },
                "$set": {"updated_at": utc_now()},
            },
        )

    await collection.delete_one({"widget_id": widget_id})

    return DeleteWidgetResponse(
        widget_id=widget_id,
        message="Widget has been deleted.",
    )
