"""
Shared pytest fixtures for the ChiefOps backend test suite.

Provides reusable fixtures for database connections, mock AI adapters,
FastAPI test clients, and sample data objects.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.ai.adapter import AIAdapter, AIRequest, AIResponse
from app.ai.mock_adapter import MockAIAdapter
from app.models.base import generate_uuid, utc_now


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Create a disposable test database using a local MongoDB instance.

    The database is dropped after the test completes. Uses a unique
    database name per test to prevent cross-contamination.
    """
    db_name = f"chiefops_test_{generate_uuid()[:8]}"
    client: AsyncIOMotorClient = AsyncIOMotorClient(  # type: ignore[type-arg]
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=3000,
    )

    db = client[db_name]

    yield db

    # Cleanup: drop the entire test database
    await client.drop_database(db_name)
    client.close()


# ---------------------------------------------------------------------------
# AI adapter fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ai_adapter() -> MockAIAdapter:
    """Return a MockAIAdapter instance for testing AI-dependent services."""
    return MockAIAdapter()


# ---------------------------------------------------------------------------
# FastAPI test app and async client
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_app(test_db: AsyncIOMotorDatabase):
    """Create a FastAPI test application with overridden dependencies.

    Replaces the real database dependency with the test database and
    stubs out Redis so tests do not require external services.
    """
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse

    from app.api.v1.endpoints.conversation import router as conversation_router
    from app.api.v1.endpoints.health import router as health_router
    from app.api.v1.endpoints.ingestion import router as ingestion_router
    from app.api.v1.endpoints.people import router as people_router
    from app.api.v1.endpoints.projects import router as projects_router
    from app.database import get_database

    app = FastAPI(
        title="ChiefOps Test API",
        default_response_class=ORJSONResponse,
    )

    # Override the database dependency
    async def _override_get_database():
        yield test_db

    app.dependency_overrides[get_database] = _override_get_database

    # Stub out the Redis dependency used by the health endpoint
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    from app.redis_client import get_redis

    async def _override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_redis] = _override_get_redis

    # Include routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(people_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(conversation_router, prefix="/api/v1")

    yield app


@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx.AsyncClient wired to the test FastAPI app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_person() -> dict:
    """Return a sample Person dict for testing."""
    now = utc_now()
    return {
        "person_id": generate_uuid(),
        "name": "Sarah Chen",
        "email": "sarah.chen@example.com",
        "role": "Engineering Lead",
        "role_source": "ai_identified",
        "department": "Platform Engineering",
        "activity_level": "very_active",
        "last_active_date": now,
        "avatar_url": "https://example.com/avatars/sarah.png",
        "slack_user_id": "U01ABC123",
        "jira_username": "schen",
        "tasks_assigned": 5,
        "tasks_completed": 12,
        "engagement_metrics": {
            "messages_sent": 247,
            "threads_replied": 89,
            "reactions_given": 156,
        },
        "source_ids": [
            {"source": "slack", "source_id": "U01ABC123"},
            {"source": "jira", "source_id": "schen"},
        ],
        "projects": ["proj-001", "proj-002"],
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_project() -> dict:
    """Return a sample Project dict for testing."""
    now = utc_now()
    return {
        "project_id": generate_uuid(),
        "name": "Platform Migration",
        "description": "Migrate legacy platform services to cloud-native architecture.",
        "status": "active",
        "health_score": "at_risk",
        "deadline": datetime(2026, 3, 15, tzinfo=timezone.utc),
        "team_members": ["person-001", "person-002", "person-003"],
        "open_tasks": 14,
        "completed_tasks": 28,
        "total_tasks": 42,
        "key_risks": [
            "Auth service v2 API contract not finalized",
            "Key engineer PTO during cutover window",
        ],
        "key_milestones": [
            {
                "name": "Phase 2: Data Migration",
                "target_date": "2026-02-01",
                "status": "completed",
            },
            {
                "name": "Phase 3: Service Cutover",
                "target_date": "2026-03-15",
                "status": "in_progress",
            },
        ],
        "recent_activity": [],
        "last_analysis_at": now,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_jira_task() -> dict:
    """Return a sample JiraTask dict for testing."""
    now = utc_now()
    return {
        "task_key": "PLAT-401",
        "project_key": "PLAT",
        "summary": "Implement auth service v2 token validation",
        "description": "Update the token validation logic to support the new JWT format.",
        "status": "In Progress",
        "assignee": "Sarah Chen",
        "reporter": "Marcus Rivera",
        "priority": "High",
        "created_date": now,
        "updated_date": now,
        "story_points": 5.0,
        "sprint": "Sprint 14",
        "labels": ["backend", "auth", "migration"],
        "comments": [
            "Started implementation of the new validation flow.",
            "Blocked on API contract finalization.",
        ],
    }


@pytest.fixture
def sample_slack_message() -> dict:
    """Return a sample SlackMessage dict for testing."""
    return {
        "message_id": generate_uuid(),
        "channel": "proj-platform-migration",
        "user_id": "U01ABC123",
        "user_name": "Sarah Chen",
        "text": "The auth service v2 PR is ready for review. @marcus can you take a look?",
        "timestamp": utc_now(),
        "thread_ts": None,
        "reactions": ["eyes", "thumbsup"],
        "reply_count": 0,
    }
