"""
Main API v1 router.

Aggregates all endpoint sub-routers under the /api/v1 prefix.
Import this router from the FastAPI application entry point and include it:

    from app.api.v1.router import api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.conversation import router as conversation_router
from app.api.v1.endpoints.dashboards import router as dashboards_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.ingestion import router as ingestion_router
from app.api.v1.endpoints.people import router as people_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.settings import router as settings_router
from app.api.v1.endpoints.websocket import router as websocket_router
from app.api.v1.endpoints.widgets import router as widgets_router

api_v1_router = APIRouter()

# Health checks (no prefix -- mounted at /api/v1/health and /api/v1/ready)
api_v1_router.include_router(health_router)

# Data ingestion -- /api/v1/ingest/*
api_v1_router.include_router(ingestion_router)

# Conversation / chat -- /api/v1/conversation/*
api_v1_router.include_router(conversation_router)

# People directory -- /api/v1/people/*
api_v1_router.include_router(people_router)

# Projects -- /api/v1/projects/*
api_v1_router.include_router(projects_router)

# Dashboards -- /api/v1/dashboards/*
api_v1_router.include_router(dashboards_router)

# Widgets -- /api/v1/widgets/*
api_v1_router.include_router(widgets_router)

# Reports -- /api/v1/reports/*
api_v1_router.include_router(reports_router)

# Alerts -- /api/v1/alerts/*
api_v1_router.include_router(alerts_router)

# Settings & data management -- /api/v1/settings/*
api_v1_router.include_router(settings_router)

# WebSocket endpoints -- /api/v1/ws/*
api_v1_router.include_router(websocket_router)
