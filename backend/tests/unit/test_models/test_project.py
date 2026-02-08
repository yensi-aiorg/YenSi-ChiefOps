"""
Unit tests for the Project model and related types.

Validates model construction, enum constraints, embedded sub-documents,
health score bounds, and serialization for project records.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.project import (
    Milestone,
    MilestoneStatus,
    Project,
    ProjectMember,
    ProjectStatus,
    SprintHealth,
    TaskSummary,
)


class TestProjectCreation:
    """Test creating a Project with required and default fields."""

    def test_project_creation(self):
        project = Project(name="Platform Migration")

        assert project.name == "Platform Migration"
        assert project.description == ""
        assert project.status == ProjectStatus.ON_TRACK
        assert project.completion_percentage == 0.0
        assert project.deadline is None
        assert project.milestones == []
        assert project.people_involved == []
        assert project.health_score == 50
        assert project.key_risks == []
        assert project.missing_tasks == []
        assert project.technical_concerns == []
        assert project.slack_channels == []
        assert project.jira_project_keys == []
        assert project.sprint_health is None
        assert project.gap_analysis is None
        assert project.technical_feasibility is None

        # Auto-generated fields
        assert len(project.project_id) == 36
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)
        assert isinstance(project.last_analyzed_at, datetime)

    def test_project_with_all_fields(self):
        now = datetime.now(timezone.utc)
        project = Project(
            project_id="proj-001",
            name="Cloud Migration",
            description="Full infrastructure migration to AWS.",
            status=ProjectStatus.AT_RISK,
            completion_percentage=65.5,
            deadline=datetime(2026, 6, 30, tzinfo=timezone.utc),
            milestones=[
                Milestone(
                    name="Phase 1: Planning",
                    target_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
                    status=MilestoneStatus.COMPLETED,
                    description="Complete infrastructure assessment.",
                ),
            ],
            people_involved=[
                ProjectMember(
                    person_id="person-001",
                    name="Sarah Chen",
                    role="tech_lead",
                    activity_level="very_active",
                ),
            ],
            task_summary=TaskSummary(
                total=42,
                completed=28,
                in_progress=8,
                blocked=2,
                to_do=4,
            ),
            health_score=62,
            key_risks=["Vendor lock-in risk"],
            slack_channels=["proj-cloud-migration"],
            jira_project_keys=["CLOUD", "INFRA"],
        )

        assert project.project_id == "proj-001"
        assert project.name == "Cloud Migration"
        assert project.status == ProjectStatus.AT_RISK
        assert project.completion_percentage == 65.5
        assert len(project.milestones) == 1
        assert project.milestones[0].name == "Phase 1: Planning"
        assert len(project.people_involved) == 1
        assert project.people_involved[0].name == "Sarah Chen"
        assert project.task_summary.total == 42
        assert project.health_score == 62
        assert project.jira_project_keys == ["CLOUD", "INFRA"]

    def test_project_serialization_roundtrip(self):
        project = Project(name="Test Project")
        data = project.model_dump()
        restored = Project(**data)

        assert restored.name == project.name
        assert restored.project_id == project.project_id
        assert restored.health_score == project.health_score


class TestProjectStatusEnum:
    """Test ProjectStatus enum values and validation."""

    def test_project_status_enum(self):
        assert ProjectStatus.ON_TRACK == "on_track"
        assert ProjectStatus.AT_RISK == "at_risk"
        assert ProjectStatus.BEHIND == "behind"
        assert ProjectStatus.COMPLETED == "completed"

    def test_all_statuses_valid_on_project(self):
        for status in ProjectStatus:
            project = Project(name="Test", status=status)
            assert project.status == status

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            Project(name="Test", status="invalid_status")

    def test_default_status_is_on_track(self):
        project = Project(name="Test")
        assert project.status == ProjectStatus.ON_TRACK


class TestTaskSummaryDefaults:
    """Test TaskSummary default values."""

    def test_task_summary_defaults(self):
        summary = TaskSummary()

        assert summary.total == 0
        assert summary.completed == 0
        assert summary.in_progress == 0
        assert summary.blocked == 0
        assert summary.to_do == 0

    def test_task_summary_with_values(self):
        summary = TaskSummary(
            total=100,
            completed=40,
            in_progress=30,
            blocked=5,
            to_do=25,
        )
        assert summary.total == 100
        assert summary.completed == 40
        assert summary.in_progress == 30
        assert summary.blocked == 5
        assert summary.to_do == 25

    def test_task_summary_rejects_negative(self):
        with pytest.raises(ValidationError):
            TaskSummary(total=-1)

    def test_project_default_task_summary(self):
        project = Project(name="Test")
        assert project.task_summary.total == 0
        assert project.task_summary.completed == 0


class TestMilestoneCreation:
    """Test Milestone model creation and validation."""

    def test_milestone_creation(self):
        target = datetime(2026, 3, 15, tzinfo=timezone.utc)
        milestone = Milestone(
            name="Beta Release",
            target_date=target,
        )

        assert milestone.name == "Beta Release"
        assert milestone.target_date == target
        assert milestone.status == MilestoneStatus.PENDING
        assert milestone.description == ""

    def test_milestone_with_all_fields(self):
        target = datetime(2026, 6, 1, tzinfo=timezone.utc)
        milestone = Milestone(
            name="GA Release",
            target_date=target,
            status=MilestoneStatus.IN_PROGRESS,
            description="General availability release to production.",
        )

        assert milestone.name == "GA Release"
        assert milestone.status == MilestoneStatus.IN_PROGRESS
        assert milestone.description == "General availability release to production."

    def test_milestone_status_enum_values(self):
        assert MilestoneStatus.PENDING == "pending"
        assert MilestoneStatus.IN_PROGRESS == "in_progress"
        assert MilestoneStatus.COMPLETED == "completed"
        assert MilestoneStatus.MISSED == "missed"

    def test_milestone_requires_name(self):
        with pytest.raises(ValidationError):
            Milestone(
                name="",
                target_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )


class TestHealthScoreRange:
    """Test health_score field boundary constraints."""

    def test_health_score_range(self):
        # Valid boundary values
        project_zero = Project(name="Test", health_score=0)
        assert project_zero.health_score == 0

        project_hundred = Project(name="Test", health_score=100)
        assert project_hundred.health_score == 100

        project_mid = Project(name="Test", health_score=50)
        assert project_mid.health_score == 50

    def test_health_score_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            Project(name="Test", health_score=-1)

    def test_health_score_above_hundred_rejected(self):
        with pytest.raises(ValidationError):
            Project(name="Test", health_score=101)

    def test_default_health_score_is_50(self):
        project = Project(name="Test")
        assert project.health_score == 50


class TestSprintHealth:
    """Test SprintHealth embedded model."""

    def test_sprint_health_defaults(self):
        health = SprintHealth()
        assert health.completion_rate == 0.0
        assert health.velocity_trend == "stable"
        assert health.blocker_count == 0
        assert health.score == 50

    def test_sprint_health_score_range(self):
        health = SprintHealth(score=0)
        assert health.score == 0

        health = SprintHealth(score=100)
        assert health.score == 100

        with pytest.raises(ValidationError):
            SprintHealth(score=101)

    def test_completion_rate_range(self):
        health = SprintHealth(completion_rate=0.0)
        assert health.completion_rate == 0.0

        health = SprintHealth(completion_rate=100.0)
        assert health.completion_rate == 100.0

        with pytest.raises(ValidationError):
            SprintHealth(completion_rate=100.1)


class TestProjectValidation:
    """Test field validation constraints."""

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            Project(name="")

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            Project(name="A" * 301)

    def test_completion_percentage_range(self):
        project = Project(name="Test", completion_percentage=0.0)
        assert project.completion_percentage == 0.0

        project = Project(name="Test", completion_percentage=100.0)
        assert project.completion_percentage == 100.0

        with pytest.raises(ValidationError):
            Project(name="Test", completion_percentage=-0.1)

        with pytest.raises(ValidationError):
            Project(name="Test", completion_percentage=100.1)
