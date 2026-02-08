# Data Models: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | **Data Models** | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## Overview

ChiefOps Step Zero uses **MongoDB** as its primary datastore, accessed via the **Motor** async driver for Python. All models are validated with **Pydantic v2**. This document defines every collection, its fields, types, constraints, and indexes. It is the authoritative reference for the engineering team.

### Conventions

- All `_id` fields use MongoDB's default `ObjectId`. Application-level IDs (e.g., `person_id`, `project_id`) are UUID v4 strings for deterministic referencing across collections.
- Timestamps are stored as UTC `datetime` objects.
- Embedded sub-documents are defined as separate Pydantic models and composed into parent models.
- Optional fields default to `None` unless otherwise specified.
- Enum fields use Python `str` enums for MongoDB serialization compatibility.

### Shared Base Model

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


def generate_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.utcnow()


class MongoBaseModel(BaseModel):
    """Base model for all MongoDB documents."""
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

---

## 1. `people` Collection

Unified directory of all identified people across data sources. When ChiefOps ingests Slack messages, Jira exports, or Google Drive files, it resolves identities into a single person record. The COO can correct AI-assigned roles, and those corrections are preserved as `coo_corrected`.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `person_id` | `str` (UUID v4) | Yes | Unique identifier for this person |
| `name` | `str` | Yes | Display name (resolved from best available source) |
| `email` | `str \| None` | No | Email address if discovered |
| `source_ids` | `list[SourceReference]` | Yes | Cross-reference to original identities in each source system |
| `role` | `str` | Yes | Job role — AI-identified from message patterns or COO-corrected |
| `role_source` | `"ai_identified" \| "coo_corrected"` | Yes | Whether the role was set by AI analysis or corrected by the COO |
| `department` | `str \| None` | No | Department name (e.g., "Engineering", "Sales") |
| `activity_level` | `"very_active" \| "active" \| "moderate" \| "quiet" \| "inactive"` | Yes | Computed from message frequency, task activity, and recency |
| `last_active_date` | `datetime` | Yes | Most recent activity timestamp across all sources |
| `avatar_url` | `str \| None` | No | Profile image URL (from Slack profile) |
| `slack_user_id` | `str \| None` | No | Slack member ID (e.g., `U01ABC123`) |
| `jira_username` | `str \| None` | No | Jira display name or account ID |
| `tasks_assigned` | `int` | Yes | Count of tasks currently assigned to this person |
| `tasks_completed` | `int` | Yes | Count of tasks this person has completed |
| `engagement_metrics` | `EngagementMetrics` | Yes | Slack engagement statistics |
| `projects` | `list[str]` | Yes | List of `project_id` values this person is involved in |
| `created_at` | `datetime` | Yes | Record creation timestamp |
| `updated_at` | `datetime` | Yes | Last modification timestamp |

### Embedded Sub-Documents

```python
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class SourceSystem(str, Enum):
    SLACK = "slack"
    JIRA = "jira"
    GDRIVE = "gdrive"


class RoleSource(str, Enum):
    AI_IDENTIFIED = "ai_identified"
    COO_CORRECTED = "coo_corrected"


class ActivityLevel(str, Enum):
    VERY_ACTIVE = "very_active"
    ACTIVE = "active"
    MODERATE = "moderate"
    QUIET = "quiet"
    INACTIVE = "inactive"


class SourceReference(BaseModel):
    """Links a person record back to their identity in a source system."""
    source: SourceSystem
    source_id: str  # The ID in the source system (Slack user ID, Jira username, etc.)


class EngagementMetrics(BaseModel):
    """Slack-derived engagement statistics."""
    messages_sent: int = 0
    threads_replied: int = 0
    reactions_given: int = 0
```

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from pydantic import Field


class Person(MongoBaseModel):
    """
    Unified person record. One document per real human, regardless of how many
    source systems they appear in. Identity resolution merges Slack users,
    Jira assignees, and Drive file owners into a single record.
    """
    person_id: str = Field(default_factory=generate_uuid, description="Unique person identifier (UUID v4)")
    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    email: Optional[str] = Field(default=None, description="Email address if discovered")

    source_ids: list[SourceReference] = Field(
        default_factory=list,
        description="Cross-references to identities in each source system"
    )

    role: str = Field(..., description="Job role — AI-identified or COO-corrected")
    role_source: RoleSource = Field(
        default=RoleSource.AI_IDENTIFIED,
        description="Whether role was set by AI or corrected by the COO"
    )
    department: Optional[str] = Field(default=None, description="Department name")

    activity_level: ActivityLevel = Field(
        default=ActivityLevel.MODERATE,
        description="Computed activity level based on message frequency and task activity"
    )
    last_active_date: datetime = Field(..., description="Most recent activity across all sources")

    avatar_url: Optional[str] = Field(default=None, description="Profile image URL from Slack")
    slack_user_id: Optional[str] = Field(default=None, description="Slack member ID (e.g., U01ABC123)")
    jira_username: Optional[str] = Field(default=None, description="Jira display name or account ID")

    tasks_assigned: int = Field(default=0, ge=0, description="Count of currently assigned tasks")
    tasks_completed: int = Field(default=0, ge=0, description="Count of completed tasks")

    engagement_metrics: EngagementMetrics = Field(
        default_factory=EngagementMetrics,
        description="Slack engagement statistics"
    )

    projects: list[str] = Field(default_factory=list, description="List of project_id values")
```

---

## 2. `projects` Collection

Projects are identified from Jira project keys and Slack channel patterns. A single project may span multiple Jira projects and Slack channels. The AI detects project boundaries, and the COO can confirm or adjust them.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | `str` (UUID v4) | Yes | Unique project identifier |
| `name` | `str` | Yes | Human-readable project name |
| `description` | `str` | Yes | AI-generated or COO-provided project description |
| `status` | `"on_track" \| "at_risk" \| "behind" \| "completed"` | Yes | Overall project status |
| `completion_percentage` | `float` | Yes | 0.0 to 100.0 — calculated from task completion ratios |
| `deadline` | `datetime \| None` | No | Target completion date |
| `milestones` | `list[Milestone]` | Yes | Ordered list of project milestones |
| `people_involved` | `list[ProjectMember]` | Yes | People and their roles within this project |
| `task_summary` | `TaskSummary` | Yes | Aggregated task counts by status |
| `health_score` | `int` | Yes | 0-100 composite health score |
| `key_risks` | `list[str]` | Yes | AI-identified risk descriptions |
| `missing_tasks` | `list[str]` | Yes | AI-detected tasks that should exist but do not |
| `technical_concerns` | `list[str]` | Yes | Technical issues flagged by AI analysis |
| `slack_channels` | `list[str]` | Yes | Slack channel names associated with this project |
| `jira_project_keys` | `list[str]` | Yes | Jira project keys (e.g., `["PROJ", "MOBILE"]`) |
| `created_at` | `datetime` | Yes | Record creation timestamp |
| `updated_at` | `datetime` | Yes | Last modification timestamp |
| `last_analyzed_at` | `datetime` | Yes | When AI last ran analysis on this project |

### Embedded Sub-Documents

```python
from enum import Enum


class ProjectStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    COMPLETED = "completed"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"


class Milestone(BaseModel):
    """A project milestone with a target date and current status."""
    name: str
    date: datetime
    status: MilestoneStatus = MilestoneStatus.PENDING


class ProjectMember(BaseModel):
    """A person's involvement in a specific project."""
    person_id: str
    role_in_project: str  # e.g., "tech_lead", "developer", "qa", "pm", "stakeholder"


class TaskSummary(BaseModel):
    """Aggregated task counts for a project."""
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    blocked: int = 0
    unassigned: int = 0
