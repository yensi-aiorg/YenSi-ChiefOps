"""
Integration tests for the health check API endpoint.

Tests the /api/v1/health endpoint structure and response format
using the test FastAPI application with mocked dependencies.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealthEndpointReturnsOk:
    """Test that the health endpoint returns a successful response."""

    async def test_health_endpoint_returns_ok(self, async_client: AsyncClient):
        """GET /api/v1/health should return 200 with status field."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestHealthEndpointStructure:
    """Test the structure of the health endpoint response."""

    async def test_health_endpoint_structure(self, async_client: AsyncClient):
        """Health response should include mongo, redis, and citex fields."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "status" in data
        assert "mongo" in data
        assert "redis" in data
        assert "citex" in data

        # Status should be a string
        assert isinstance(data["status"], str)
        assert data["status"] in ("ok", "degraded")

        # Connectivity booleans
        assert isinstance(data["mongo"], bool)
        assert isinstance(data["redis"], bool)
        assert isinstance(data["citex"], bool)
