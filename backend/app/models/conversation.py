"""
Conversation and memory models for the ChiefOps memory system.

Covers conversation turns, memory streams, hard facts, source tracking,
and compacted summaries. These models power the multi-tier memory system
that gives ChiefOps persistent context across conversations.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.base import MongoBaseModel, generate_uuid, utc_now

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StreamType(str, Enum):
    """Type of conversation stream."""

    PROJECT = "project"
    GLOBAL = "global"


class TurnRole(str, Enum):
    """Role of the participant in a conversation turn."""

    USER = "user"
    ASSISTANT = "assistant"


class SourceType(str, Enum):
    """Type of data source referenced by the assistant."""

    SLACK = "slack"
    JIRA = "jira"
    DRIVE = "drive"
    MEMORY = "memory"


class FactCategory(str, Enum):
    """
    Category of a hard fact extracted from conversation.

    - role_correction: COO corrected an AI-assigned role.
    - assignment: COO confirmed or changed a task assignment.
    - deadline: COO set or modified a deadline.
    - decision: COO made an operational decision.
    - organizational: Fact about team structure or reporting lines.
    - project_fact: Fact about a project's scope, constraints, or context.
    - preference: COO stated a personal preference (report format, etc.).
    - blocker: COO flagged a blocker or dependency.
    """

    ROLE_CORRECTION = "role_correction"
    ASSIGNMENT = "assignment"
    DEADLINE = "deadline"
    DECISION = "decision"
    ORGANIZATIONAL = "organizational"
    PROJECT_FACT = "project_fact"
    PREFERENCE = "preference"
    BLOCKER = "blocker"


# ---------------------------------------------------------------------------
# Embedded sub-documents
# ---------------------------------------------------------------------------


class SourceUsed(BaseModel):
    """Records a data source consulted when generating an assistant response."""

    source_type: SourceType = Field(
        ...,
        description="Type of source that was consulted.",
    )
    item_count: int = Field(
        default=0,
        ge=0,
        description="Number of items retrieved from this source.",
    )
    date_range: str | None = Field(
        default=None,
        description="Human-readable date range of the data consulted (e.g. '2024-01-01 to 2024-03-15').",
    )


# ---------------------------------------------------------------------------
# Primary model: ConversationTurn
# ---------------------------------------------------------------------------


class ConversationTurn(MongoBaseModel):
    """
    A single turn in a conversation between the COO and ChiefOps.
    Every user message and every assistant response is stored as a
    separate document. Turns are the raw material for the memory
    system -- facts are extracted from them, and session summaries
    are generated when sessions end.

    MongoDB collection: ``conversation_turns``
    """

    turn_id: str = Field(
        default_factory=generate_uuid,
        description="Unique turn identifier (UUID v4).",
    )
    project_id: str | None = Field(
        default=None,
        description="Project this turn relates to (None for global stream).",
    )
    stream_type: StreamType = Field(
        default=StreamType.GLOBAL,
        description="Whether this turn belongs to a project stream or the global stream.",
    )
    role: TurnRole = Field(
        ...,
        description="Who produced this turn (user = COO, assistant = ChiefOps).",
    )
    content: str = Field(
        ...,
        description="Text content of this turn.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the turn occurred.",
    )
    turn_number: int = Field(
        default=0,
        ge=0,
        description="Sequential turn number within the stream/session.",
    )
    sources_used: list[SourceUsed] = Field(
        default_factory=list,
        description="Data sources consulted when producing this response.",
    )


# ---------------------------------------------------------------------------
# Primary model: MemoryStream
# ---------------------------------------------------------------------------


class MemoryStream(MongoBaseModel):
    """
    Per-project (or global) conversational stream metadata. Every project
    gets its own memory stream so that project-specific context, facts,
    and summaries are isolated. The global stream (project_id=None) handles
    cross-project conversations and general preferences.

    MongoDB collection: ``memory_streams``
    """

    stream_id: str = Field(
        default_factory=generate_uuid,
        description="Unique stream identifier (UUID v4).",
    )
    project_id: str | None = Field(
        default=None,
        description="Linked project (None for the global stream).",
    )
    stream_type: StreamType = Field(
        default=StreamType.GLOBAL,
        description="Type of this memory stream.",
    )
    hard_facts: list[str] = Field(
        default_factory=list,
        description="List of fact_id values belonging to this stream.",
    )
    summary: str = Field(
        default="",
        description="Current rolling summary text for context assembly.",
    )
    recent_turns: list[str] = Field(
        default_factory=list,
        description="List of recent turn_id values kept in working memory.",
    )
    last_compacted_at: datetime | None = Field(
        default=None,
        description="When the stream's summary was last compacted.",
    )


# ---------------------------------------------------------------------------
# Primary model: HardFact
# ---------------------------------------------------------------------------


class HardFact(MongoBaseModel):
    """
    A hard fact extracted from a conversation turn. Facts are NEVER
    compacted or deleted -- they are the permanent record of what the
    COO has communicated to ChiefOps.

    When a new fact supersedes an old one (e.g. a role correction),
    the old fact's ``active`` flag is set to False and the new fact's
    ``supersedes`` field references the old fact_id. Queries always
    filter on active=True to get the current state.

    MongoDB collection: ``hard_facts``
    """

    fact_id: str = Field(
        default_factory=generate_uuid,
        description="Unique fact identifier (UUID v4).",
    )
    project_id: str | None = Field(
        default=None,
        description="Linked project (None for global facts).",
    )
    stream_type: StreamType = Field(
        default=StreamType.GLOBAL,
        description="Which stream type this fact belongs to.",
    )
    fact_text: str = Field(
        ...,
        min_length=1,
        description="The fact statement in natural language.",
    )
    category: FactCategory = Field(
        ...,
        description="Classification of this fact.",
    )
    source: dict = Field(
        default_factory=dict,
        description="Provenance of the fact (e.g. {turn_id: '...', timestamp: '...'}).",
    )
    extracted_by: str = Field(
        default="system",
        description="Identifier of the extraction method or model that produced this fact.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of the extraction (0.0 to 1.0).",
    )
    supersedes: str | None = Field(
        default=None,
        description="fact_id of the fact this one replaces (if any).",
    )
    active: bool = Field(
        default=True,
        description="False if this fact has been superseded by a newer fact.",
    )


# ---------------------------------------------------------------------------
# Primary model: CompactedSummary
# ---------------------------------------------------------------------------


class CompactedSummary(MongoBaseModel):
    """
    A progressively compacted summary for long-term memory. The compaction
    pipeline rolls up recent conversation turns into periodic summaries.
    Each level reduces token count while preserving operationally relevant
    context. Facts are never lost in compaction -- only narrative summaries
    are compressed.

    MongoDB collection: ``compacted_summaries``
    """

    summary_id: str = Field(
        default_factory=generate_uuid,
        description="Unique compacted summary identifier (UUID v4).",
    )
    project_id: str | None = Field(
        default=None,
        description="Linked project (None for global stream summaries).",
    )
    stream_type: StreamType = Field(
        default=StreamType.GLOBAL,
        description="Which stream type this summary belongs to.",
    )
    content: str = Field(
        ...,
        description="The compacted summary text.",
    )
    turn_range_start: int = Field(
        ...,
        ge=0,
        description="First turn number covered by this summary.",
    )
    turn_range_end: int = Field(
        ...,
        ge=0,
        description="Last turn number covered by this summary.",
    )
    compacted_at: datetime = Field(
        default_factory=utc_now,
        description="When this compacted summary was generated.",
    )
