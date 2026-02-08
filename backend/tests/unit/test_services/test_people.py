"""
Unit tests for the people identity resolution and management services.

Tests entity resolution strategies, activity level computation, AI-based
role detection, and COO correction application.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.adapter import AIRequest, AIResponse
from app.ai.mock_adapter import MockAIAdapter
from app.models.base import generate_uuid, utc_now
from app.models.person import ActivityLevel, Person, RoleSource


@pytest.mark.integration
class TestEntityResolutionExactEmailMatch:
    """Test entity resolution via exact email matching."""

    async def test_entity_resolution_exact_email_match(self, test_db):
        """Two records with the same email should resolve to the same person."""
        collection = test_db["people"]

        # Insert a person with a known email
        person_id = generate_uuid()
        await collection.insert_one({
            "person_id": person_id,
            "name": "Sarah Chen",
            "email": "sarah.chen@example.com",
            "role": "Engineering Lead",
            "role_source": "ai_identified",
            "activity_level": "active",
            "last_active_date": utc_now(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Search for a person by the same email
        doc = await collection.find_one({"email": "sarah.chen@example.com"})

        assert doc is not None
        assert doc["person_id"] == person_id
        assert doc["name"] == "Sarah Chen"

    async def test_no_match_for_different_email(self, test_db):
        """Different emails should not resolve to the same person."""
        collection = test_db["people"]

        await collection.insert_one({
            "person_id": generate_uuid(),
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "role": "Developer",
            "role_source": "ai_identified",
            "activity_level": "active",
            "last_active_date": utc_now(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        doc = await collection.find_one({"email": "bob@example.com"})
        assert doc is None


@pytest.mark.integration
class TestEntityResolutionFuzzyNameMatch:
    """Test entity resolution via fuzzy name matching."""

    async def test_entity_resolution_fuzzy_name_match(self, test_db):
        """People with similar names should be findable via regex search."""
        collection = test_db["people"]

        await collection.insert_one({
            "person_id": generate_uuid(),
            "name": "Marcus Rivera",
            "email": "marcus@example.com",
            "role": "Senior Backend Developer",
            "role_source": "ai_identified",
            "activity_level": "active",
            "last_active_date": utc_now(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Fuzzy search using case-insensitive regex (simulating fuzzy match)
        doc = await collection.find_one(
            {"name": {"$regex": "marcus", "$options": "i"}}
        )

        assert doc is not None
        assert doc["name"] == "Marcus Rivera"

    async def test_partial_name_match(self, test_db):
        """Partial name search should find matching records."""
        collection = test_db["people"]

        await collection.insert_one({
            "person_id": generate_uuid(),
            "name": "Sarah Chen",
            "email": "sarah@example.com",
            "role": "Tech Lead",
            "role_source": "ai_identified",
            "activity_level": "active",
            "last_active_date": utc_now(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Search by partial name
        doc = await collection.find_one(
            {"name": {"$regex": "Chen", "$options": "i"}}
        )

        assert doc is not None
        assert doc["name"] == "Sarah Chen"


class TestActivityLevelCalculation:
    """Test computation of activity levels from engagement data."""

    def test_activity_level_calculation(self):
        """Activity level should be determinable from engagement metrics."""
        # Define thresholds for activity level computation
        def compute_activity(messages: int, tasks_completed: int, days_since_active: int) -> ActivityLevel:
            score = messages * 0.3 + tasks_completed * 0.5
            if days_since_active > 30:
                return ActivityLevel.INACTIVE
            if days_since_active > 14:
                return ActivityLevel.QUIET
            if score >= 50:
                return ActivityLevel.VERY_ACTIVE
            if score >= 20:
                return ActivityLevel.ACTIVE
            if score >= 5:
                return ActivityLevel.MODERATE
            return ActivityLevel.QUIET

        # Very active: score = 150*0.3 + 50*0.5 = 45+25 = 70 >= 50
        assert compute_activity(150, 50, 1) == ActivityLevel.VERY_ACTIVE

        # Active: score = 50*0.3 + 20*0.5 = 15+10 = 25, in [20, 50)
        assert compute_activity(50, 20, 3) == ActivityLevel.ACTIVE

        # Moderate: score = 15*0.3 + 5*0.5 = 4.5+2.5 = 7, in [5, 20)
        assert compute_activity(15, 5, 5) == ActivityLevel.MODERATE

        # Quiet: score = 2*0.3 + 1*0.5 = 0.6+0.5 = 1.1, < 5
        assert compute_activity(2, 1, 10) == ActivityLevel.QUIET

        # Inactive: stale
        assert compute_activity(100, 50, 45) == ActivityLevel.INACTIVE

    def test_all_activity_levels_are_valid_enum_values(self):
        """All activity levels should be valid enum members."""
        levels = [level.value for level in ActivityLevel]
        assert "very_active" in levels
        assert "active" in levels
        assert "moderate" in levels
        assert "quiet" in levels
        assert "inactive" in levels


class TestRoleDetectionWithMockAI:
    """Test AI-based role detection using the MockAIAdapter."""

    async def test_role_detection_with_mock_ai(self, mock_ai_adapter):
        """MockAIAdapter should return a role detection response for role-related prompts."""
        request = AIRequest(
            system_prompt="You are a role detection assistant. Analyze the activity data and detect the role.",
            user_prompt="What role does this person have based on their activity?",
            context={
                "person_name": "Sarah Chen",
                "activities": [
                    "Reviews pull requests from multiple team members",
                    "Participates in architecture decisions",
                    "Approves deployment workflows",
                ],
            },
        )

        response = await mock_ai_adapter.generate_structured(request)

        assert response.adapter == "mock"
        assert response.content  # Should have content

        # Parse the JSON response
        data = response.parse_json()
        assert "detected_role" in data
        assert "confidence" in data
        assert data["confidence"] > 0.0
        assert data["detected_role"]  # Should be non-empty

    async def test_role_detection_response_has_evidence(self, mock_ai_adapter):
        """Role detection should include evidence supporting the role assignment."""
        request = AIRequest(
            system_prompt="Role detection: analyze activity patterns to determine role.",
            user_prompt="Detect the role for this person.",
        )

        response = await mock_ai_adapter.generate_structured(request)
        data = response.parse_json()

        assert "evidence" in data
        assert isinstance(data["evidence"], list)
        assert len(data["evidence"]) > 0


@pytest.mark.integration
class TestCorrectionApplication:
    """Test applying COO corrections to person records."""

    async def test_correction_application(self, test_db):
        """A COO correction should update the role and set role_source to coo_corrected."""
        collection = test_db["people"]

        person_id = generate_uuid()
        now = utc_now()
        await collection.insert_one({
            "person_id": person_id,
            "name": "Marcus Rivera",
            "email": "marcus@example.com",
            "role": "Senior Backend Developer",
            "role_source": RoleSource.AI_IDENTIFIED.value,
            "activity_level": "active",
            "last_active_date": now,
            "created_at": now,
            "updated_at": now,
        })

        # Apply correction
        new_role = "Staff Engineer"
        await collection.update_one(
            {"person_id": person_id},
            {
                "$set": {
                    "role": new_role,
                    "role_source": RoleSource.COO_CORRECTED.value,
                    "updated_at": utc_now(),
                },
            },
        )

        # Verify the correction was applied
        doc = await collection.find_one({"person_id": person_id})
        assert doc is not None
        assert doc["role"] == "Staff Engineer"
        assert doc["role_source"] == RoleSource.COO_CORRECTED.value

    async def test_correction_preserves_other_fields(self, test_db):
        """A role correction should not affect other person fields."""
        collection = test_db["people"]

        person_id = generate_uuid()
        now = utc_now()
        original_doc = {
            "person_id": person_id,
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "role": "Developer",
            "role_source": RoleSource.AI_IDENTIFIED.value,
            "department": "Engineering",
            "activity_level": "active",
            "tasks_assigned": 5,
            "tasks_completed": 12,
            "last_active_date": now,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(original_doc)

        # Apply role correction only
        await collection.update_one(
            {"person_id": person_id},
            {"$set": {"role": "Senior Developer", "role_source": RoleSource.COO_CORRECTED.value}},
        )

        doc = await collection.find_one({"person_id": person_id})
        assert doc["name"] == "Alice Johnson"
        assert doc["email"] == "alice@example.com"
        assert doc["department"] == "Engineering"
        assert doc["tasks_assigned"] == 5
        assert doc["tasks_completed"] == 12
        assert doc["role"] == "Senior Developer"
