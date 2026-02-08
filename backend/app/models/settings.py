"""
Settings model for application configuration stored in MongoDB.

Persists user preferences, integration credentials, branding, and
system configuration so they survive restarts and are editable through
the ChiefOps conversation interface.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class SlackIntegration(BaseModel):
    """Configuration for Slack workspace integration."""

    enabled: bool = Field(
        default=False,
        description="Whether Slack integration is active.",
    )
    workspace_name: str = Field(
        default="",
        description="Slack workspace display name.",
    )
    bot_token: Optional[str] = Field(
        default=None,
        description="Slack bot OAuth token (encrypted at rest).",
    )
    default_channel: Optional[str] = Field(
        default=None,
        description="Default channel for notifications.",
    )


class JiraIntegration(BaseModel):
    """Configuration for Jira integration."""

    enabled: bool = Field(
        default=False,
        description="Whether Jira integration is active.",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Jira instance base URL.",
    )
    api_token: Optional[str] = Field(
        default=None,
        description="Jira API token (encrypted at rest).",
    )
    username: Optional[str] = Field(
        default=None,
        description="Jira username for API authentication.",
    )


class DriveIntegration(BaseModel):
    """Configuration for Google Drive integration."""

    enabled: bool = Field(
        default=False,
        description="Whether Google Drive integration is active.",
    )
    service_account_key: Optional[str] = Field(
        default=None,
        description="Path to Google service account JSON key file.",
    )
    root_folder_id: Optional[str] = Field(
        default=None,
        description="Google Drive root folder ID to scan.",
    )


class CitexConfig(BaseModel):
    """Configuration for the Citex RAG system."""

    base_url: str = Field(
        default="http://citex:8000",
        description="Citex service base URL.",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Citex API key (if required).",
    )
    collection_name: str = Field(
        default="chiefops",
        description="Default Citex collection for document ingestion.",
    )


class AIProviderConfig(BaseModel):
    """Configuration for AI model access."""

    provider: str = Field(
        default="openrouter",
        description="Active AI provider ('openrouter', 'cli_claude', 'cli_codex', 'cli_gemini').",
    )
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key (encrypted at rest).",
    )
    default_model: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Default model identifier for AI calls.",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Default temperature for AI responses.",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=200000,
        description="Default max tokens for AI responses.",
    )


class BrandingConfig(BaseModel):
    """Visual branding settings for reports and dashboards."""

    company_name: str = Field(
        default="",
        description="Company name for report headers.",
    )
    logo_url: Optional[str] = Field(
        default=None,
        description="URL to company logo image.",
    )
    color_scheme: dict = Field(
        default_factory=lambda: {
            "primary": "#1a1a2e",
            "secondary": "#16213e",
            "accent": "#0f3460",
            "highlight": "#e94560",
        },
        description="Named hex color values for theming.",
    )


class MemoryConfig(BaseModel):
    """Configuration for the memory compaction system."""

    max_recent_turns: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Maximum number of recent turns to keep in working memory.",
    )
    compaction_threshold: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Number of turns before triggering summary compaction.",
    )
    context_token_budget: int = Field(
        default=8000,
        ge=1000,
        le=100000,
        description="Token budget for assembled context in each AI call.",
    )
    fact_extraction_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for automatic fact extraction.",
    )


class NotificationConfig(BaseModel):
    """Configuration for alert notifications."""

    email_enabled: bool = Field(
        default=False,
        description="Whether email notifications are active.",
    )
    email_recipients: list[str] = Field(
        default_factory=list,
        description="Email addresses for alert notifications.",
    )
    slack_notifications_enabled: bool = Field(
        default=False,
        description="Whether to send alert notifications to Slack.",
    )
    slack_notification_channel: Optional[str] = Field(
        default=None,
        description="Slack channel for alert notifications.",
    )


# ---------------------------------------------------------------------------
# Primary model: Settings
# ---------------------------------------------------------------------------


class Settings(MongoBaseModel):
    """
    Application-level configuration stored in MongoDB. A single document
    in the ``settings`` collection holds all persistent configuration.
    Settings are editable through the COO conversation interface or
    through a future admin panel.

    MongoDB collection: ``settings`` (singleton document)
    """

    settings_id: str = Field(
        default_factory=generate_uuid,
        description="Unique settings document identifier (UUID v4).",
    )

    # Integration configurations
    slack: SlackIntegration = Field(
        default_factory=SlackIntegration,
        description="Slack workspace integration settings.",
    )
    jira: JiraIntegration = Field(
        default_factory=JiraIntegration,
        description="Jira integration settings.",
    )
    drive: DriveIntegration = Field(
        default_factory=DriveIntegration,
        description="Google Drive integration settings.",
    )
    citex: CitexConfig = Field(
        default_factory=CitexConfig,
        description="Citex RAG system configuration.",
    )
    ai_provider: AIProviderConfig = Field(
        default_factory=AIProviderConfig,
        description="AI model provider configuration.",
    )

    # Display and branding
    branding: BrandingConfig = Field(
        default_factory=BrandingConfig,
        description="Visual branding for reports and dashboards.",
    )

    # Memory system
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory compaction system configuration.",
    )

    # Notifications
    notifications: NotificationConfig = Field(
        default_factory=NotificationConfig,
        description="Alert notification configuration.",
    )

    # General
    timezone: str = Field(
        default="UTC",
        description="Default timezone for date formatting in reports and UI.",
    )
    data_retention_days: int = Field(
        default=365,
        ge=30,
        le=3650,
        description="Number of days to retain raw ingested data before archival.",
    )