```

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from pydantic import Field


class Project(MongoBaseModel):
    """
    A project identified from Jira project keys and Slack channel patterns.
    One project may span multiple Jira projects and multiple Slack channels.
    AI detects project boundaries; the COO confirms or adjusts.
    """
    project_id: str = Field(default_factory=generate_uuid, description="Unique project identifier (UUID v4)")
    name: str = Field(..., min_length=1, max_length=300, description="Project name")
    description: str = Field(default="", description="AI-generated or COO-provided description")

    status: ProjectStatus = Field(
        default=ProjectStatus.ON_TRACK,
        description="Overall project status"
    )
    completion_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Task-based completion percentage"
    )
    deadline: Optional[datetime] = Field(default=None, description="Target completion date")

    milestones: list[Milestone] = Field(default_factory=list, description="Ordered project milestones")

    people_involved: list[ProjectMember] = Field(
        default_factory=list,
        description="People and their roles within this project"
    )

    task_summary: TaskSummary = Field(
        default_factory=TaskSummary,
        description="Aggregated task counts by status"
    )

    health_score: int = Field(
        default=50, ge=0, le=100,
        description="Composite health score (0 = critical, 100 = excellent)"
    )

    key_risks: list[str] = Field(default_factory=list, description="AI-identified risk descriptions")
    missing_tasks: list[str] = Field(default_factory=list, description="AI-detected missing tasks")
    technical_concerns: list[str] = Field(default_factory=list, description="Technical issues flagged by AI")

    slack_channels: list[str] = Field(default_factory=list, description="Associated Slack channels")
    jira_project_keys: list[str] = Field(default_factory=list, description="Associated Jira project keys")

    last_analyzed_at: datetime = Field(
        default_factory=utc_now,
        description="When AI last analyzed this project"
    )
```

---

## 3. `tasks` Collection

Work items sourced from Jira CSV exports and AI-identified assignments from Slack conversations. Slack-identified tasks are informal assignments detected by the AI (e.g., "Hey @bob can you handle the API migration?"). These carry `source_evidence` linking back to the original messages.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | `str` (UUID v4) | Yes | Unique task identifier |
| `source` | `"jira" \| "slack_identified"` | Yes | Where this task originated |
| `jira_key` | `str \| None` | No | Jira issue key (e.g., `PROJ-123`) — only for Jira-sourced tasks |
| `project_id` | `str` | Yes | The project this task belongs to |
| `summary` | `str` | Yes | Task title / summary |
| `description` | `str` | No | Full task description |
| `status` | `str` | Yes | Current status (e.g., `"To Do"`, `"In Progress"`, `"Done"`) |
| `assignees` | `list[str]` | Yes | List of `person_id` values — supports multiple assignees |
| `priority` | `str \| None` | No | Priority level (e.g., `"Critical"`, `"High"`, `"Medium"`, `"Low"`) |
| `sprint` | `str \| None` | No | Sprint name if applicable |
| `story_points` | `float \| None` | No | Story point estimate |
| `labels` | `list[str]` | Yes | Labels or tags |
| `created_date` | `datetime` | Yes | When the task was created in the source system |
| `updated_date` | `datetime` | Yes | When the task was last updated in the source system |
| `due_date` | `datetime \| None` | No | Task due date |
| `state_transitions` | `list[StateTransition]` | Yes | History of status changes |
| `comments` | `list[TaskComment]` | Yes | Comments on the task |
| `is_blocker` | `bool` | Yes | Whether this task is blocking other tasks |
| `blocked_by` | `list[str]` | Yes | List of `task_id` values this task is blocked by |
| `blocking` | `list[str]` | Yes | List of `task_id` values this task is blocking |
| `source_evidence` | `SourceEvidence` | Yes | Original data from source system |

### Embedded Sub-Documents

```python
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskSource(str, Enum):
    JIRA = "jira"
    SLACK_IDENTIFIED = "slack_identified"


class StateTransition(BaseModel):
    """Records a status change for audit trail and velocity calculation."""
    from_status: str
    to_status: str
    date: datetime


class TaskComment(BaseModel):
    """A comment on a task, from Jira or Slack."""
    author: str  # person_id
    text: str
    date: datetime


class SourceEvidence(BaseModel):
    """
    Links a task back to its source data. For Jira tasks, this holds
    the raw CSV row data. For Slack-identified tasks, this holds the
    message(s) where the assignment was detected.
    """
    slack_messages: list[dict] = Field(
        default_factory=list,
        description="Slack messages where this task assignment was detected"
    )
    jira_data: dict = Field(
        default_factory=dict,
        description="Raw Jira CSV row data"
    )
```

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from pydantic import Field


class Task(MongoBaseModel):
    """
    A work item from Jira CSV or an AI-identified assignment from Slack.
    Slack-identified tasks are informal assignments detected by the AI
    from conversation patterns. They always carry source_evidence linking
    back to the original messages for the COO to verify.
    """
    task_id: str = Field(default_factory=generate_uuid, description="Unique task identifier (UUID v4)")
    source: TaskSource = Field(..., description="Where this task originated")
    jira_key: Optional[str] = Field(default=None, description="Jira issue key (e.g., PROJ-123)")

    project_id: str = Field(..., description="The project this task belongs to")
    summary: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: str = Field(default="", description="Full task description")

    status: str = Field(..., description="Current status (e.g., To Do, In Progress, Done)")
    assignees: list[str] = Field(
        default_factory=list,
        description="List of person_id values — supports multiple assignees"
    )

    priority: Optional[str] = Field(default=None, description="Priority level")
    sprint: Optional[str] = Field(default=None, description="Sprint name")
    story_points: Optional[float] = Field(default=None, ge=0, description="Story point estimate")
    labels: list[str] = Field(default_factory=list, description="Labels or tags")

    created_date: datetime = Field(..., description="Creation date in source system")
    updated_date: datetime = Field(..., description="Last update date in source system")
    due_date: Optional[datetime] = Field(default=None, description="Due date")

    state_transitions: list[StateTransition] = Field(
        default_factory=list,
        description="History of status changes for velocity calculation"
    )
    comments: list[TaskComment] = Field(default_factory=list, description="Task comments")

    is_blocker: bool = Field(default=False, description="Whether this task blocks others")
    blocked_by: list[str] = Field(default_factory=list, description="task_ids this is blocked by")
    blocking: list[str] = Field(default_factory=list, description="task_ids this is blocking")

    source_evidence: SourceEvidence = Field(
        default_factory=SourceEvidence,
        description="Original data from source system for traceability"
    )
```

---

## 4. `messages` Collection

Slack messages and Jira comments stored for context and analysis. Not every raw message is stored individually — the ingestion pipeline summarizes and aggregates where appropriate (e.g., high-volume channels may store thread summaries rather than every reply). Messages that contain task assignments, decisions, or notable sentiment are always stored individually.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | `str` (UUID v4) | Yes | Unique message identifier |
| `source` | `"slack" \| "jira_comment"` | Yes | Origin system |
| `channel` | `str` | Yes | Slack channel name or Jira issue key |
| `channel_type` | `"public" \| "private" \| "dm"` | Yes | Channel visibility type |
| `project_id` | `str \| None` | No | Linked project if identifiable from channel mapping |
| `timestamp` | `datetime` | Yes | Message timestamp |
| `author` | `str` | Yes | `person_id` of the message author |
| `text` | `str` | Yes | Message content |
| `thread_id` | `str \| None` | No | Parent thread ID if this is a threaded reply |
| `is_thread_parent` | `bool` | Yes | Whether this message started a thread |
| `reply_count` | `int` | Yes | Number of replies (for thread parents) |
| `reaction_count` | `int` | Yes | Total reaction count |
| `reactions` | `list[str]` | Yes | Reaction emoji names |
| `mentions` | `list[str]` | Yes | List of `person_id` values mentioned |
| `topics` | `list[str]` | Yes | AI-extracted topic labels |
| `sentiment` | `"positive" \| "neutral" \| "negative" \| None` | No | AI-analyzed sentiment |
| `has_task_assignment` | `bool` | Yes | Whether AI detected an informal task assignment |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class MessageSource(str, Enum):
    SLACK = "slack"
    JIRA_COMMENT = "jira_comment"


class ChannelType(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    DM = "dm"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Message(MongoBaseModel):
    """
    A message from Slack or a Jira comment. Stored selectively — the ingestion
    pipeline prioritizes messages containing task assignments, decisions, risk
    signals, and notable sentiment over routine chatter.
    """
    message_id: str = Field(default_factory=generate_uuid)
    source: MessageSource = Field(...)
    channel: str = Field(..., description="Slack channel name or Jira issue key")
    channel_type: ChannelType = Field(...)
    project_id: Optional[str] = Field(default=None, description="Linked project_id")

    timestamp: datetime = Field(...)
    author: str = Field(..., description="person_id of the author")
    text: str = Field(..., description="Message content")

    thread_id: Optional[str] = Field(default=None, description="Parent thread ID")
    is_thread_parent: bool = Field(default=False)
    reply_count: int = Field(default=0, ge=0)
    reaction_count: int = Field(default=0, ge=0)
    reactions: list[str] = Field(default_factory=list, description="Reaction emoji names")

    mentions: list[str] = Field(default_factory=list, description="person_ids mentioned")
    topics: list[str] = Field(default_factory=list, description="AI-extracted topics")
    sentiment: Optional[Sentiment] = Field(default=None, description="AI-analyzed sentiment")
    has_task_assignment: bool = Field(
        default=False,
        description="AI detected an informal task assignment in this message"
    )
```

