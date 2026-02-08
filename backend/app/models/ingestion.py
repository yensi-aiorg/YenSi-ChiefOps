"""
Ingestion models for the ChiefOps data pipeline.

Covers ingestion job tracking and the raw data representations for
Slack messages, Slack channels, Jira tasks, and Google Drive files
as they are parsed during the ingestion pipeline -- before entity
resolution transforms them into unified Person/Project/Task records.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid, utc_now

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IngestionStatus(str, Enum):
    """Lifecycle status of an ingestion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionFileType(str, Enum):
    """
    Type of data source file being ingested.

    - slack_admin_export: Full workspace export ZIP from Slack admin panel.
    - slack_api_extract: Data pulled via Slack API integration.
    - slack_manual_export: Manually exported Slack channel data.
    - jira_csv: CSV export from Jira (issues, boards, backlogs).
    - drive_document: Google Drive document (PDF, DOCX, spreadsheet, etc.).
    """

    SLACK_ADMIN_EXPORT = "slack_admin_export"
    SLACK_API_EXTRACT = "slack_api_extract"
    SLACK_MANUAL_EXPORT = "slack_manual_export"
    JIRA_CSV = "jira_csv"
    DRIVE_DOCUMENT = "drive_document"


class IngestionFileStatus(str, Enum):
    """Processing status of an individual file within an ingestion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class IngestionFileResult(BaseModel):
    """Tracks the processing outcome for a single file within an ingestion job."""

    filename: str = Field(
        ...,
        description="Name of the file being processed.",
    )
    file_type: IngestionFileType = Field(
        ...,
        description="Type of data source.",
    )
    status: IngestionFileStatus = Field(
        default=IngestionFileStatus.PENDING,
        description="Processing status of this file.",
    )
    records_processed: int = Field(
        default=0,
        ge=0,
        description="Number of records successfully processed from this file.",
    )
    records_skipped: int = Field(
        default=0,
        ge=0,
        description="Number of records skipped (duplicates, invalid, etc.).",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if processing failed.",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA-256 hash of file content for deduplication.",
    )


# ---------------------------------------------------------------------------
# Primary model: IngestionJob
# ---------------------------------------------------------------------------


class IngestionJob(MongoBaseModel):
    """
    Tracks a file ingestion pipeline from upload to completion.

    Progress is reported in stages:
    - slack_admin_export: extracting -> parsing_messages -> resolving_people -> analyzing
    - jira_csv: parsing_rows -> mapping_tasks -> resolving_people -> analyzing
    - drive_document: scanning_files -> ingesting_to_citex -> indexing -> analyzing

    MongoDB collection: ``ingestion_jobs``
    """

    job_id: str = Field(
        default_factory=generate_uuid,
        description="Unique ingestion job identifier (UUID v4).",
    )
    status: IngestionStatus = Field(
        default=IngestionStatus.PENDING,
        description="Overall job lifecycle status.",
    )
    files: list[IngestionFileResult] = Field(
        default_factory=list,
        description="Per-file processing results.",
    )

    started_at: datetime | None = Field(
        default=None,
        description="When processing began.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When processing finished (success or failure).",
    )
    error_count: int = Field(
        default=0,
        ge=0,
        description="Total number of errors encountered across all files.",
    )
    total_records: int = Field(
        default=0,
        ge=0,
        description="Total number of records processed across all files.",
    )


# ---------------------------------------------------------------------------
# Raw data models -- parsed from source files during ingestion
# ---------------------------------------------------------------------------


class SlackMessage(MongoBaseModel):
    """
    A single Slack message as parsed from an export or API extraction.
    Stored in the ``slack_messages`` collection during ingestion before
    entity resolution maps users to unified Person records.
    """

    message_id: str = Field(
        default_factory=generate_uuid,
        description="Unique message identifier (UUID v4).",
    )
    channel: str = Field(
        ...,
        description="Slack channel name or ID where the message was posted.",
    )
    user_id: str = Field(
        ...,
        description="Slack user ID of the message author.",
    )
    user_name: str = Field(
        default="",
        description="Slack display name of the message author.",
    )
    text: str = Field(
        default="",
        description="Message text content.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="Message timestamp.",
    )
    thread_ts: str | None = Field(
        default=None,
        description="Thread timestamp if this message is part of a thread.",
    )
    reactions: list[str] = Field(
        default_factory=list,
        description="Emoji reaction names on this message.",
    )
    reply_count: int = Field(
        default=0,
        ge=0,
        description="Number of replies (for thread parent messages).",
    )


class SlackChannel(MongoBaseModel):
    """
    Slack channel metadata as parsed from an export or API extraction.
    Used to map channels to projects during entity resolution.
    """

    channel_id: str = Field(
        ...,
        description="Slack channel ID.",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Channel name.",
    )
    purpose: str = Field(
        default="",
        description="Channel purpose / description.",
    )
    members: list[str] = Field(
        default_factory=list,
        description="Slack user IDs of channel members.",
    )
    message_count: int = Field(
        default=0,
        ge=0,
        description="Total number of messages in this channel.",
    )


class JiraTask(MongoBaseModel):
    """
    A Jira issue as parsed from a CSV export. Stored in the ``jira_tasks``
    collection during ingestion before being mapped to unified Task records.
    """

    task_key: str = Field(
        ...,
        description="Jira issue key (e.g. PROJ-123).",
    )
    project_key: str = Field(
        ...,
        description="Jira project key (e.g. PROJ).",
    )
    summary: str = Field(
        ...,
        min_length=1,
        description="Issue summary / title.",
    )
    description: str = Field(
        default="",
        description="Full issue description.",
    )
    status: str = Field(
        default="To Do",
        description="Current issue status (e.g. To Do, In Progress, Done).",
    )
    assignee: str | None = Field(
        default=None,
        description="Assignee display name or account ID.",
    )
    reporter: str | None = Field(
        default=None,
        description="Reporter display name or account ID.",
    )
    priority: str | None = Field(
        default=None,
        description="Priority level (e.g. Critical, High, Medium, Low).",
    )
    created_date: datetime = Field(
        default_factory=utc_now,
        description="Issue creation date in Jira.",
    )
    updated_date: datetime = Field(
        default_factory=utc_now,
        description="Last update date in Jira.",
    )
    story_points: float | None = Field(
        default=None,
        ge=0,
        description="Story point estimate.",
    )
    sprint: str | None = Field(
        default=None,
        description="Sprint name this issue belongs to.",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Issue labels.",
    )
    comments: list[str] = Field(
        default_factory=list,
        description="Comment texts on the issue.",
    )


class DriveFile(MongoBaseModel):
    """
    Google Drive file metadata parsed during ingestion. File content
    is ingested into Citex for RAG-based retrieval; this model tracks
    metadata and ingestion status.
    """

    file_id: str = Field(
        ...,
        description="Google Drive file ID or generated unique identifier.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        description="Original file name.",
    )
    file_type: str = Field(
        default="",
        description="MIME type or file extension.",
    )
    file_hash: str | None = Field(
        default=None,
        description="SHA-256 hash of file content for deduplication.",
    )
    content_preview: str = Field(
        default="",
        max_length=2000,
        description="First portion of extracted text content for quick preview.",
    )
    indexed_in_citex: bool = Field(
        default=False,
        description="Whether this file has been successfully ingested into Citex.",
    )
    citex_document_id: str | None = Field(
        default=None,
        description="Citex document reference ID after successful ingestion.",
    )
