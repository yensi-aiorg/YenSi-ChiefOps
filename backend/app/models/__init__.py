"""
ChiefOps data models package.

All Pydantic v2 models for MongoDB document storage. Import from this
module for convenient access to every model and enum in the system.
"""

# Base model and helpers
from app.models.base import (
    MongoBaseModel,
    generate_uuid,
    utc_now,
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

# Report models
from app.models.report import (
    ReportHistory,
    ReportSection,
    ReportSpec,
    ReportStatus,
    ReportType,
    SectionType,
)

# Alert models
from app.models.alert import (
    Alert,
    AlertOperator,
    AlertSeverity,
    AlertTriggered,
    AlertType,
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
    # base
    "MongoBaseModel",
    "generate_uuid",
    "utc_now",
    # person
    "ActivityLevel",
    "EngagementMetrics",
    "Person",
    "RoleSource",
    "SourceReference",
    "SourceSystem",
    # project
    "BackwardPlanItem",
    "GapAnalysis",
    "Milestone",
    "MilestoneStatus",
    "Project",
    "ProjectMember",
    "ProjectStatus",
    "ReadinessItem",
    "RiskItem",
    "SprintHealth",
    "TaskSummary",
    "TechnicalFeasibility",
    # ingestion
    "DriveFile",
    "IngestionFileResult",
    "IngestionFileStatus",
    "IngestionFileType",
    "IngestionJob",
    "IngestionStatus",
    "JiraTask",
    "SlackChannel",
    "SlackMessage",
    # conversation
    "CompactedSummary",
    "ConversationTurn",
    "FactCategory",
    "HardFact",
    "MemoryStream",
    "SourceType",
    "SourceUsed",
    "StreamType",
    "TurnRole",
    # dashboard
    "Dashboard",
    "DashboardType",
    "DataQuery",
    "QueryType",
    "WidgetPosition",
    "WidgetSpec",
    "WidgetType",
    # report
    "ReportHistory",
    "ReportSection",
    "ReportSpec",
    "ReportStatus",
    "ReportType",
    "SectionType",
    # alert
    "Alert",
    "AlertOperator",
    "AlertSeverity",
    "AlertTriggered",
    "AlertType",
    # settings
    "AIProviderConfig",
    "BrandingConfig",
    "CitexConfig",
    "DriveIntegration",
    "JiraIntegration",
    "MemoryConfig",
    "NotificationConfig",
    "Settings",
    "SlackIntegration",
]
