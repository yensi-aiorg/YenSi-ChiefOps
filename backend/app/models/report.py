"""
Report models for the ChiefOps report generation system.

Reports are created through conversation and can be iteratively refined.
Each report has a structured specification defining its sections, and
the system generates PDF exports on demand. Version tracking provides
a full audit trail of conversational edits.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid, utc_now

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReportType(str, Enum):
    """
    Category of report. Each type triggers a different report template
    and data assembly strategy.
    """

    BOARD_OPS_SUMMARY = "board_ops_summary"
    PROJECT_STATUS = "project_status"
    TEAM_PERFORMANCE = "team_performance"
    RISK_ASSESSMENT = "risk_assessment"
    SPRINT_REPORT = "sprint_report"
    RESOURCE_UTILIZATION = "resource_utilization"
    TECHNICAL_DUE_DILIGENCE = "technical_due_diligence"
    CUSTOM = "custom"


class ReportStatus(str, Enum):
    """Lifecycle status of a report."""

    GENERATING = "generating"
    READY = "ready"
    EXPORTED = "exported"


class SectionType(str, Enum):
    """Type of content section within a report."""

    NARRATIVE = "narrative"
    METRICS_GRID = "metrics_grid"
    CHART = "chart"
    TABLE = "table"
    CARD_LIST = "card_list"
    CHECKLIST = "checklist"


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class ReportSection(BaseModel):
    """
    A single section within a report. Sections are ordered and typed;
    the rendering engine uses section_type to select the appropriate
    template partial for PDF generation.
    """

    section_id: str = Field(
        default_factory=generate_uuid,
        description="Unique section identifier (UUID v4).",
    )
    section_type: SectionType = Field(
        ...,
        description="Type of content in this section.",
    )
    title: str = Field(
        default="",
        max_length=300,
        description="Section heading.",
    )
    content: dict = Field(
        default_factory=dict,
        description="Section payload (structure varies by section_type).",
    )
    order: int = Field(
        default=0,
        ge=0,
        description="Display order within the report (lower = earlier).",
    )


# ---------------------------------------------------------------------------
# Primary model: ReportSpec
# ---------------------------------------------------------------------------


class ReportSpec(MongoBaseModel):
    """
    A generated report with full edit history. Reports are created
    through conversation and iteratively refined. The sections list
    defines the structured content; the metadata dict carries additional
    context used during rendering (branding, color scheme, etc.).

    MongoDB collection: ``reports``
    """

    report_id: str = Field(
        default_factory=generate_uuid,
        description="Unique report identifier (UUID v4).",
    )
    report_type: ReportType = Field(
        ...,
        description="Report category.",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Report title.",
    )
    time_scope: dict = Field(
        default_factory=dict,
        description="Time range for the report (e.g. {start: '...', end: '...', label: 'Q1 2025'}).",
    )
    audience: str = Field(
        default="coo",
        description="Intended audience for the report (e.g. 'board', 'coo', 'engineering').",
    )
    projects: list[str] = Field(
        default_factory=list,
        description="List of project_id values included in this report.",
    )
    sections: list[ReportSection] = Field(
        default_factory=list,
        description="Ordered list of report sections.",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional rendering metadata (branding, color scheme, layout hints).",
    )
    status: ReportStatus = Field(
        default=ReportStatus.GENERATING,
        description="Report lifecycle status.",
    )


# ---------------------------------------------------------------------------
# Primary model: ReportHistory
# ---------------------------------------------------------------------------


class ReportHistory(MongoBaseModel):
    """
    Immutable record of a generated report snapshot. Each time a report
    is finalized or exported, a history entry is created capturing the
    full report specification at that point in time, along with the
    export artifact path.

    MongoDB collection: ``report_history``
    """

    history_id: str = Field(
        default_factory=generate_uuid,
        description="Unique history entry identifier (UUID v4).",
    )
    report_id: str = Field(
        ...,
        description="References the report_id this snapshot belongs to.",
    )
    report_spec: dict = Field(
        default_factory=dict,
        description="Full report specification snapshot at time of generation.",
    )
    pdf_path: str | None = Field(
        default=None,
        description="File system path to the generated PDF (None if not yet exported).",
    )
    generated_at: datetime = Field(
        default_factory=utc_now,
        description="When this snapshot was generated.",
    )
    generated_by: str = Field(
        default="system",
        description="Identifier of who/what triggered the generation.",
    )