---

## 5. `documents` Collection

Google Drive file metadata and Citex ingestion status. ChiefOps does not store file content directly — files are ingested into Citex for RAG-based retrieval. This collection tracks metadata, ingestion status, and the Citex document reference for querying.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | `str` (UUID v4) | Yes | Unique document identifier |
| `file_name` | `str` | Yes | Original file name |
| `file_type` | `str` | Yes | MIME type (e.g., `application/pdf`) |
| `file_size` | `int` | Yes | File size in bytes |
| `owner` | `str` | Yes | `person_id` or raw name of the file owner |
| `created_date` | `datetime` | Yes | File creation date |
| `modified_date` | `datetime` | Yes | Last modification date |
| `sharing_scope` | `"private" \| "team" \| "company" \| "external"` | Yes | Sharing visibility |
| `folder_path` | `str` | Yes | Full folder path in Google Drive |
| `citex_doc_id` | `str \| None` | No | Citex document reference ID after ingestion |
| `citex_status` | `"pending" \| "processing" \| "completed" \| "failed"` | Yes | Citex ingestion status |
| `project_id` | `str \| None` | No | Linked project if assignable |
| `tags` | `list[str]` | Yes | Tags for categorization |
| `content_summary` | `str \| None` | No | AI-generated brief summary of document content |
| `is_indexed_in_rag` | `bool` | Yes | Whether the document is available for RAG queries |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class SharingScope(str, Enum):
    PRIVATE = "private"
    TEAM = "team"
    COMPANY = "company"
    EXTERNAL = "external"


class CitexStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(MongoBaseModel):
    """
    Google Drive file metadata and Citex ingestion tracking. File content
    lives in Citex for RAG retrieval — this collection stores metadata,
    ingestion status, and the reference ID for querying Citex.
    """
    document_id: str = Field(default_factory=generate_uuid)
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., ge=0, description="File size in bytes")

    owner: str = Field(..., description="person_id or raw name of file owner")
    created_date: datetime = Field(...)
    modified_date: datetime = Field(...)

    sharing_scope: SharingScope = Field(default=SharingScope.PRIVATE)
    folder_path: str = Field(default="", description="Full folder path in Google Drive")

    citex_doc_id: Optional[str] = Field(default=None, description="Citex document reference ID")
    citex_status: CitexStatus = Field(default=CitexStatus.PENDING, description="Citex ingestion status")

    project_id: Optional[str] = Field(default=None, description="Linked project_id")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    content_summary: Optional[str] = Field(default=None, description="AI-generated brief summary")
    is_indexed_in_rag: bool = Field(default=False, description="Available for RAG queries")
```

---

## 6. `conversation_turns` Collection

Every interaction the COO has with ChiefOps. Each user message and each assistant response is a separate turn. Turns are grouped by `stream_id` (which links to a project stream or the global stream) and `session_id` (a single sitting / conversation window). This is the raw log of all interactions, used by the memory system for fact extraction and summary generation.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `turn_id` | `str` (UUID v4) | Yes | Unique turn identifier |
| `stream_id` | `str` | Yes | Links to a project stream or the global stream |
| `source` | `"coo_chat" \| "slack_message" \| "jira_comment"` | Yes | Where this turn originated |
| `page_context` | `"main_dashboard" \| "project_view" \| "custom_dashboard" \| "report_preview"` | Yes | Which UI page the COO was on |
| `role` | `"user" \| "assistant"` | Yes | Whether this is a COO message or a ChiefOps response |
| `content` | `str` | Yes | The text content of the turn |
| `timestamp` | `datetime` | Yes | When the turn occurred |
| `session_id` | `str` | Yes | Groups turns into a single conversation session |
| `extracted_facts` | `list[str]` | Yes | List of `fact_id` values extracted from this turn |
| `charts_generated` | `list[dict]` | Yes | Chart specification references generated in this turn |
| `widgets_created` | `list[str]` | Yes | List of `widget_id` values created in this turn |
| `reports_generated` | `list[str]` | Yes | List of `report_id` values generated in this turn |

### Pydantic v2 Model

```python
from datetime import datetime
from enum import Enum


class TurnSource(str, Enum):
    COO_CHAT = "coo_chat"
    SLACK_MESSAGE = "slack_message"
    JIRA_COMMENT = "jira_comment"


class PageContext(str, Enum):
    MAIN_DASHBOARD = "main_dashboard"
    PROJECT_VIEW = "project_view"
    CUSTOM_DASHBOARD = "custom_dashboard"
    REPORT_PREVIEW = "report_preview"


class TurnRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationTurn(MongoBaseModel):
    """
    A single turn in a conversation between the COO and ChiefOps.
    Every user message and every assistant response is a separate document.
    Turns are the raw material for the memory system — facts are extracted
    from them, and session summaries are generated when sessions end.
    """
    turn_id: str = Field(default_factory=generate_uuid)
    stream_id: str = Field(..., description="Project stream or global stream reference")
    source: TurnSource = Field(default=TurnSource.COO_CHAT)
    page_context: PageContext = Field(
        default=PageContext.MAIN_DASHBOARD,
        description="Which UI page the COO was viewing"
    )

    role: TurnRole = Field(..., description="user = COO, assistant = ChiefOps")
    content: str = Field(..., description="Text content of this turn")
    timestamp: datetime = Field(default_factory=utc_now)
    session_id: str = Field(..., description="Groups turns into a conversation session")

    extracted_facts: list[str] = Field(
        default_factory=list,
        description="fact_id values extracted from this turn"
    )
    charts_generated: list[dict] = Field(
        default_factory=list,
        description="Chart spec references generated in this turn"
    )
    widgets_created: list[str] = Field(
        default_factory=list,
        description="widget_id values created in this turn"
    )
    reports_generated: list[str] = Field(
        default_factory=list,
        description="report_id values generated in this turn"
    )
```

---

## 7. `conversation_facts` Collection

Hard facts extracted from conversations. Facts are **never compacted** — they persist forever as the ground truth of what the COO has told ChiefOps. Summaries and context windows may be compressed, but facts remain intact. Facts power the correction system: when the COO says "Actually, Priya is the tech lead, not Amit," a fact of type `correction` is stored, and the `people` collection is updated accordingly.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fact_id` | `str` (UUID v4) | Yes | Unique fact identifier |
| `stream_id` | `str` | Yes | The conversation stream this fact belongs to |
| `project_id` | `str \| None` | No | Linked project (null for global facts) |
| `fact_type` | `"correction" \| "decision" \| "preference" \| "observation"` | Yes | Category of fact |
| `subject` | `str` | Yes | What the fact is about (person name, project, task, etc.) |
| `field` | `str` | Yes | What was stated or corrected (e.g., "role", "deadline", "assignee") |
| `value` | `str` | Yes | The current / corrected value |
| `previous_value` | `str \| None` | No | What it was before (if a correction) |
| `established_at` | `datetime` | Yes | When this fact was stated |
| `source_turn_id` | `str` | Yes | Which conversation turn established this fact |
| `is_active` | `bool` | Yes | Whether this fact is current (can be superseded by a newer fact) |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class FactType(str, Enum):
    CORRECTION = "correction"
    DECISION = "decision"
    PREFERENCE = "preference"
    OBSERVATION = "observation"


