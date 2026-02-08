"""
Pydantic request/response models for the Citex RAG service.

These models define the wire format used by CitexClient when communicating
with the Citex REST API for document ingestion, querying, and deletion.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CitexIngestRequest(BaseModel):
    """Payload sent to Citex when ingesting a new document."""

    project_id: str = Field(
        ...,
        min_length=1,
        description="Project this document belongs to.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Full text content of the document.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata attached to the document (source, author, etc.).",
    )
    filename: str = Field(
        ...,
        min_length=1,
        description="Original filename of the ingested document.",
    )


class CitexQueryRequest(BaseModel):
    """Payload sent to Citex when performing a semantic query."""

    project_id: str = Field(
        ...,
        min_length=1,
        description="Project scope for the query.",
    )
    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language query text.",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata filters to narrow the search.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of chunks to return.",
    )


class CitexChunk(BaseModel):
    """A single chunk returned from a Citex semantic search."""

    chunk_id: str = Field(
        ...,
        description="Unique identifier of the chunk.",
    )
    content: str = Field(
        ...,
        description="Text content of the chunk.",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score (0.0 to 1.0).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata associated with this chunk.",
    )
    source: str = Field(
        default="",
        description="Source filename or identifier.",
    )


class CitexQueryResponse(BaseModel):
    """Response from a Citex semantic query."""

    chunks: list[CitexChunk] = Field(
        default_factory=list,
        description="Matching chunks ordered by relevance score (descending).",
    )
    total: int = Field(
        default=0,
        ge=0,
        description="Total number of matching chunks (may exceed returned count).",
    )
