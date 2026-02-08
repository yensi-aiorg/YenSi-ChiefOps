"""
Alert management endpoints.

Alerts are threshold-based or pattern-based monitors that trigger when
conditions are met (e.g., "alert me if Project X has no activity for 3 days").
Supports creation from natural language, listing, updating, and deletion.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""

    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISMISSED = "dismissed"
    DISABLED = "disabled"


class AlertCondition(BaseModel):
    """Machine-readable alert trigger condition."""

    field: str = Field(..., description="The data field to monitor.")
    operator: str = Field(
        ...,
        description="Comparison operator: eq, ne, gt, gte, lt, lte, contains, absent.",
    )
    value: Any = Field(..., description="Threshold or comparison value.")
    collection: str = Field(default="projects", description="MongoDB collection to monitor.")
    filter: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional MongoDB filter criteria.",
    )


class AlertCreateRequest(BaseModel):
    """Request to create an alert from natural language."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language description of the alert condition.",
    )


class AlertUpdateRequest(BaseModel):
    """Request to update or dismiss an alert."""

    status: AlertStatus | None = Field(default=None, description="New status.")
    severity: AlertSeverity | None = Field(default=None, description="Updated severity.")
    name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Updated name."
    )


class AlertResponse(BaseModel):
    """Full alert specification."""

    alert_id: str = Field(..., description="Unique alert identifier.")
    name: str = Field(..., description="Alert display name.")
    description: str = Field(default="", description="Human-readable alert description.")
    severity: AlertSeverity = Field(..., description="Severity level.")
    status: AlertStatus = Field(..., description="Current status.")
    condition: AlertCondition | None = Field(default=None, description="Trigger condition spec.")
    generated_from: str = Field(default="", description="Original NL request.")
    project_id: str | None = Field(default=None, description="Scoped project ID.")
    last_triggered_at: datetime | None = Field(default=None, description="Last trigger time.")
    trigger_count: int = Field(default=0, description="Total times triggered.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    alerts: list[AlertResponse] = Field(default_factory=list, description="Alerts list.")
    total: int = Field(default=0, description="Total matching alerts.")
    skip: int = Field(default=0, description="Records skipped.")
    limit: int = Field(default=50, description="Page size.")


class DeleteAlertResponse(BaseModel):
    """Response after deleting an alert."""

    alert_id: str = Field(..., description="Deleted alert ID.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["alerts"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=AlertResponse,
    status_code=201,
    summary="Create alert from natural language",
    description="Describe an alert condition in plain English. The AI translates "
    "it into a machine-readable condition that is continuously monitored.",
)
async def create_alert(
    body: AlertCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> AlertResponse:
    collection = _get_collection(db)
    now = utc_now()
    alert_id = generate_uuid()

    # Try AI-powered condition parsing
    alert_name: str
    alert_description: str
    alert_severity: AlertSeverity
    condition: AlertCondition | None = None
    project_id: str | None = None

    try:
        from app.services.alerts.service import AlertService

        service = AlertService(db)
        result = await service.create_from_nl(message=body.message)

        alert_name = result.get("name", f"Alert: {body.message[:60]}")
        alert_description = result.get("description", body.message)
        alert_severity = AlertSeverity(result.get("severity", "warning"))
        project_id = result.get("project_id")

        condition_data = result.get("condition")
        if condition_data:
            condition = AlertCondition(**condition_data)
    except ImportError:
        logger.warning("Alert service not yet implemented; creating with defaults.")
        alert_name = f"Alert: {body.message[:80]}"
        alert_description = body.message
        alert_severity = AlertSeverity.WARNING
    except Exception as exc:
        logger.error("Alert creation via NL failed", exc_info=exc)
        alert_name = f"Alert: {body.message[:80]}"
        alert_description = body.message
        alert_severity = AlertSeverity.WARNING

    alert_doc = {
        "alert_id": alert_id,
        "name": alert_name,
        "description": alert_description,
        "severity": alert_severity.value,
        "status": AlertStatus.ACTIVE.value,
        "condition": condition.model_dump() if condition else None,
        "generated_from": body.message,
        "project_id": project_id,
        "last_triggered_at": None,
        "trigger_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    await collection.insert_one(alert_doc)

    alert_doc.pop("_id", None)
    return AlertResponse(**alert_doc)


@router.get(
    "/",
    response_model=AlertListResponse,
    summary="List all alerts",
    description="Retrieve all alerts with optional filtering by status and severity.",
)
async def list_alerts(
    skip: int = Query(default=0, ge=0, description="Records to skip."),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return."),
    status: AlertStatus | None = Query(default=None, description="Filter by status."),
    severity: AlertSeverity | None = Query(default=None, description="Filter by severity."),
    project_id: str | None = Query(default=None, description="Filter by project ID."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> AlertListResponse:
    collection = _get_collection(db)

    query: dict = {}
    if status is not None:
        query["status"] = status.value
    if severity is not None:
        query["severity"] = severity.value
    if project_id is not None:
        query["project_id"] = project_id

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    alerts = [AlertResponse(**doc) for doc in docs]

    return AlertListResponse(alerts=alerts, total=total, skip=skip, limit=limit)


@router.get(
    "/triggered",
    response_model=AlertListResponse,
    summary="List triggered alerts",
    description="Retrieve all currently triggered (active) alerts that require attention.",
)
async def list_triggered_alerts(
    skip: int = Query(default=0, ge=0, description="Records to skip."),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> AlertListResponse:
    collection = _get_collection(db)

    query = {"status": AlertStatus.TRIGGERED.value}

    total = await collection.count_documents(query)
    cursor = (
        collection.find(query, {"_id": 0}).sort("last_triggered_at", -1).skip(skip).limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    alerts = [AlertResponse(**doc) for doc in docs]

    return AlertListResponse(alerts=alerts, total=total, skip=skip, limit=limit)


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update or dismiss alert",
    description="Update an alert's status (e.g., dismiss), severity, or name.",
)
async def update_alert(
    alert_id: str,
    body: AlertUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> AlertResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"alert_id": alert_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    update_fields: dict = {"updated_at": utc_now()}

    if body.status is not None:
        update_fields["status"] = body.status.value
    if body.severity is not None:
        update_fields["severity"] = body.severity.value
    if body.name is not None:
        update_fields["name"] = body.name

    await collection.update_one({"alert_id": alert_id}, {"$set": update_fields})

    updated_doc = await collection.find_one({"alert_id": alert_id}, {"_id": 0})

    return AlertResponse(**updated_doc)


@router.delete(
    "/{alert_id}",
    response_model=DeleteAlertResponse,
    summary="Delete alert",
    description="Permanently delete an alert.",
)
async def delete_alert(
    alert_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DeleteAlertResponse:
    collection = _get_collection(db)
    doc = await collection.find_one({"alert_id": alert_id})

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    await collection.delete_one({"alert_id": alert_id})

    return DeleteAlertResponse(
        alert_id=alert_id,
        message="Alert has been deleted.",
    )