class ConversationFact(MongoBaseModel):
    """
    A hard fact extracted from a conversation turn. Facts are NEVER compacted
    or deleted — they are the permanent record of what the COO has communicated.

    When a new fact supersedes an old one (e.g., a role correction), the old
    fact's is_active is set to False, and the new fact references the same
    subject+field combination. Queries always filter on is_active=True to get
    the current state.

    Fact types:
    - correction: The COO corrected something AI got wrong (role, assignment, etc.)
    - decision: The COO made a decision (deadline change, priority shift, etc.)
    - preference: The COO stated a preference (report format, dashboard layout, etc.)
    - observation: The COO shared context the AI should remember (team dynamics, etc.)
    """
    fact_id: str = Field(default_factory=generate_uuid)
    stream_id: str = Field(..., description="Conversation stream this fact belongs to")
    project_id: Optional[str] = Field(
        default=None,
        description="Linked project_id (null for global facts)"
    )

    fact_type: FactType = Field(..., description="Category of fact")
    subject: str = Field(..., description="What the fact is about")
    field: str = Field(..., description="What was stated or corrected")
    value: str = Field(..., description="The current / corrected value")
    previous_value: Optional[str] = Field(
        default=None,
        description="Previous value (for corrections)"
    )

    established_at: datetime = Field(default_factory=utc_now)
    source_turn_id: str = Field(..., description="Conversation turn that established this fact")
    is_active: bool = Field(default=True, description="False if superseded by a newer fact")
```

---

## 8. `session_summaries` Collection

AI-generated summaries created when a conversation session ends (or at periodic intervals for long sessions). These summaries capture the key points of a conversation without storing every turn in the LLM context window. Session summaries are the first tier of the memory compaction pipeline.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary_id` | `str` (UUID v4) | Yes | Unique summary identifier |
| `stream_id` | `str` | Yes | The conversation stream this summary belongs to |
| `session_id` | `str` | Yes | The session that was summarized |
| `summary_text` | `str` | Yes | The AI-generated summary |
| `turn_range` | `TurnRange` | Yes | Start and end turn IDs covered by this summary |
| `key_topics` | `list[str]` | Yes | Main topics discussed |
| `facts_extracted` | `list[str]` | Yes | List of `fact_id` values extracted during this session |
| `created_at` | `datetime` | Yes | When the summary was generated |
| `compacted_into` | `str \| None` | No | Reference to a compacted summary if this session summary has been rolled up |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional


class TurnRange(BaseModel):
    """Defines the range of conversation turns covered by a summary."""
    start_turn_id: str
    end_turn_id: str


class SessionSummary(MongoBaseModel):
    """
    AI-generated summary of a conversation session. Created when a session
    ends or at periodic intervals during long sessions. Session summaries
    are the first tier of the memory compaction pipeline — they get rolled
    up into compacted summaries over time.
    """
    summary_id: str = Field(default_factory=generate_uuid)
    stream_id: str = Field(...)
    session_id: str = Field(...)
    summary_text: str = Field(..., description="AI-generated session summary")

    turn_range: TurnRange = Field(..., description="Start and end turn IDs")
    key_topics: list[str] = Field(default_factory=list, description="Main topics discussed")
    facts_extracted: list[str] = Field(
        default_factory=list,
        description="fact_id values extracted during this session"
    )

    compacted_into: Optional[str] = Field(
        default=None,
        description="compacted_summary_id if rolled up, null otherwise"
    )
```

---

## 9. `compacted_summaries` Collection

Progressively compacted summaries for long-term memory. As session summaries accumulate, they are rolled up into weekly summaries, then monthly summaries, then archived summaries. Each compaction level reduces token count while preserving the most important context. Facts are never lost in compaction — only narrative summaries are compressed.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary_id` | `str` (UUID v4) | Yes | Unique compacted summary identifier |
| `stream_id` | `str` | Yes | The conversation stream |
| `scope` | `"weekly" \| "monthly" \| "archive"` | Yes | Compaction level |
| `period_start` | `datetime` | Yes | Start of the period covered |
| `period_end` | `datetime` | Yes | End of the period covered |
| `summary_text` | `str` | Yes | The compacted summary text |
| `token_count` | `int` | Yes | Token count of the summary (for context window budgeting) |
| `source_sessions` | `list[str]` | Yes | List of session summary IDs or previous compacted summary IDs |
| `created_at` | `datetime` | Yes | When this compacted summary was generated |

### Pydantic v2 Model

```python
from datetime import datetime
from enum import Enum


class CompactionScope(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ARCHIVE = "archive"


class CompactedSummary(MongoBaseModel):
    """
    A progressively compacted summary for long-term memory. The compaction
    pipeline rolls up session summaries into weekly, then monthly, then
    archive-level summaries. Each level reduces token count while
    preserving the most operationally relevant context.

    Token counts are tracked so the context assembly system can budget
    how much memory to include in each LLM call.
    """
    summary_id: str = Field(default_factory=generate_uuid)
    stream_id: str = Field(...)
    scope: CompactionScope = Field(..., description="Compaction level")

    period_start: datetime = Field(..., description="Start of covered period")
    period_end: datetime = Field(..., description="End of covered period")

    summary_text: str = Field(..., description="Compacted summary text")
    token_count: int = Field(..., ge=0, description="Token count for context window budgeting")

    source_sessions: list[str] = Field(
        default_factory=list,
        description="Session summary IDs or previous compacted summary IDs that were rolled up"
    )
```

---

## 10. `project_streams` Collection

Per-project conversational stream metadata. Every project gets its own conversation stream so that project-specific context, facts, and summaries are isolated. There is also a single global stream (`project_id=None`) for cross-project conversations. This collection tracks the active summary state and statistics for each stream.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stream_id` | `str` (UUID v4) | Yes | Unique stream identifier |
| `project_id` | `str \| None` | No | Linked project (null for the global stream) |
| `active_summary` | `ActiveSummary` | Yes | Current rolling summary state |
| `fact_count` | `int` | Yes | Total facts in this stream |
| `total_turns` | `int` | Yes | Total conversation turns in this stream |
| `last_activity_at` | `datetime` | Yes | Most recent turn timestamp |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional


class ActiveSummary(BaseModel):
    """The current rolling summary state for a conversation stream."""
    text: str = ""
    token_count: int = 0
    last_compacted: Optional[datetime] = None


class ProjectStream(MongoBaseModel):
    """
    Metadata for a per-project conversation stream. Each project has its
    own stream for isolated context. The global stream (project_id=None)
    handles cross-project conversations and general preferences.
    """
    stream_id: str = Field(default_factory=generate_uuid)
    project_id: Optional[str] = Field(
        default=None,
        description="Linked project_id (null for global stream)"
    )

    active_summary: ActiveSummary = Field(
        default_factory=ActiveSummary,
        description="Current rolling summary state"
    )
    fact_count: int = Field(default=0, ge=0)
    total_turns: int = Field(default=0, ge=0)
    last_activity_at: datetime = Field(default_factory=utc_now)
```

---

## 11. `dashboard_widgets` Collection

Dynamic widgets created by the COO through natural language conversation. When the COO says "Show me a bar chart of tasks per person for Project Alpha," ChiefOps generates a widget specification, stores it here, and renders it on the dashboard. Widgets can also be system defaults created during project initialization.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `widget_id` | `str` (UUID v4) | Yes | Unique widget identifier |
| `dashboard_id` | `str` | Yes | Format: `"{project_id}_custom"` or `"main"` |
| `widget_type` | enum (see below) | Yes | The visualization type |
| `title` | `str` | Yes | Display title |
| `data_query` | `DataQuery` | Yes | What data to fetch and how to aggregate it |
| `chart_spec` | `dict` | Yes | ECharts JSON configuration for rendering |
| `position` | `WidgetPosition` | Yes | Grid position on the dashboard |
| `created_by` | `"coo_conversation" \| "system_default"` | Yes | How the widget was created |
| `created_at` | `datetime` | Yes | Creation timestamp |
| `updated_at` | `datetime` | Yes | Last modification timestamp |
| `conversation_turn_id` | `str \| None` | No | Which conversation turn created this widget |

### Embedded Sub-Documents

