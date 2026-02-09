"""
Integration tests for the people directory API endpoints.

Tests listing people, retrieving person details, and applying
COO corrections through the REST API.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.base import generate_uuid, utc_now
from app.models.person import ActivityLevel, RoleSource


class TestListPeople:
    """Test the people listing endpoint."""

    async def test_list_people(self, async_client: AsyncClient, test_db):
        """GET /api/v1/people should return a paginated list of people."""
        # Insert test people
        collection = test_db["people"]
        now = utc_now()

        for i, name in enumerate(["Alice Johnson", "Bob Smith", "Charlie Davis"]):
            await collection.insert_one({
                "person_id": generate_uuid(),
                "name": name,
                "email": f"{name.split()[0].lower()}@example.com",
                "role": "Developer",
                "role_source": RoleSource.AI_IDENTIFIED.value,
                "department": "Engineering",
                "activity_level": ActivityLevel.ACTIVE.value,
                "last_active_date": now,
                "tasks_assigned": i,
                "tasks_completed": i * 2,
                "projects": [],
                "created_at": now,
                "updated_at": now,
            })

        response = await async_client.get("/api/v1/people")

        assert response.status_code == 200
        data = response.json()
        assert "people" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["people"]) >= 3

        # People should have required fields
        person = data["people"][0]
        assert "person_id" in person
        assert "name" in person
        assert "role" in person
        assert "activity_level" in person

    async def test_list_people_empty(self, async_client: AsyncClient):
        """Listing people when none exist should return an empty list."""
        response = await async_client.get("/api/v1/people")

        assert response.status_code == 200
        data = response.json()
        assert data["people"] == []
        assert data["total"] == 0

    async def test_list_people_with_filters(self, async_client: AsyncClient, test_db):
        """People listing should support filter parameters."""
        collection = test_db["people"]
        now = utc_now()

        await collection.insert_one({
            "person_id": generate_uuid(),
            "name": "Diana Expert",
            "email": "diana@example.com",
            "role": "Staff Engineer",
            "role_source": RoleSource.AI_IDENTIFIED.value,
            "department": "Platform Engineering",
            "activity_level": ActivityLevel.VERY_ACTIVE.value,
            "last_active_date": now,
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "projects": [],
            "created_at": now,
            "updated_at": now,
        })

        response = await async_client.get(
            "/api/v1/people",
            params={"activity_level": "very_active"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for person in data["people"]:
            assert person["activity_level"] == "very_active"


class TestGetPerson:
    """Test retrieving a single person by ID."""

    async def test_get_person(self, async_client: AsyncClient, test_db):
        """GET /api/v1/people/{person_id} should return the full person detail."""
        collection = test_db["people"]
        person_id = generate_uuid()
        now = utc_now()

        await collection.insert_one({
            "person_id": person_id,
            "name": "Sarah Chen",
            "email": "sarah@example.com",
            "role": "Engineering Lead",
            "role_source": RoleSource.AI_IDENTIFIED.value,
            "department": "Platform Engineering",
            "activity_level": ActivityLevel.VERY_ACTIVE.value,
            "last_active_date": now,
            "avatar_url": "https://example.com/sarah.png",
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
            ],
            "projects": ["proj-001"],
            "created_at": now,
            "updated_at": now,
        })

        response = await async_client.get(f"/api/v1/people/{person_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["person_id"] == person_id
        assert data["name"] == "Sarah Chen"
        assert data["email"] == "sarah@example.com"
        assert data["role"] == "Engineering Lead"
        assert data["department"] == "Platform Engineering"
        assert data["tasks_assigned"] == 5
        assert data["tasks_completed"] == 12
        assert data["engagement_metrics"]["messages_sent"] == 247

    async def test_get_person_not_found(self, async_client: AsyncClient):
        """Requesting a non-existent person should return 404."""
        response = await async_client.get(
            f"/api/v1/people/{generate_uuid()}"
        )

        assert response.status_code == 404


class TestCorrectPerson:
    """Test applying COO corrections to a person record."""

    async def test_correct_person(self, async_client: AsyncClient, test_db):
        """PATCH /api/v1/people/{person_id} should update specified fields."""
        collection = test_db["people"]
        person_id = generate_uuid()
        now = utc_now()

        await collection.insert_one({
            "person_id": person_id,
            "name": "Marcus Rivera",
            "email": "marcus@example.com",
            "role": "Senior Backend Developer",
            "role_source": RoleSource.AI_IDENTIFIED.value,
            "department": "Engineering",
            "activity_level": ActivityLevel.ACTIVE.value,
            "last_active_date": now,
            "tasks_assigned": 3,
            "tasks_completed": 15,
            "projects": [],
            "created_at": now,
            "updated_at": now,
        })

        # Apply correction
        response = await async_client.patch(
            f"/api/v1/people/{person_id}",
            json={"role": "Staff Engineer", "department": "Platform Engineering"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["person_id"] == person_id
        assert "role" in data["updated_fields"]
        assert "department" in data["updated_fields"]

        # Verify the correction was persisted
        doc = await collection.find_one({"person_id": person_id})
        assert doc["role"] == "Staff Engineer"
        assert doc["role_source"] == RoleSource.COO_CORRECTED.value
        assert doc["department"] == "Platform Engineering"

    async def test_correct_person_no_changes(self, async_client: AsyncClient, test_db):
        """Patching with the same values should report no changes."""
        collection = test_db["people"]
        person_id = generate_uuid()
        now = utc_now()

        await collection.insert_one({
            "person_id": person_id,
            "name": "Test Person",
            "role": "Developer",
            "role_source": RoleSource.AI_IDENTIFIED.value,
            "activity_level": ActivityLevel.ACTIVE.value,
            "last_active_date": now,
            "created_at": now,
            "updated_at": now,
        })

        response = await async_client.patch(
            f"/api/v1/people/{person_id}",
            json={"role": "Developer"},  # Same as current
        )

        assert response.status_code == 200
        data = response.json()
        assert data["updated_fields"] == []
        assert "No changes" in data["message"]

    async def test_correct_person_not_found(self, async_client: AsyncClient):
        """Patching a non-existent person should return 404."""
        response = await async_client.patch(
            f"/api/v1/people/{generate_uuid()}",
            json={"role": "New Role"},
        )

        assert response.status_code == 404
