"""
Conversation endpoints.

Provides the core COO-to-AI chat interface. Messages are processed by the
conversation service which handles context retrieval, AI generation, and
memory persistence. Responses are streamed via Server-Sent Events (SSE).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["conversation"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MessageRequest(BaseModel):
    """Request body for sending a message."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user message content.",
    )
    project_id: str | None = Field(
        default=None,
        description="Optional project context for the conversation.",
    )


class MessageResponse(BaseModel):
    """A single message in the conversation history."""

    message_id: str = Field(..., description="Unique message identifier.")
    role: str = Field(..., description="Message author role: 'user' or 'assistant'.")
    content: str = Field(..., description="Message content.")
    project_id: str | None = Field(default=None, description="Associated project ID.")
    created_at: datetime = Field(..., description="Message creation timestamp.")
    metadata: dict | None = Field(
        default=None, description="Additional metadata (sources, widget refs, etc.)."
    )


class ConversationHistoryResponse(BaseModel):
    """Paginated conversation history."""

    messages: list[MessageResponse] = Field(default_factory=list, description="List of messages.")
    total: int = Field(default=0, description="Total number of messages matching the filter.")
    skip: int = Field(default=0, description="Number of records skipped.")
    limit: int = Field(default=50, description="Page size.")


class ClearHistoryResponse(BaseModel):
    """Response after clearing conversation history."""

    deleted_count: int = Field(..., description="Number of messages deleted.")
    message: str = Field(..., description="Human-readable status message.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_collection(db: AsyncIOMotorDatabase):  # type: ignore[type-arg]
    """Return the conversation_messages collection."""
    return db["conversation_messages"]


async def _stream_response(content: str, message_id: str, project_id: str | None):
    """Generate SSE events from the AI response.

    Falls back to a single-chunk stream if the conversation service
    is not yet available.
    """
    # SSE format: data: {json}\n\n
    # Stream the response in chunks to simulate real-time generation
    chunk_size = 20
    accumulated = ""

    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        accumulated += chunk
        event_data = {
            "type": "chunk",
            "message_id": message_id,
            "content": chunk,
        }
        yield f"data: {json.dumps(event_data)}\n\n"

    # Final event with complete message
    done_data = {
        "type": "done",
        "message_id": message_id,
        "content": accumulated,
        "project_id": project_id,
    }
    yield f"data: {json.dumps(done_data)}\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/message",
    summary="Send a message",
    description="Send a message to the AI assistant. Returns a Server-Sent Events "
    "stream with the response generated in real time.",
)
async def send_message(
    body: MessageRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> StreamingResponse:
    collection = _get_collection(db)
    now = utc_now()

    # Persist the user message
    user_message_id = generate_uuid()
    user_doc = {
        "message_id": user_message_id,
        "role": "user",
        "content": body.content,
        "project_id": body.project_id,
        "created_at": now,
        "metadata": None,
    }
    await collection.insert_one(user_doc)

    # Generate AI response via conversation service
    assistant_message_id = generate_uuid()
    response_content: str
    response_metadata: dict | None = None

    try:
        from app.services.conversation.service import ConversationService

        service = ConversationService(db)
        result = await service.generate_response(
            message=body.content,
            project_id=body.project_id,
        )
        response_content = result.get(
            "content", "I understand your request. Let me look into that."
        )
        response_metadata = result.get("metadata")
    except ImportError:
        logger.warning("Conversation service not yet implemented; returning placeholder response.")
        response_content = (
            "I received your message. The conversation service is being initialized. "
            "Please check back shortly."
        )
    except Exception as exc:
        logger.error("Conversation service error", exc_info=exc)
        response_content = "I encountered an issue processing your request. Please try again."
        response_metadata = {"error": str(exc)}

    # Persist the assistant message
    assistant_doc = {
        "message_id": assistant_message_id,
        "role": "assistant",
        "content": response_content,
        "project_id": body.project_id,
        "created_at": utc_now(),
        "metadata": response_metadata,
    }
    await collection.insert_one(assistant_doc)

    return StreamingResponse(
        _stream_response(response_content, assistant_message_id, body.project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/history",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Retrieve paginated conversation history, optionally filtered by project.",
)
async def get_history(
    skip: int = Query(default=0, ge=0, description="Number of messages to skip."),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum messages to return."),
    project_id: str | None = Query(default=None, description="Filter by project ID."),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ConversationHistoryResponse:
    collection = _get_collection(db)

    query: dict = {}
    if project_id is not None:
        query["project_id"] = project_id

    total = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    messages = [MessageResponse(**doc) for doc in docs]

    return ConversationHistoryResponse(
        messages=messages,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/history",
    response_model=ClearHistoryResponse,
    summary="Clear conversation history",
    description="Delete conversation history. Hard facts extracted from conversations "
    "are preserved in the memory store.",
)
async def clear_history(
    project_id: str | None = Query(
        default=None,
        description="If provided, only clear history for this project. Otherwise clear all.",
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ClearHistoryResponse:
    collection = _get_collection(db)

    query: dict = {}
    if project_id is not None:
        query["project_id"] = project_id

    result = await collection.delete_many(query)

    scope = f"project '{project_id}'" if project_id else "all projects"
    return ClearHistoryResponse(
        deleted_count=result.deleted_count,
        message=f"Cleared {result.deleted_count} message(s) for {scope}. Hard facts preserved.",
    )