```python
from enum import Enum
from typing import Optional


class WidgetType(str, Enum):
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    GANTT = "gantt"
    TABLE = "table"
    KPI_CARD = "kpi_card"
    SUMMARY_TEXT = "summary_text"
    PERSON_GRID = "person_grid"
    TIMELINE = "timeline"
    ACTIVITY_FEED = "activity_feed"


class WidgetCreator(str, Enum):
    COO_CONVERSATION = "coo_conversation"
    SYSTEM_DEFAULT = "system_default"


class DataQuery(BaseModel):
    """
    Defines what data to fetch and how to aggregate it for a widget.
    This is the abstract query specification — the backend resolves it
    into actual MongoDB aggregation pipelines at render time.
    """
    source: str = Field(..., description="Collection to query (e.g., 'tasks', 'people', 'messages')")
    group_by: Optional[str] = Field(default=None, description="Field to group by")
    metric: str = Field(..., description="What to measure (e.g., 'count', 'sum:story_points')")
    split_by: Optional[str] = Field(default=None, description="Secondary grouping for stacked charts")
    filters: dict = Field(default_factory=dict, description="Query filters as key-value pairs")
    time_range: Optional[dict] = Field(
        default=None,
        description="Time range filter: {start: datetime, end: datetime, field: str}"
    )


class WidgetPosition(BaseModel):
    """Grid position for dashboard layout."""
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    width: int = Field(ge=1, le=12, description="Grid columns (1-12)")
    height: int = Field(ge=1, le=8, description="Grid rows (1-8)")
```

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from pydantic import Field


class DashboardWidget(MongoBaseModel):
    """
    A dynamic widget on a dashboard. Widgets are created either by the COO
    through natural language ("Show me a bar chart of tasks per person") or
    as system defaults during project initialization.

    The data_query field defines WHAT to show. The chart_spec field defines
    HOW to render it (ECharts JSON). The backend resolves data_query into
    MongoDB aggregation pipelines and populates chart_spec with real data
    at render time.
    """
    widget_id: str = Field(default_factory=generate_uuid)
    dashboard_id: str = Field(
        ...,
        description="Format: '{project_id}_custom' or 'main'"
    )

    widget_type: WidgetType = Field(..., description="Visualization type")
    title: str = Field(..., min_length=1, max_length=200, description="Display title")

    data_query: DataQuery = Field(..., description="What data to fetch and how to aggregate")
    chart_spec: dict = Field(
        default_factory=dict,
        description="ECharts JSON configuration for rendering"
    )

    position: WidgetPosition = Field(
        default_factory=lambda: WidgetPosition(row=0, col=0, width=6, height=4),
        description="Grid position on the dashboard"
    )

    created_by: WidgetCreator = Field(
        default=WidgetCreator.COO_CONVERSATION,
        description="How the widget was created"
    )
    conversation_turn_id: Optional[str] = Field(
        default=None,
        description="Conversation turn that created this widget"
    )
```

---

## 12. `reports` Collection

Generated reports with full edit history. Reports are created through conversation and can be iteratively refined. Each report has a JSON specification defining its sections, and the system generates PDF exports on demand. The version field tracks how many times the report has been edited through conversation.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report_id` | `str` (UUID v4) | Yes | Unique report identifier |
| `project_id` | `str \| None` | No | Linked project (null for cross-project reports) |
| `report_type` | enum (see below) | Yes | Report category |
| `title` | `str` | Yes | Report title |
| `subtitle` | `str` | No | Report subtitle |
| `report_spec` | `dict` | Yes | Full JSON specification with sections, charts, and data references |
| `generated_at` | `datetime` | Yes | Initial generation timestamp |
| `last_modified` | `datetime` | Yes | Last modification timestamp |
| `status` | `"draft" \| "finalized" \| "exported"` | Yes | Report lifecycle status |
| `exports` | `list[ReportExport]` | Yes | Export history |
| `conversation_turns` | `list[str]` | Yes | Turn IDs that created or modified this report |
| `version` | `int` | Yes | Edit count (incremented on each modification) |
| `branding` | `ReportBranding` | Yes | Visual branding configuration |

### Embedded Sub-Documents

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class ReportType(str, Enum):
    BOARD_SUMMARY = "board_summary"
    PROJECT_STATUS = "project_status"
    TEAM_PERFORMANCE = "team_performance"
    RISK_ASSESSMENT = "risk_assessment"
    SPRINT_REPORT = "sprint_report"
    RESOURCE_UTILIZATION = "resource_utilization"
    TECHNICAL_DUE_DILIGENCE = "technical_due_diligence"
    CUSTOM = "custom"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class ReportExport(BaseModel):
    """Record of a report export."""
    format: str = "pdf"  # Currently only PDF; future: pptx, html
    url: str = Field(..., description="Download URL for the exported file")
    exported_at: datetime = Field(default_factory=utc_now)


class ReportBranding(BaseModel):
    """Visual branding for report generation."""
    company: str = ""
    logo_url: Optional[str] = None
    color_scheme: dict = Field(
        default_factory=lambda: {
            "primary": "#1a1a2e",
            "secondary": "#16213e",
            "accent": "#0f3460",
            "highlight": "#e94560"
        },
        description="Color scheme as named hex values"
    )
```

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from pydantic import Field


class Report(MongoBaseModel):
    """
    A generated report with full edit history. Reports are created through
    conversation and iteratively refined. The report_spec contains the full
    JSON specification — sections, charts, data references, and layout.

    The version field tracks conversational edits: each time the COO says
    "change the title" or "add a section on risks," the version increments
    and the report_spec is updated. The conversation_turns list provides
    a full audit trail of which turns shaped this report.
    """
    report_id: str = Field(default_factory=generate_uuid)
    project_id: Optional[str] = Field(
        default=None,
        description="Linked project (null for cross-project reports)"
    )

    report_type: ReportType = Field(..., description="Report category")
    title: str = Field(..., min_length=1, max_length=300, description="Report title")
    subtitle: str = Field(default="", description="Report subtitle")

    report_spec: dict = Field(
        default_factory=dict,
        description="Full JSON specification: sections, charts, data references, layout"
    )

    generated_at: datetime = Field(default_factory=utc_now)
    last_modified: datetime = Field(default_factory=utc_now)

    status: ReportStatus = Field(default=ReportStatus.DRAFT, description="Lifecycle status")

    exports: list[ReportExport] = Field(default_factory=list, description="Export history")

    conversation_turns: list[str] = Field(
        default_factory=list,
        description="Turn IDs that created or modified this report"
    )
    version: int = Field(default=1, ge=1, description="Edit count")

    branding: ReportBranding = Field(
        default_factory=ReportBranding,
        description="Visual branding configuration"
    )
```

---

## 13. `alerts` Collection

Configured alert thresholds and their trigger history. Alerts are created through conversation (e.g., "Alert me if Project Alpha's health score drops below 60") or by the system as defaults. Each alert monitors a condition and tracks when it was triggered and resolved.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `alert_id` | `str` (UUID v4) | Yes | Unique alert identifier |
| `project_id` | `str \| None` | No | Linked project (null for global alerts) |
| `alert_type` | `str` | Yes | Category (e.g., `"health_score"`, `"deadline_risk"`, `"blocked_tasks"`, `"activity_drop"`) |
| `condition` | `str` | Yes | Human-readable condition description |
| `threshold` | `float` | Yes | Numeric threshold value |
| `current_value` | `float` | Yes | Current measured value |
| `status` | `"active" \| "resolved" \| "acknowledged"` | Yes | Alert lifecycle status |
| `triggered_at` | `datetime` | Yes | When the alert was triggered |
| `resolved_at` | `datetime \| None` | No | When the alert was resolved |
| `created_by_turn_id` | `str \| None` | No | Conversation turn that created this alert |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class Alert(MongoBaseModel):
    """
    A configured alert with threshold monitoring. Alerts fire when a
    monitored metric crosses a threshold and resolve when the condition
    clears. The COO can acknowledge alerts to silence them temporarily.
    """
    alert_id: str = Field(default_factory=generate_uuid)
    project_id: Optional[str] = Field(default=None, description="Linked project (null for global)")

    alert_type: str = Field(..., description="Alert category (e.g., health_score, deadline_risk)")
    condition: str = Field(..., description="Human-readable condition description")
    threshold: float = Field(..., description="Numeric threshold value")
    current_value: float = Field(..., description="Current measured value")

    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="Alert lifecycle status")
    triggered_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = Field(default=None)

    created_by_turn_id: Optional[str] = Field(default=None, description="Conversation turn that created this")
