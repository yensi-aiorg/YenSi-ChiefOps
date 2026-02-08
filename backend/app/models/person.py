"""
Person model and related types for the ChiefOps people collection.

Unified directory of all identified people across data sources. When ChiefOps
ingests Slack messages, Jira exports, or Google Drive files, it resolves
identities into a single person record. The COO can correct AI-assigned roles,
and those corrections are preserved as coo_corrected.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourceSystem(str, Enum):
    """Data source systems integrated with ChiefOps."""

    SLACK = "slack"
    JIRA = "jira"
    GDRIVE = "gdrive"


class RoleSource(str, Enum):
    """How a person's role was determined."""

    AI_IDENTIFIED = "ai_identified"
    COO_CORRECTED = "coo_corrected"


class ActivityLevel(str, Enum):
    """
    Computed activity level based on message frequency, task activity,
    and recency of interactions across all integrated sources.
    """

    VERY_ACTIVE = "very_active"
    ACTIVE = "active"
    MODERATE = "moderate"
    QUIET = "quiet"
    INACTIVE = "inactive"


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class SourceReference(BaseModel):
    """Links a person record back to their identity in a source system."""

    source: SourceSystem = Field(
        ...,
        description="The source system this identity comes from.",
    )
    source_id: str = Field(
        ...,
        min_length=1,
        description="The identifier in the source system (Slack user ID, Jira username, etc.).",
    )


class EngagementMetrics(BaseModel):
    """Slack-derived engagement statistics for a person."""

    messages_sent: int = Field(
        default=0,
        ge=0,
        description="Total Slack messages sent by this person.",
    )
    threads_replied: int = Field(
        default=0,
        ge=0,
        description="Number of threads this person has replied to.",
    )
    reactions_given: int = Field(
        default=0,
        ge=0,
        description="Total emoji reactions this person has given.",
    )


# ---------------------------------------------------------------------------
# Primary model
# ---------------------------------------------------------------------------


class Person(MongoBaseModel):
    """
    Unified person record. One document per real human, regardless of how many
    source systems they appear in. Identity resolution merges Slack users,
    Jira assignees, and Drive file owners into a single record.

    MongoDB collection: ``people``
    """

    person_id: str = Field(
        default_factory=generate_uuid,
        description="Unique person identifier (UUID v4).",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Display name (resolved from best available source).",
    )
    email: Optional[str] = Field(
        default=None,
        description="Email address if discovered from any source.",
    )

    source_ids: list[SourceReference] = Field(
        default_factory=list,
        description="Cross-references to identities in each source system.",
    )

    role: str = Field(
        ...,
        description="Job role -- AI-identified from message patterns or COO-corrected.",
    )
    role_source: RoleSource = Field(
        default=RoleSource.AI_IDENTIFIED,
        description="Whether the role was set by AI analysis or corrected by the COO.",
    )
    department: Optional[str] = Field(
        default=None,
        description="Department name (e.g. Engineering, Sales).",
    )

    activity_level: ActivityLevel = Field(
        default=ActivityLevel.MODERATE,
        description="Computed activity level based on message frequency and task activity.",
    )
    last_active_date: datetime = Field(
        default_factory=utc_now,
        description="Most recent activity timestamp across all sources.",
    )

    avatar_url: Optional[str] = Field(
        default=None,
        description="Profile image URL from Slack.",
    )
    slack_user_id: Optional[str] = Field(
        default=None,
        description="Slack member ID (e.g. U01ABC123).",
    )
    jira_username: Optional[str] = Field(
        default=None,
        description="Jira display name or account ID.",
    )

    tasks_assigned: int = Field(
        default=0,
        ge=0,
        description="Count of tasks currently assigned to this person.",
    )
    tasks_completed: int = Field(
        default=0,
        ge=0,
        description="Count of tasks this person has completed.",
    )

    engagement_metrics: EngagementMetrics = Field(
        default_factory=EngagementMetrics,
        description="Slack engagement statistics.",
    )

    projects: list[str] = Field(
        default_factory=list,
        description="List of project_id values this person is involved in.",
    )
