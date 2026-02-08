"""
SSE streaming handler for conversation responses.

Wraps AI adapter output into Server-Sent Events (SSE) format using
the sse-starlette library. Handles chunked streaming, error events,
and graceful termination.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)


async def stream_response(
    response_generator: AsyncGenerator[str, None],
    request: Request | None = None,
) -> EventSourceResponse:
    """Wrap an async generator into an SSE EventSourceResponse.

    The generator yields text chunks which are sent as SSE ``message``
    events. A final ``done`` event is sent when the generator exhausts.
    Errors are sent as ``error`` events.

    Args:
        response_generator: Async generator yielding text chunks.
        request: Optional Starlette request for client disconnect detection.

    Returns:
        An ``EventSourceResponse`` ready to be returned from a FastAPI endpoint.
    """

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        try:
            async for chunk in response_generator:
                if request is not None and await request.is_disconnected():
                    logger.debug("Client disconnected, stopping stream")
                    break

                yield {
                    "event": "message",
                    "data": json.dumps({"type": "chunk", "content": chunk}),
                }

            # Send completion event
            yield {
                "event": "message",
                "data": json.dumps({"type": "done", "content": ""}),
            }

        except Exception as exc:
            logger.exception("Error during response streaming")
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "content": f"Stream error: {exc}",
                }),
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def collect_stream(
    response_generator: AsyncGenerator[str, None],
) -> str:
    """Collect all chunks from a streaming response into a single string.

    Useful for non-streaming endpoints that still use the streaming
    AI adapter internally.

    Args:
        response_generator: Async generator yielding text chunks.

    Returns:
        Concatenated text from all chunks.
    """
    parts: list[str] = []
    async for chunk in response_generator:
        parts.append(chunk)
    return "".join(parts)


def format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event string.

    Args:
        event_type: The SSE event name.
        data: The event data payload.

    Returns:
        Formatted SSE string with event and data fields.
    """
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"
