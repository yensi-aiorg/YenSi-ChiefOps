"""
Unit tests for the Person model and related types.

Validates model construction, enum constraints, defaults, and field
validation for the unified person directory records.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.person import (
    ActivityLevel,
    EngagementMetrics,
    Person,
    RoleSource,
    SourceReference,
    SourceSystem,
)


class TestPersonCreationWithDefaults:
    """Test creating a Person with only required fields."""

    def test_person_creation_with_defaults(self):
        person = Person(name="Alice Johnson", role="Developer")

        assert person.name == "Alice Johnson"
        assert person.role == "Developer"
        assert person.email is None
        assert person.department is None
        assert person.avatar_url is None
        assert person.slack_user_id is None
        assert person.jira_username is None
        assert person.tasks_assigned == 0
        assert person.tasks_completed == 0
        assert person.projects == []
        assert person.source_ids == []

        # Defaults
        assert person.role_source == RoleSource.AI_IDENTIFIED
        assert person.activity_level == ActivityLevel.MODERATE

        # person_id should be auto-generated UUID
        assert len(person.person_id) == 36  # UUID v4 format
        assert "-" in person.person_id

        # Timestamps should be set
        assert isinstance(person.created_at, datetime)
        assert isinstance(person.updated_at, datetime)
        assert isinstance(person.last_active_date, datetime)


class TestPersonWithAllFields:
    """Test creating a Person with every field populated."""

    def test_person_with_all_fields(self):
        now = datetime.now(timezone.utc)
        person = Person(
            person_id="test-person-001",
            name="Marcus Rivera",
            email="marcus@example.com",
            source_ids=[
                SourceReference(source=SourceSystem.SLACK, source_id="U02XYZ789"),
                SourceReference(source=SourceSystem.JIRA, source_id="mrivera"),
            ],
            role="Staff Engineer",
            role_source=RoleSource.COO_CORRECTED,
            department="Platform Engineering",
            activity_level=ActivityLevel.VERY_ACTIVE,
            last_active_date=now,
            avatar_url="https://example.com/avatar.png",
            slack_user_id="U02XYZ789",
            jira_username="mrivera",
            tasks_assigned=3,
            tasks_completed=15,
            engagement_metrics=EngagementMetrics(
                messages_sent=150,
                threads_replied=42,
                reactions_given=88,
            ),
            projects=["proj-001", "proj-002"],
        )

        assert person.person_id == "test-person-001"
        assert person.name == "Marcus Rivera"
        assert person.email == "marcus@example.com"
        assert len(person.source_ids) == 2
        assert person.source_ids[0].source == SourceSystem.SLACK
        assert person.source_ids[0].source_id == "U02XYZ789"
        assert person.source_ids[1].source == SourceSystem.JIRA
        assert person.role == "Staff Engineer"
        assert person.role_source == RoleSource.COO_CORRECTED
        assert person.department == "Platform Engineering"
        assert person.activity_level == ActivityLevel.VERY_ACTIVE
        assert person.last_active_date == now
        assert person.avatar_url == "https://example.com/avatar.png"
        assert person.slack_user_id == "U02XYZ789"
        assert person.jira_username == "mrivera"
        assert person.tasks_assigned == 3
        assert person.tasks_completed == 15
        assert person.engagement_metrics.messages_sent == 150
        assert person.engagement_metrics.threads_replied == 42
        assert person.engagement_metrics.reactions_given == 88
        assert person.projects == ["proj-001", "proj-002"]

    def test_person_serialization_roundtrip(self):
        person = Person(name="Test User", role="Developer")
        data = person.model_dump()
        restored = Person(**data)

        assert restored.name == person.name
        assert restored.role == person.role
        assert restored.person_id == person.person_id


class TestPersonActivityLevelEnum:
    """Test ActivityLevel enum values and validation."""

    def test_person_activity_level_enum(self):
        assert ActivityLevel.VERY_ACTIVE == "very_active"
        assert ActivityLevel.ACTIVE == "active"
        assert ActivityLevel.MODERATE == "moderate"
        assert ActivityLevel.QUIET == "quiet"
        assert ActivityLevel.INACTIVE == "inactive"

    def test_all_activity_levels_valid_on_person(self):
        for level in ActivityLevel:
            person = Person(name="Test", role="Dev", activity_level=level)
            assert person.activity_level == level

    def test_invalid_activity_level_rejected(self):
        with pytest.raises(ValidationError):
            Person(name="Test", role="Dev", activity_level="nonexistent")


class TestPersonRoleSourceEnum:
    """Test RoleSource enum values."""

    def test_person_role_source_enum(self):
        assert RoleSource.AI_IDENTIFIED == "ai_identified"
        assert RoleSource.COO_CORRECTED == "coo_corrected"

    def test_ai_identified_is_default(self):
        person = Person(name="Test", role="Dev")
        assert person.role_source == RoleSource.AI_IDENTIFIED

    def test_coo_corrected_can_be_set(self):
        person = Person(
            name="Test",
            role="Dev",
            role_source=RoleSource.COO_CORRECTED,
        )
        assert person.role_source == RoleSource.COO_CORRECTED


class TestEngagementMetricsDefaults:
    """Test EngagementMetrics default values."""

    def test_engagement_metrics_defaults(self):
        metrics = EngagementMetrics()
        assert metrics.messages_sent == 0
        assert metrics.threads_replied == 0
        assert metrics.reactions_given == 0

    def test_engagement_metrics_with_values(self):
        metrics = EngagementMetrics(
            messages_sent=100,
            threads_replied=25,
            reactions_given=50,
        )
        assert metrics.messages_sent == 100
        assert metrics.threads_replied == 25
        assert metrics.reactions_given == 50

    def test_engagement_metrics_rejects_negative(self):
        with pytest.raises(ValidationError):
            EngagementMetrics(messages_sent=-1)

    def test_person_default_engagement_metrics(self):
        person = Person(name="Test", role="Dev")
        assert person.engagement_metrics.messages_sent == 0
        assert person.engagement_metrics.threads_replied == 0
        assert person.engagement_metrics.reactions_given == 0


class TestPersonValidation:
    """Test field validation constraints."""

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            Person(name="", role="Dev")

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            Person(name="A" * 201, role="Dev")

    def test_tasks_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            Person(name="Test", role="Dev", tasks_assigned=-1)

    def test_source_reference_requires_source_id(self):
        with pytest.raises(ValidationError):
            SourceReference(source=SourceSystem.SLACK, source_id="")