```

---

## 14. `ingestion_jobs` Collection

Tracks the status of file ingestion pipelines. When the COO uploads a Slack ZIP, Jira CSV, or Google Drive folder, an ingestion job is created to track progress through parsing, entity resolution, and analysis stages.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | `str` (UUID v4) | Yes | Unique job identifier |
| `file_name` | `str` | Yes | Name of the uploaded file or folder |
| `file_type` | `"slack_zip" \| "slack_api" \| "jira_csv" \| "gdrive_folder"` | Yes | Type of data source |
| `status` | `"queued" \| "processing" \| "completed" \| "failed"` | Yes | Job lifecycle status |
| `progress` | `IngestionProgress` | Yes | Current stage and percentage |
| `stats` | `IngestionStats` | Yes | Processing statistics |
| `errors` | `list[str]` | Yes | Error messages if any |
| `started_at` | `datetime \| None` | No | When processing began |
| `completed_at` | `datetime \| None` | No | When processing finished |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class IngestionFileType(str, Enum):
    SLACK_ZIP = "slack_zip"
    SLACK_API = "slack_api"
    JIRA_CSV = "jira_csv"
    GDRIVE_FOLDER = "gdrive_folder"


class IngestionStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionProgress(BaseModel):
    """Current progress of an ingestion job."""
    stage: str = Field(default="queued", description="Current processing stage")
    percentage: float = Field(default=0.0, ge=0.0, le=100.0)


class IngestionStats(BaseModel):
    """Processing statistics for an ingestion job."""
    messages_processed: int = 0
    tasks_processed: int = 0
    documents_processed: int = 0


class IngestionJob(MongoBaseModel):
    """
    Tracks a file ingestion pipeline from upload to completion.
    Progress is reported in stages:
    - slack_zip: extracting -> parsing_messages -> resolving_people -> analyzing
    - jira_csv: parsing_rows -> mapping_tasks -> resolving_people -> analyzing
    - gdrive_folder: scanning_files -> ingesting_to_citex -> indexing -> analyzing
    """
    job_id: str = Field(default_factory=generate_uuid)
    file_name: str = Field(..., description="Uploaded file or folder name")
    file_type: IngestionFileType = Field(..., description="Data source type")

    status: IngestionStatus = Field(default=IngestionStatus.QUEUED)
    progress: IngestionProgress = Field(default_factory=IngestionProgress)
    stats: IngestionStats = Field(default_factory=IngestionStats)
    errors: list[str] = Field(default_factory=list)

    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
```

---

## 15. `analysis_results` Collection

Cached analysis results from AI processing. AI analysis is expensive — results are cached with a data snapshot hash so they can be reused until the underlying data changes. When new data is ingested, the hash changes and the cached result is marked stale.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `analysis_id` | `str` (UUID v4) | Yes | Unique analysis identifier |
| `analysis_type` | enum (see below) | Yes | Type of analysis performed |
| `project_id` | `str \| None` | No | Linked project if project-scoped |
| `result_data` | `dict` | Yes | The analysis output (structure varies by type) |
| `data_snapshot_hash` | `str` | Yes | Hash of input data for cache invalidation |
| `created_at` | `datetime` | Yes | When the analysis was run |
| `is_stale` | `bool` | Yes | True if underlying data has changed since this analysis |

### Pydantic v2 Model

```python
from datetime import datetime
from typing import Optional
from enum import Enum


class AnalysisType(str, Enum):
    PEOPLE_IDENTIFICATION = "people_identification"
    PROJECT_DETECTION = "project_detection"
    TASK_MAPPING = "task_mapping"
    GAP_DETECTION = "gap_detection"
    TECHNICAL_FEASIBILITY = "technical_feasibility"
    HEALTH_SCORE = "health_score"


class AnalysisResult(MongoBaseModel):
    """
    Cached AI analysis result. Analysis is expensive, so results are
    cached with a data_snapshot_hash. When new data is ingested, the
    hash of the input data changes, and is_stale is set to True.
    Stale results are re-computed on next access.

    result_data structure varies by analysis_type:
    - people_identification: {identified: [...], confidence_scores: {...}}
    - project_detection: {projects: [...], channel_mappings: {...}}
    - task_mapping: {tasks: [...], assignments: [...]}
    - gap_detection: {gaps: [...], severity: {...}}
    - technical_feasibility: {concerns: [...], questions: [...]}
    - health_score: {score: int, factors: {...}, trend: [...]}
    """
    analysis_id: str = Field(default_factory=generate_uuid)
    analysis_type: AnalysisType = Field(...)
    project_id: Optional[str] = Field(default=None)

    result_data: dict = Field(
        default_factory=dict,
        description="Analysis output (structure varies by analysis_type)"
    )
    data_snapshot_hash: str = Field(
        ...,
        description="Hash of input data for cache invalidation"
    )

    is_stale: bool = Field(default=False, description="True if underlying data has changed")
```

---

## 16. Indexes

All indexes are defined for query performance, uniqueness constraints, and text search. Compound indexes are ordered by selectivity (most selective field first).

### `people` Collection

```javascript
// Unique identifier
db.people.createIndex({ "person_id": 1 }, { unique: true })

// Lookup by email (sparse — only indexes documents where email exists)
db.people.createIndex({ "email": 1 }, { sparse: true })

// Lookup by Slack user ID
db.people.createIndex({ "slack_user_id": 1 }, { sparse: true })

// Lookup by Jira username
db.people.createIndex({ "jira_username": 1 }, { sparse: true })

// Filter by activity level + last active (for "who is inactive?" queries)
db.people.createIndex({ "activity_level": 1, "last_active_date": -1 })

// Filter by department
db.people.createIndex({ "department": 1 })

// Cross-reference lookup: find person by source system ID
db.people.createIndex({ "source_ids.source": 1, "source_ids.source_id": 1 })

// Find people in a specific project
db.people.createIndex({ "projects": 1 })

// Text search on name for fuzzy person lookup
db.people.createIndex({ "name": "text", "email": "text" })
```

### `projects` Collection

```javascript
// Unique identifier
db.projects.createIndex({ "project_id": 1 }, { unique: true })

// Filter by status (most common dashboard query)
db.projects.createIndex({ "status": 1, "health_score": 1 })

// Lookup by Jira project key
db.projects.createIndex({ "jira_project_keys": 1 })

// Lookup by Slack channel
db.projects.createIndex({ "slack_channels": 1 })

// Sort by health score (for "which projects are struggling?" queries)
db.projects.createIndex({ "health_score": 1 })

// Text search on project name and description
db.projects.createIndex({ "name": "text", "description": "text" })
```

### `tasks` Collection

```javascript
// Unique identifier
db.tasks.createIndex({ "task_id": 1 }, { unique: true })

// Lookup by Jira key (sparse — only for Jira-sourced tasks)
db.tasks.createIndex({ "jira_key": 1 }, { sparse: true })

// Tasks for a project, sorted by status (most common query)
db.tasks.createIndex({ "project_id": 1, "status": 1 })

// Tasks assigned to a person
db.tasks.createIndex({ "assignees": 1, "status": 1 })

// Blocker queries
db.tasks.createIndex({ "is_blocker": 1, "project_id": 1 })

// Tasks by priority within a project
db.tasks.createIndex({ "project_id": 1, "priority": 1 })

// Sprint-based filtering
db.tasks.createIndex({ "sprint": 1, "status": 1 })

// Due date queries (upcoming deadlines)
db.tasks.createIndex({ "due_date": 1 }, { sparse: true })

// Source type filtering
db.tasks.createIndex({ "source": 1 })
```

### `messages` Collection

