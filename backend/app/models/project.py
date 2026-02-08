"""
Project model and related types for the ChiefOps projects collection.

Projects are identified from Jira project keys and Slack channel patterns.
A single project may span multiple Jira projects and Slack channels. The AI
detects project boundaries, and the COO can confirm or adjust them.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProjectStatus(str, Enum):
    """Overall project health status."""

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    COMPLETED = "completed"


class MilestoneStatus(str, Enum):
    """Lifecycle status of a project milestone."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class Milestone(BaseModel):
    """A project milestone with a target date and current status."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Milestone name.",
    )
    target_date: datetime = Field(
        ...,
        description="Target completion date for this milestone.",
    )
    status: MilestoneStatus = Field(
        default=MilestoneStatus.PENDING,
        description="Current milestone status.",
    )
    description: str = Field(
        default="",
        description="Optional description of the milestone scope.",
    )


class ProjectMember(BaseModel):
    """A person's involvement in a specific project."""

    person_id: str = Field(
        ...,
        description="References the person_id in the people collection.",
    )
    name: str = Field(
        default="",
        description="Denormalized display name for quick rendering.",
    )
    role: str = Field(
        default="contributor",
        description="Role within this project (e.g. tech_lead, developer, qa, pm, stakeholder).",
    )
    activity_level: str = Field(
        default="moderate",
        description="Person's activity level within this specific project.",
    )


class TaskSummary(BaseModel):
    """Aggregated task counts for a project, broken down by status."""

    total: int = Field(default=0, ge=0, description="Total task count.")
    completed: int = Field(default=0, ge=0, description="Tasks marked as done.")
    in_progress: int = Field(default=0, ge=0, description="Tasks currently in progress.")
    blocked: int = Field(default=0, ge=0, description="Tasks that are blocked.")
    to_do: int = Field(default=0, ge=0, description="Tasks not yet started.")


class SprintHealth(BaseModel):
    """Sprint-level health metrics for a project."""

    completion_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of sprint items completed.",
    )
    velocity_trend: str = Field(
        default="stable",
        description="Velocity trend direction (increasing, stable, decreasing).",
    )
    blocker_count: int = Field(
        default=0,
        ge=0,
        description="Number of active blockers in the current sprint.",
    )
    score: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Composite sprint health score (0-100).",
    )


class BackwardPlanItem(BaseModel):
    """A single item in a backward plan derived from gap analysis."""

    task: str = Field(
        ...,
        description="Description of the required task.",
    )
    estimated_days: int = Field(
        default=1,
        ge=1,
        description="Estimated days to complete this task.",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Tasks this item depends on.",
    )
    priority: str = Field(
        default="medium",
        description="Priority level (critical, high, medium, low).",
    )


class GapAnalysis(BaseModel):
    """AI-detected gaps in project planning and execution."""

    missing_tasks: list[str] = Field(
        default_factory=list,
        description="Tasks that should exist but have not been created.",
    )
    missing_prerequisites: list[str] = Field(
        default_factory=list,
        description="Prerequisites that are unaccounted for.",
    )
    backward_plan: list[BackwardPlanItem] = Field(
        default_factory=list,
        description="Backward plan items generated from deadline to present.",
    )


class ReadinessItem(BaseModel):
    """A single technical readiness evaluation item."""

    area: str = Field(
        ...,
        description="Technical area being evaluated (e.g. infrastructure, API design).",
    )
    status: str = Field(
        default="unknown",
        description="Readiness status (ready, partial, not_ready, unknown).",
    )
    details: str = Field(
        default="",
        description="Explanation of readiness assessment.",
    )


class RiskItem(BaseModel):
    """A single technical risk item."""

    risk: str = Field(
        ...,
        description="Description of the technical risk.",
    )
    severity: str = Field(
        default="medium",
        description="Risk severity (critical, high, medium, low).",
    )
    mitigation: str = Field(
        default="",
        description="Suggested mitigation strategy.",
    )


class TechnicalFeasibility(BaseModel):
    """AI-assessed technical feasibility of a project."""

    readiness_items: list[ReadinessItem] = Field(
        default_factory=list,
        description="Technical readiness evaluations by area.",
    )
    risk_items: list[RiskItem] = Field(
        default_factory=list,
        description="Identified technical risks with severity and mitigation.",
    )
    architect_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved questions for the architecture team.",
    )


# ---------------------------------------------------------------------------
# Primary model
# ---------------------------------------------------------------------------


class Project(MongoBaseModel):
    """
    A project identified from Jira project keys and Slack channel patterns.
    One project may span multiple Jira projects and multiple Slack channels.
    AI detects project boundaries; the COO confirms or adjusts.

    MongoDB collection: ``projects``
    """

    project_id: str = Field(
        default_factory=generate_uuid,
        description="Unique project identifier (UUID v4).",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Human-readable project name.",
    )
    description: str = Field(
        default="",
        description="AI-generated or COO-provided project description.",
    )

    status: ProjectStatus = Field(
        default=ProjectStatus.ON_TRACK,
        description="Overall project status.",
    )
    completion_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Task-based completion percentage (0.0 to 100.0).",
    )
    deadline: Optional[datetime] = Field(
        default=None,
        description="Target completion date.",
    )

    milestones: list[Milestone] = Field(
        default_factory=list,
        description="Ordered list of project milestones.",
    )

    people_involved: list[ProjectMember] = Field(
        default_factory=list,
        description="People and their roles within this project.",
    )

    task_summary: TaskSummary = Field(
        default_factory=TaskSummary,
        description="Aggregated task counts by status.",
    )

    health_score: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Composite health score (0 = critical, 100 = excellent).",
    )

    key_risks: list[str] = Field(
        default_factory=list,
        description="AI-identified risk descriptions.",
    )
    missing_tasks: list[str] = Field(
        default_factory=list,
        description="AI-detected tasks that should exist but do not.",
    )
    technical_concerns: list[str] = Field(
        default_factory=list,
        description="Technical issues flagged by AI analysis.",
    )

    slack_channels: list[str] = Field(
        default_factory=list,
        description="Slack channel names associated with this project.",
    )
    jira_project_keys: list[str] = Field(
        default_factory=list,
        description="Jira project keys (e.g. ['PROJ', 'MOBILE']).",
    )

    sprint_health: Optional[SprintHealth] = Field(
        default=None,
        description="Current sprint health metrics.",
    )
    gap_analysis: Optional[GapAnalysis] = Field(
        default=None,
        description="AI-detected gaps in planning and execution.",
    )
    technical_feasibility: Optional[TechnicalFeasibility] = Field(
        default=None,
        description="AI-assessed technical feasibility.",
    )

    last_analyzed_at: datetime = Field(
        default_factory=utc_now,
        description="When AI last ran analysis on this project.",
    )
