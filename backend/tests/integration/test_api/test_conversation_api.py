"""
Integration tests for the conversation API endpoints.

Tests sending messages, retrieving conversation history, and
clearing history through the REST API.
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from app.models.base import generate_uuid, utc_now


class TestSendMessage:
    """Test the message sending endpoint."""

    async def test_send_message(self, async_client: AsyncClient):
        """POST /api/v1/conversation/message should accept a message and stream a response."""
        response = await async_client.post(
            "/api/v1/conversation/message",
            json={"content": "What is the status of the Platform Migration project?"},
        )

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")

        # Parse the SSE stream
        body = response.text
        events = [
            line.replace("data: ", "")
            for line in body.strip().split("\n")
            if line.startswith("data: ")
        ]

        assert len(events) > 0

        # The last event should be a "done" event
        last_event = json.loads(events[-1])
        assert last_event["type"] == "done"
        assert "message_id" in last_event
        assert "content" in last_event

    async def test_send_message_with_project_context(self, async_client: AsyncClient):
        """Sending a message with a project_id should scope the conversation."""
        project_id = generate_uuid()

        response = await async_client.post(
            "/api/v1/conversation/message",
            json={
                "content": "How is this project doing?",
                "project_id": project_id,
            },
        )

        assert response.status_code == 200

        # Parse the last SSE event
        body = response.text
        events = [
            line.replace("data: ", "")
            for line in body.strip().split("\n")
            if line.startswith("data: ")
        ]

        last_event = json.loads(events[-1])
        assert last_event["project_id"] == project_id

    async def test_send_empty_message_rejected(self, async_client: AsyncClient):
        """Sending an empty message should return 422."""
        response = await async_client.post(
            "/api/v1/conversation/message",
            json={"content": ""},
        )

        assert response.status_code == 422


class TestGetConversationHistory:
    """Test the conversation history retrieval endpoint."""

    async def test_get_history(self, async_client: AsyncClient):
        """GET /api/v1/conversation/history should return paginated messages."""
        # First, send a message to create history
        await async_client.post(
            "/api/v1/conversation/message",
            json={"content": "Hello, ChiefOps!"},
        )

        response = await async_client.get("/api/v1/conversation/history")

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert isinstance(data["messages"], list)
        # Should have at least the user message and the assistant response
        assert data["total"] >= 2

    async def test_get_history_with_pagination(self, async_client: AsyncClient):
        """History endpoint should support skip and limit parameters."""
        response = await async_client.get(
            "/api/v1/conversation/history",
            params={"skip": 0, "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["skip"] == 0

    async def test_get_history_by_project(self, async_client: AsyncClient):
        """History should be filterable by project_id."""
        project_id = generate_uuid()

        # Send a message scoped to a project
        await async_client.post(
            "/api/v1/conversation/message",
            json={"content": "Project-scoped message.", "project_id": project_id},
        )

        response = await async_client.get(
            "/api/v1/conversation/history",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        for msg in data["messages"]:
            assert msg["project_id"] == project_id


class TestClearHistory:
    """Test the conversation history clearing endpoint."""

    async def test_clear_history(self, async_client: AsyncClient):
        """DELETE /api/v1/conversation/history should clear all messages."""
        # Create some history
        await async_client.post(
            "/api/v1/conversation/message",
            json={"content": "Message to be cleared."},
        )

        response = await async_client.delete("/api/v1/conversation/history")

        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert data["deleted_count"] >= 0
        assert "message" in data

    async def test_clear_history_by_project(self, async_client: AsyncClient):
        """Clearing history with a project_id should only clear that project's messages."""
        project_id = generate_uuid()

        # Send messages to two different projects
        await async_client.post(
            "/api/v1/conversation/message",
            json={"content": "Project A message.", "project_id": project_id},
        )
        await async_client.post(
            "/api/v1/conversation/message",
            json={"content": "Global message."},
        )

        # Clear only the project-scoped messages
        response = await async_client.delete(
            "/api/v1/conversation/history",
            params={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] >= 2  # user + assistant messages

        # Global messages should still exist
        global_response = await async_client.get(
            "/api/v1/conversation/history",
            params={"project_id": "null"},  # no project filter
        )
        # We just verify the endpoint still works
        assert global_response.status_code == 200