```javascript
// Unique identifier
db.messages.createIndex({ "message_id": 1 }, { unique: true })

// Messages in a channel, sorted by time (primary query pattern)
db.messages.createIndex({ "channel": 1, "timestamp": -1 })

// Messages by author
db.messages.createIndex({ "author": 1, "timestamp": -1 })

// Messages for a project
db.messages.createIndex({ "project_id": 1, "timestamp": -1 })

// Thread queries
db.messages.createIndex({ "thread_id": 1 })

// Find messages with task assignments (for task detection pipeline)
db.messages.createIndex({ "has_task_assignment": 1, "timestamp": -1 })

// Sentiment analysis queries
db.messages.createIndex({ "sentiment": 1, "project_id": 1 })

// Text search on message content
db.messages.createIndex({ "text": "text" })
```

### `documents` Collection

```javascript
// Unique identifier
db.documents.createIndex({ "document_id": 1 }, { unique: true })

// Citex ingestion status tracking
db.documents.createIndex({ "citex_status": 1 })

// Documents for a project
db.documents.createIndex({ "project_id": 1 })

// Documents by owner
db.documents.createIndex({ "owner": 1 })

// RAG-indexed documents
db.documents.createIndex({ "is_indexed_in_rag": 1 })

// File type filtering
db.documents.createIndex({ "file_type": 1 })

// Text search on file name and content summary
db.documents.createIndex({ "file_name": "text", "content_summary": "text" })
```

### `conversation_turns` Collection

```javascript
// Unique identifier
db.conversation_turns.createIndex({ "turn_id": 1 }, { unique: true })

// Turns in a stream, sorted by time (primary query for context assembly)
db.conversation_turns.createIndex({ "stream_id": 1, "timestamp": -1 })

// Turns in a session, sorted by time
db.conversation_turns.createIndex({ "session_id": 1, "timestamp": 1 })

// Recent turns across all streams (for global activity view)
db.conversation_turns.createIndex({ "timestamp": -1 })
```

### `conversation_facts` Collection

```javascript
// Unique identifier
db.conversation_facts.createIndex({ "fact_id": 1 }, { unique: true })

// Active facts for a stream (primary query for context assembly)
db.conversation_facts.createIndex({ "stream_id": 1, "is_active": 1 })

// Active facts for a project
db.conversation_facts.createIndex({ "project_id": 1, "is_active": 1 })

// Fact lookup by subject + field (for superseding old facts)
db.conversation_facts.createIndex({ "subject": 1, "field": 1, "is_active": 1 })

// Facts by type (for "show me all corrections" queries)
db.conversation_facts.createIndex({ "fact_type": 1, "is_active": 1 })

// Source turn lookup (for audit trail)
db.conversation_facts.createIndex({ "source_turn_id": 1 })
```

### `session_summaries` Collection

```javascript
// Unique identifier
db.session_summaries.createIndex({ "summary_id": 1 }, { unique: true })

// Summaries for a stream (for compaction pipeline)
db.session_summaries.createIndex({ "stream_id": 1, "created_at": -1 })

// Uncompacted summaries (for compaction candidates)
db.session_summaries.createIndex({ "compacted_into": 1 })

// Summaries for a session
db.session_summaries.createIndex({ "session_id": 1 })
```

### `compacted_summaries` Collection

```javascript
// Unique identifier
db.compacted_summaries.createIndex({ "summary_id": 1 }, { unique: true })

// Summaries for a stream by scope and period (for context assembly)
db.compacted_summaries.createIndex({ "stream_id": 1, "scope": 1, "period_end": -1 })
```

### `project_streams` Collection

```javascript
// Unique identifier
db.project_streams.createIndex({ "stream_id": 1 }, { unique: true })

// Lookup stream by project (most common access pattern)
db.project_streams.createIndex({ "project_id": 1 }, { unique: true })
```

### `dashboard_widgets` Collection

```javascript
// Unique identifier
db.dashboard_widgets.createIndex({ "widget_id": 1 }, { unique: true })

// Widgets for a dashboard (primary query for rendering)
db.dashboard_widgets.createIndex({ "dashboard_id": 1 })
```

### `reports` Collection

```javascript
// Unique identifier
db.reports.createIndex({ "report_id": 1 }, { unique: true })

// Reports for a project
db.reports.createIndex({ "project_id": 1, "generated_at": -1 })

// Reports by type
db.reports.createIndex({ "report_type": 1, "status": 1 })

// Recent reports
db.reports.createIndex({ "generated_at": -1 })
```

### `alerts` Collection

```javascript
// Unique identifier
db.alerts.createIndex({ "alert_id": 1 }, { unique: true })

// Active alerts (dashboard query)
db.alerts.createIndex({ "status": 1, "triggered_at": -1 })

// Alerts for a project
db.alerts.createIndex({ "project_id": 1, "status": 1 })
```

### `ingestion_jobs` Collection

```javascript
// Unique identifier
db.ingestion_jobs.createIndex({ "job_id": 1 }, { unique: true })

// Active jobs (for progress monitoring)
db.ingestion_jobs.createIndex({ "status": 1, "created_at": -1 })
```

### `analysis_results` Collection

```javascript
// Unique identifier
db.analysis_results.createIndex({ "analysis_id": 1 }, { unique: true })

// Cache lookup: find analysis by type + project + freshness
db.analysis_results.createIndex({ "analysis_type": 1, "project_id": 1, "is_stale": 1 })

// Cache invalidation by data hash
db.analysis_results.createIndex({ "data_snapshot_hash": 1 })
```

---

## Collection Relationship Diagram

```
people <──────────── projects (people_involved.person_id)
  │                     │
  │                     ├──── tasks (project_id)
  │                     │       │
  │                     │       └── task.assignees ──> people
  │                     │
  │                     ├──── messages (project_id)
  │                     │       │
  │                     │       └── message.author ──> people
  │                     │
  │                     ├──── documents (project_id)
  │                     │
  │                     ├──── project_streams (project_id)
  │                     │       │
  │                     │       ├── conversation_turns (stream_id)
  │                     │       │       │
  │                     │       │       └── conversation_facts (source_turn_id)
  │                     │       │
  │                     │       ├── session_summaries (stream_id)
  │                     │       │       │
  │                     │       │       └── compacted_summaries (stream_id)
  │                     │       │
  │                     │       └── conversation_facts (stream_id)
  │                     │
  │                     ├──── dashboard_widgets (dashboard_id contains project_id)
  │                     │
  │                     ├──── reports (project_id)
  │                     │
  │                     ├──── alerts (project_id)
  │                     │
  │                     └──── analysis_results (project_id)
  │
  └──────────────────── ingestion_jobs (standalone — tracks file processing)
```

---

## Data Flow Summary

1. **Ingestion:** Files uploaded by the COO create `ingestion_jobs`. The pipeline parses raw data into `messages`, `tasks`, and `documents`.

2. **Entity Resolution:** The AI identifies unique people across sources and creates/updates `people` records. It detects project boundaries and creates `projects`.

3. **Analysis:** AI processing generates `analysis_results` (cached). Health scores, risk assessments, and gap detection are stored here.

4. **Conversation:** COO interactions create `conversation_turns`. The memory system extracts `conversation_facts` and generates `session_summaries`, which compact into `compacted_summaries` over time. Each project has a `project_stream`.

5. **Visualization:** COO requests create `dashboard_widgets` and `reports`. Alert thresholds create `alerts`.

6. **Feedback Loop:** COO corrections (stored as `conversation_facts` with `fact_type=correction`) update `people`, `projects`, and `tasks` records, improving accuracy over time.

---

## Motor Async Access Pattern

All database access uses Motor's async interface. Here is the standard access pattern used throughout the codebase:

