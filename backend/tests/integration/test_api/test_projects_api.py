"""
Integration tests for the projects API endpoints.

Tests project listing, creation, retrieval, and updates
through the REST API with a test MongoDB instance.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.models.base import generate_uuid, utc_now


class TestListProjects:
    """Test the projects listing endpoint."""

    async def test_list_projects(self, async_client: AsyncClient, test_db):
        """GET /api/v1/projects should return a paginated list of projects."""
        collection = test_db["projects"]
        now = utc_now()

        for name in ["Alpha", "Beta", "Gamma"]:
            await collection.insert_one({
                "project_id": generate_uuid(),
                "name": name,
                "description": f"{name} project description.",
                "status": "active",
                "health_score": "healthy",
                "deadline": None,
                "team_members": [],
                "open_tasks": 5,
                "completed_tasks": 10,
                "total_tasks": 15,
                "key_risks": [],
                "key_milestones": [],
                "recent_activity": [],
                "last_analysis_at": None,
                "created_at": now,
                "updated_at": now,
            })

        response = await async_client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["projects"]) >= 3

    async def test_list_projects_empty(self, async_client: AsyncClient):
        """Listing projects when none exist should return an empty list."""
        response = await async_client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []
        assert data["total"] == 0


class TestCreateProject:
    """Test project creation endpoint."""

    async def test_create_project(self, async_client: AsyncClient):
        """POST /api/v1/projects should create a new project."""
        response = await async_client.post(
            "/api/v1/projects",
            json={
                "name": "New Platform",
                "description": "A brand new platform project.",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Platform"
        assert data["description"] == "A brand new platform project."
        assert data["status"] == "active"
        assert "project_id" in data
        assert data["project_id"]  # Non-empty

    async def test_create_project_with_deadline(self, async_client: AsyncClient):
        """Creating a project with a deadline should persist the deadline."""
        deadline = "2026-06-30T00:00:00Z"
        response = await async_client.post(
            "/api/v1/projects",
            json={
                "name": "Deadline Project",
                "deadline": deadline,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Deadline Project"
        assert data["deadline"] is not None

    async def test_create_project_requires_name(self, async_client: AsyncClient):
        """Creating a project without a name should fail validation."""
        response = await async_client.post(
            "/api/v1/projects",
            json={"description": "No name provided."},
        )

        assert response.status_code == 422


class TestGetProject:
    """Test retrieving a single project by ID."""

    async def test_get_project(self, async_client: AsyncClient, test_db):
        """GET /api/v1/projects/{project_id} should return the full project detail."""
        collection = test_db["projects"]
        project_id = generate_uuid()
        now = utc_now()

        await collection.insert_one({
            "project_id": project_id,
            "name": "Detail Test Project",
            "description": "A project for testing detail retrieval.",
            "status": "active",
            "health_score": "at_risk",
            "deadline": datetime(2026, 6, 30, tzinfo=timezone.utc),
            "team_members": ["person-001", "person-002"],
            "open_tasks": 10,
            "completed_tasks": 20,
            "total_tasks": 30,
            "key_risks": ["Dependency on external API"],
            "key_milestones": [],
            "recent_activity": [],
            "last_analysis_at": now,
            "created_at": now,
            "updated_at": now,
        })

        response = await async_client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["name"] == "Detail Test Project"
        assert data["status"] == "active"
        assert data["open_tasks"] == 10
        assert len(data["team_members"]) == 2

    async def test_get_project_not_found(self, async_client: AsyncClient):
        """Requesting a non-existent project should return 404."""
        response = await async_client.get(
            f"/api/v1/projects/{generate_uuid()}"
        )

        assert response.status_code == 404


class TestUpdateProject:
    """Test project update endpoint."""

    async def test_update_project(self, async_client: AsyncClient, test_db):
        """PATCH /api/v1/projects/{project_id} should update specified fields."""
        collection = test_db["projects"]
        project_id = generate_uuid()
        now = utc_now()

        await collection.insert_one({
            "project_id": project_id,
            "name": "Original Name",
            "description": "Original description.",
            "status": "active",
            "health_score": "healthy",
            "deadline": None,
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
        })

        response = await async_client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Updated Name", "description": "Updated description."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description."

    async def test_update_project_not_found(self, async_client: AsyncClient):
        """Updating a non-existent project should return 404."""
        response = await async_client.patch(
            f"/api/v1/projects/{generate_uuid()}",
            json={"name": "Ghost Project"},
        )

        assert response.status_code == 404
