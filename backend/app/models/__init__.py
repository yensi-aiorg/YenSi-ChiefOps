"""
ChiefOps data models package.

All Pydantic v2 models for MongoDB document storage. Import from this
module for convenient access to every model and enum in the system.
"""

# Base model and helpers
# Alert models
from app.models.alert import (
    Alert,
    AlertOperator,
    AlertSeverity,
    AlertTriggered,
    AlertType,
)
from app.models.base import (
    MongoBaseModel,
    generate_uuid,
    utc_now,
)

# Conversation and memory models
from app.models.conversation import (
    CompactedSummary,
    ConversationTurn,
    FactCategory,
    HardFact,
    MemoryStream,
    SourceType,
    SourceUsed,
    StreamType,
    TurnRole,
)

# Dashboard and widget models
from app.models.dashboard import (
    Dashboard,
    DashboardType,
    DataQuery,
    QueryType,
    WidgetPosition,
    WidgetSpec,
    WidgetType,
)

# Ingestion models
from app.models.ingestion import (
    DriveFile,
    IngestionFileResult,
    IngestionFileStatus,
    IngestionFileType,
    IngestionJob,
    IngestionStatus,
    JiraTask,
    SlackChannel,
    SlackMessage,
)

# Person models
from app.models.person import (
    ActivityLevel,
    EngagementMetrics,
    Person,
    RoleSource,
    SourceReference,
    SourceSystem,
)

# Project models
from app.models.project import (
    BackwardPlanItem,
    GapAnalysis,
    Milestone,
    MilestoneStatus,
    Project,
    ProjectMember,
    ProjectStatus,
    ReadinessItem,
    RiskItem,
    SprintHealth,
    TaskSummary,
    TechnicalFeasibility,
)

# Report models
from app.models.report import (
    ReportHistory,
    ReportSection,
    ReportSpec,
    ReportStatus,
    ReportType,
    SectionType,
)

# Settings model
from app.models.settings import (
    AIProviderConfig,
    BrandingConfig,
    CitexConfig,
    DriveIntegration,
    JiraIntegration,
    MemoryConfig,
    NotificationConfig,
    Settings,
    SlackIntegration,
)

__all__ = [
    # settings
    "AIProviderConfig",
    # person
    "ActivityLevel",
    # alert
    "Alert",
    "AlertOperator",
    "AlertSeverity",
    "AlertTriggered",
    "AlertType",
    # project
    "BackwardPlanItem",
    "BrandingConfig",
    "CitexConfig",
    # conversation
    "CompactedSummary",
    "ConversationTurn",
    # dashboard
    "Dashboard",
    "DashboardType",
    "DataQuery",
    # ingestion
    "DriveFile",
    "DriveIntegration",
    "EngagementMetrics",
    "FactCategory",
    "GapAnalysis",
    "HardFact",
    "IngestionFileResult",
    "IngestionFileStatus",
    "IngestionFileType",
    "IngestionJob",
    "IngestionStatus",
    "JiraIntegration",
    "JiraTask",
    "MemoryConfig",
    "MemoryStream",
    "Milestone",
    "MilestoneStatus",
    # base
    "MongoBaseModel",
    "NotificationConfig",
    "Person",
    "Project",
    "ProjectMember",
    "ProjectStatus",
    "QueryType",
    "ReadinessItem",
    # report
    "ReportHistory",
    "ReportSection",
    "ReportSpec",
    "ReportStatus",
    "ReportType",
    "RiskItem",
    "RoleSource",
    "SectionType",
    "Settings",
    "SlackChannel",
    "SlackIntegration",
    "SlackMessage",
    "SourceReference",
    "SourceSystem",
    "SourceType",
    "SourceUsed",
    "SprintHealth",
    "StreamType",
    "TaskSummary",
    "TechnicalFeasibility",
    "TurnRole",
    "WidgetPosition",
    "WidgetSpec",
    "WidgetType",
    "generate_uuid",
    "utc_now",
]