```python
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT


class Database:
    """
    Async MongoDB access via Motor. Singleton per application instance.
    All collection access goes through this class to ensure indexes
    are created on startup and connection pooling is managed correctly.
    """

    def __init__(self, connection_string: str, database_name: str = "chiefops"):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client[database_name]

    # --- Collection accessors ---

    @property
    def people(self):
        return self.db["people"]

    @property
    def projects(self):
        return self.db["projects"]

    @property
    def tasks(self):
        return self.db["tasks"]

    @property
    def messages(self):
        return self.db["messages"]

    @property
    def documents(self):
        return self.db["documents"]

    @property
    def conversation_turns(self):
        return self.db["conversation_turns"]

    @property
    def conversation_facts(self):
        return self.db["conversation_facts"]

    @property
    def session_summaries(self):
        return self.db["session_summaries"]

    @property
    def compacted_summaries(self):
        return self.db["compacted_summaries"]

    @property
    def project_streams(self):
        return self.db["project_streams"]

    @property
    def dashboard_widgets(self):
        return self.db["dashboard_widgets"]

    @property
    def reports(self):
        return self.db["reports"]

    @property
    def alerts(self):
        return self.db["alerts"]

    @property
    def ingestion_jobs(self):
        return self.db["ingestion_jobs"]

    @property
    def analysis_results(self):
        return self.db["analysis_results"]

    # --- Lifecycle ---

    async def ensure_indexes(self):
        """Create all indexes on startup. Idempotent — safe to call multiple times."""

        # People indexes
        await self.people.create_indexes([
            IndexModel([("person_id", ASCENDING)], unique=True),
            IndexModel([("email", ASCENDING)], sparse=True),
            IndexModel([("slack_user_id", ASCENDING)], sparse=True),
            IndexModel([("jira_username", ASCENDING)], sparse=True),
            IndexModel([("activity_level", ASCENDING), ("last_active_date", DESCENDING)]),
            IndexModel([("department", ASCENDING)]),
            IndexModel([("source_ids.source", ASCENDING), ("source_ids.source_id", ASCENDING)]),
            IndexModel([("projects", ASCENDING)]),
        ])

        # Projects indexes
        await self.projects.create_indexes([
            IndexModel([("project_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("health_score", ASCENDING)]),
            IndexModel([("jira_project_keys", ASCENDING)]),
            IndexModel([("slack_channels", ASCENDING)]),
            IndexModel([("health_score", ASCENDING)]),
        ])

        # Tasks indexes
        await self.tasks.create_indexes([
            IndexModel([("task_id", ASCENDING)], unique=True),
            IndexModel([("jira_key", ASCENDING)], sparse=True),
            IndexModel([("project_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("assignees", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("is_blocker", ASCENDING), ("project_id", ASCENDING)]),
            IndexModel([("project_id", ASCENDING), ("priority", ASCENDING)]),
            IndexModel([("sprint", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("due_date", ASCENDING)], sparse=True),
            IndexModel([("source", ASCENDING)]),
        ])

        # Messages indexes
        await self.messages.create_indexes([
            IndexModel([("message_id", ASCENDING)], unique=True),
            IndexModel([("channel", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("author", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("project_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("thread_id", ASCENDING)]),
            IndexModel([("has_task_assignment", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("sentiment", ASCENDING), ("project_id", ASCENDING)]),
        ])

        # Documents indexes
        await self.documents.create_indexes([
            IndexModel([("document_id", ASCENDING)], unique=True),
            IndexModel([("citex_status", ASCENDING)]),
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("owner", ASCENDING)]),
            IndexModel([("is_indexed_in_rag", ASCENDING)]),
            IndexModel([("file_type", ASCENDING)]),
        ])

        # Conversation turns indexes
        await self.conversation_turns.create_indexes([
            IndexModel([("turn_id", ASCENDING)], unique=True),
            IndexModel([("stream_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("session_id", ASCENDING), ("timestamp", ASCENDING)]),
            IndexModel([("timestamp", DESCENDING)]),
        ])

        # Conversation facts indexes
        await self.conversation_facts.create_indexes([
            IndexModel([("fact_id", ASCENDING)], unique=True),
            IndexModel([("stream_id", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("project_id", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("subject", ASCENDING), ("field", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("fact_type", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("source_turn_id", ASCENDING)]),
        ])

        # Session summaries indexes
        await self.session_summaries.create_indexes([
            IndexModel([("summary_id", ASCENDING)], unique=True),
            IndexModel([("stream_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("compacted_into", ASCENDING)]),
            IndexModel([("session_id", ASCENDING)]),
        ])

        # Compacted summaries indexes
        await self.compacted_summaries.create_indexes([
            IndexModel([("summary_id", ASCENDING)], unique=True),
            IndexModel([("stream_id", ASCENDING), ("scope", ASCENDING), ("period_end", DESCENDING)]),
        ])

        # Project streams indexes
        await self.project_streams.create_indexes([
            IndexModel([("stream_id", ASCENDING)], unique=True),
            IndexModel([("project_id", ASCENDING)], unique=True),
        ])

        # Dashboard widgets indexes
        await self.dashboard_widgets.create_indexes([
            IndexModel([("widget_id", ASCENDING)], unique=True),
            IndexModel([("dashboard_id", ASCENDING)]),
        ])

        # Reports indexes
        await self.reports.create_indexes([
            IndexModel([("report_id", ASCENDING)], unique=True),
            IndexModel([("project_id", ASCENDING), ("generated_at", DESCENDING)]),
            IndexModel([("report_type", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("generated_at", DESCENDING)]),
        ])

        # Alerts indexes
        await self.alerts.create_indexes([
            IndexModel([("alert_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("triggered_at", DESCENDING)]),
            IndexModel([("project_id", ASCENDING), ("status", ASCENDING)]),
        ])

        # Ingestion jobs indexes
        await self.ingestion_jobs.create_indexes([
            IndexModel([("job_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # Analysis results indexes
        await self.analysis_results.create_indexes([
            IndexModel([("analysis_id", ASCENDING)], unique=True),
            IndexModel([("analysis_type", ASCENDING), ("project_id", ASCENDING), ("is_stale", ASCENDING)]),
            IndexModel([("data_snapshot_hash", ASCENDING)]),
        ])

    async def close(self):
        """Close the Motor client connection."""
        self.client.close()
```

---

## Serialization Helpers

Pydantic v2 models serialize to and from MongoDB documents using these helpers:

```python
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def to_mongo(model: BaseModel) -> dict:
    """Convert a Pydantic model to a MongoDB-ready dict."""
    return model.model_dump(by_alias=True, exclude_none=False)


async def from_mongo(collection, query: dict, model_class: Type[T]) -> T | None:
    """Fetch a single document and parse it into a Pydantic model."""
    doc = await collection.find_one(query)
    if doc is None:
        return None
    doc.pop("_id", None)  # Remove MongoDB's ObjectId before parsing
    return model_class.model_validate(doc)


async def from_mongo_many(
    collection, query: dict, model_class: Type[T],
    sort: list | None = None, limit: int = 0
) -> list[T]:
    """Fetch multiple documents and parse them into Pydantic models."""
    cursor = collection.find(query)
    if sort:
        cursor = cursor.sort(sort)
    if limit > 0:
        cursor = cursor.limit(limit)

    results = []
    async for doc in cursor:
        doc.pop("_id", None)
        results.append(model_class.model_validate(doc))
    return results
```

---

## Notes for the Engineering Team

1. **Text indexes:** MongoDB allows only one text index per collection. The text indexes defined above cover the most common search fields. If additional text search is needed, use Citex RAG instead of adding MongoDB text indexes.

2. **Schema evolution:** MongoDB is schemaless, but all writes go through Pydantic validation. When adding new fields, add them to the Pydantic model with a default value so existing documents remain valid.

3. **Embedded vs. referenced:** Small, bounded sub-documents (milestones, engagement metrics, task summary) are embedded. Unbounded or cross-referenced data (people in projects, tasks in projects) use ID references.

4. **TTL considerations:** None of the current collections use TTL indexes. If storage becomes a concern, `messages` is the first candidate for TTL-based expiry (e.g., archive messages older than 6 months). `conversation_facts` should never be TTL-expired.

5. **Aggregation pipelines:** The `dashboard_widgets` collection stores `DataQuery` objects that are resolved into MongoDB aggregation pipelines at render time. The pipeline builder is documented in [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md).

6. **Citex integration:** The `documents` collection tracks Citex ingestion status. The actual RAG queries go through the Citex API, not MongoDB. See [Citex Integration](./05-CITEX-INTEGRATION.md) for details.

7. **Memory system:** The `conversation_turns`, `conversation_facts`, `session_summaries`, `compacted_summaries`, and `project_streams` collections form the memory system. The compaction pipeline and context assembly logic are documented in [Memory System](./04-MEMORY-SYSTEM.md).
