"""
Application settings endpoints.

Manages runtime configuration, data export, and data purge operations.
Settings are persisted in MongoDB so they survive restarts.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS: dict[str, Any] = {
    "settings_id": "singleton",
    "ai_adapter": "cli",
    "ai_cli_tool": "claude",
    "openrouter_model": "anthropic/claude-sonnet-4",
    "pii_redaction_enabled": True,
    "auto_analyze_on_ingest": True,
    "dashboard_refresh_interval_seconds": 300,
    "notification_preferences": {
        "alert_email": False,
        "alert_in_app": True,
    },
    "data_retention_days": 0,
    "theme": "system",
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SettingsResponse(BaseModel):
    """Current application settings."""

    ai_adapter: str = Field(default="cli", description="AI backend: 'openrouter' or 'cli'.")
    ai_cli_tool: str = Field(default="claude", description="CLI tool name when ai_adapter=cli.")
    openrouter_model: str = Field(
        default="anthropic/claude-sonnet-4", description="OpenRouter model ID."
    )
    pii_redaction_enabled: bool = Field(
        default=True, description="Whether PII redaction is active."
    )
    auto_analyze_on_ingest: bool = Field(
        default=True,
        description="Automatically run project analysis after ingestion.",
    )
    dashboard_refresh_interval_seconds: int = Field(
        default=300,
        description="Default dashboard auto-refresh interval.",
    )
    notification_preferences: dict[str, Any] = Field(
        default_factory=lambda: {"alert_email": False, "alert_in_app": True},
        description="Notification channel preferences.",
    )
    data_retention_days: int = Field(
        default=0,
        ge=0,
        description="Days to retain data (0 = unlimited).",
    )
    theme: str = Field(default="system", description="UI theme: 'light', 'dark', or 'system'.")
    updated_at: datetime | None = Field(default=None, description="Last settings update.")


class SettingsUpdateRequest(BaseModel):
    """Request to update one or more settings."""

    ai_adapter: str | None = Field(default=None, description="AI backend.")
    ai_cli_tool: str | None = Field(default=None, description="CLI tool name.")
    openrouter_model: str | None = Field(default=None, description="OpenRouter model ID.")
    pii_redaction_enabled: bool | None = Field(default=None, description="PII redaction toggle.")
    auto_analyze_on_ingest: bool | None = Field(default=None, description="Auto-analyze toggle.")
    dashboard_refresh_interval_seconds: int | None = Field(
        default=None, ge=10, description="Dashboard refresh interval."
    )
    notification_preferences: dict[str, Any] | None = Field(
        default=None, description="Notification preferences."
    )
    data_retention_days: int | None = Field(default=None, ge=0, description="Data retention days.")
    theme: str | None = Field(default=None, description="UI theme.")


class DataExportResponse(BaseModel):
    """Response containing exported data."""

    export_id: str = Field(..., description="Export identifier.")
    collections: list[str] = Field(default_factory=list, description="Collections included.")
    total_documents: int = Field(default=0, description="Total documents exported.")
    message: str = Field(..., description="Human-readable status message.")


class DataClearResponse(BaseModel):
    """Response after clearing all data."""

    collections_cleared: list[str] = Field(
        default_factory=list, description="Collections that were cleared."
    )
    total_deleted: int = Field(default=0, description="Total documents deleted.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    return db["settings"]


async def _ensure_settings(db: AsyncIOMotorDatabase) -> dict[str, Any]:  # type: ignore[type-arg]
    """Return the settings document, creating it with defaults if it does not exist."""
    collection = _get_collection(db)
    doc = await collection.find_one({"settings_id": "singleton"}, {"_id": 0})
    if doc is None:
        now = utc_now()
        doc = {**DEFAULT_SETTINGS, "created_at": now, "updated_at": now}
        await collection.insert_one(doc)
        doc.pop("_id", None)
    return doc


# Collections that hold user data (not including settings itself)
DATA_COLLECTIONS = [
    "people",
    "projects",
    "project_analyses",
    "conversation_messages",
    "ingestion_jobs",
    "ingestion_file_store",
    "dashboards",
    "widgets",
    "reports",
    "alerts",
    "memory_facts",
    "extracted_documents",
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get current settings",
    description="Retrieve the current application configuration.",
)
async def get_settings(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> SettingsResponse:
    doc = await _ensure_settings(db)

    return SettingsResponse(
        ai_adapter=doc.get("ai_adapter", DEFAULT_SETTINGS["ai_adapter"]),
        ai_cli_tool=doc.get("ai_cli_tool", DEFAULT_SETTINGS["ai_cli_tool"]),
        openrouter_model=doc.get("openrouter_model", DEFAULT_SETTINGS["openrouter_model"]),
        pii_redaction_enabled=doc.get(
            "pii_redaction_enabled", DEFAULT_SETTINGS["pii_redaction_enabled"]
        ),
        auto_analyze_on_ingest=doc.get(
            "auto_analyze_on_ingest", DEFAULT_SETTINGS["auto_analyze_on_ingest"]
        ),
        dashboard_refresh_interval_seconds=doc.get(
            "dashboard_refresh_interval_seconds",
            DEFAULT_SETTINGS["dashboard_refresh_interval_seconds"],
        ),
        notification_preferences=doc.get(
            "notification_preferences",
            DEFAULT_SETTINGS["notification_preferences"],
        ),
        data_retention_days=doc.get("data_retention_days", DEFAULT_SETTINGS["data_retention_days"]),
        theme=doc.get("theme", DEFAULT_SETTINGS["theme"]),
        updated_at=doc.get("updated_at"),
    )


@router.patch(
    "",
    response_model=SettingsResponse,
    summary="Update settings",
    description="Update one or more application settings. Only provided fields are changed.",
)
async def update_settings(
    body: SettingsUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> SettingsResponse:
    await _ensure_settings(db)
    collection = _get_collection(db)

    update_fields: dict[str, Any] = {"updated_at": utc_now()}

    if body.ai_adapter is not None:
        if body.ai_adapter not in ("openrouter", "cli"):
            raise HTTPException(
                status_code=422,
                detail="ai_adapter must be 'openrouter' or 'cli'.",
            )
        update_fields["ai_adapter"] = body.ai_adapter

    if body.ai_cli_tool is not None:
        update_fields["ai_cli_tool"] = body.ai_cli_tool

    if body.openrouter_model is not None:
        update_fields["openrouter_model"] = body.openrouter_model

    if body.pii_redaction_enabled is not None:
        update_fields["pii_redaction_enabled"] = body.pii_redaction_enabled

    if body.auto_analyze_on_ingest is not None:
        update_fields["auto_analyze_on_ingest"] = body.auto_analyze_on_ingest

    if body.dashboard_refresh_interval_seconds is not None:
        update_fields["dashboard_refresh_interval_seconds"] = (
            body.dashboard_refresh_interval_seconds
        )

    if body.notification_preferences is not None:
        update_fields["notification_preferences"] = body.notification_preferences

    if body.data_retention_days is not None:
        update_fields["data_retention_days"] = body.data_retention_days

    if body.theme is not None:
        if body.theme not in ("light", "dark", "system"):
            raise HTTPException(
                status_code=422,
                detail="theme must be 'light', 'dark', or 'system'.",
            )
        update_fields["theme"] = body.theme

    await collection.update_one({"settings_id": "singleton"}, {"$set": update_fields})

    doc = await collection.find_one({"settings_id": "singleton"}, {"_id": 0})

    return SettingsResponse(
        ai_adapter=doc.get("ai_adapter", DEFAULT_SETTINGS["ai_adapter"]),
        ai_cli_tool=doc.get("ai_cli_tool", DEFAULT_SETTINGS["ai_cli_tool"]),
        openrouter_model=doc.get("openrouter_model", DEFAULT_SETTINGS["openrouter_model"]),
        pii_redaction_enabled=doc.get(
            "pii_redaction_enabled", DEFAULT_SETTINGS["pii_redaction_enabled"]
        ),
        auto_analyze_on_ingest=doc.get(
            "auto_analyze_on_ingest", DEFAULT_SETTINGS["auto_analyze_on_ingest"]
        ),
        dashboard_refresh_interval_seconds=doc.get(
            "dashboard_refresh_interval_seconds",
            DEFAULT_SETTINGS["dashboard_refresh_interval_seconds"],
        ),
        notification_preferences=doc.get(
            "notification_preferences",
            DEFAULT_SETTINGS["notification_preferences"],
        ),
        data_retention_days=doc.get("data_retention_days", DEFAULT_SETTINGS["data_retention_days"]),
        theme=doc.get("theme", DEFAULT_SETTINGS["theme"]),
        updated_at=doc.get("updated_at"),
    )


@router.post(
    "/data/export",
    summary="Export all data",
    description="Export all application data as a JSON file download. "
    "Includes people, projects, conversations, dashboards, reports, and alerts.",
)
async def export_data(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> StreamingResponse:
    import json

    export: dict[str, Any] = {
        "exported_at": utc_now().isoformat(),
        "collections": {},
    }

    total_docs = 0

    for col_name in DATA_COLLECTIONS:
        try:
            col = db[col_name]
            docs = await col.find({}, {"_id": 0}).to_list(length=None)

            # Convert datetime objects for JSON serialization
            serialized = json.loads(json.dumps(docs, default=str))
            export["collections"][col_name] = serialized
            total_docs += len(docs)
        except Exception as exc:
            logger.warning(f"Failed to export collection {col_name}", exc_info=exc)
            export["collections"][col_name] = {"error": str(exc)}

    export["total_documents"] = total_docs

    json_bytes = json.dumps(export, indent=2, default=str).encode("utf-8")

    return StreamingResponse(
        iter([json_bytes]),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="chiefops_export.json"',
            "Content-Length": str(len(json_bytes)),
        },
    )


@router.delete(
    "/data",
    response_model=DataClearResponse,
    summary="Clear all data",
    description="Permanently delete ALL application data across all collections. "
    "This action is irreversible. Requires a confirmation query parameter.",
)
async def clear_data(
    confirm: bool = Query(
        ...,
        description="Must be set to true to confirm data deletion.",
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> DataClearResponse:
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Data deletion requires confirm=true query parameter.",
        )

    cleared: list[str] = []
    total_deleted = 0

    for col_name in DATA_COLLECTIONS:
        try:
            col = db[col_name]
            result = await col.delete_many({})
            if result.deleted_count > 0:
                cleared.append(col_name)
                total_deleted += result.deleted_count
        except Exception as exc:
            logger.warning(f"Failed to clear collection {col_name}", exc_info=exc)

    return DataClearResponse(
        collections_cleared=cleared,
        total_deleted=total_deleted,
        message=f"Cleared {total_deleted} documents across {len(cleared)} collections.",
    )
