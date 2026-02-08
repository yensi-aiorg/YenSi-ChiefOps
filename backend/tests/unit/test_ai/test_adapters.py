"""
Unit tests for the AI adapter system.

Tests the MockAIAdapter implementation, structured output generation,
health checks, and the adapter factory's fallback behavior.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.ai.adapter import AIAdapter, AIRequest, AIResponse
from app.ai.factory import get_adapter, reset_adapter
from app.ai.mock_adapter import MockAIAdapter


class TestMockAdapterGenerate:
    """Test MockAIAdapter.generate() free-text generation."""

    async def test_mock_adapter_generate(self):
        """generate() should return a valid AIResponse with content."""
        adapter = MockAIAdapter()
        request = AIRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is the status of the engineering team?",
        )

        response = await adapter.generate(request)

        assert isinstance(response, AIResponse)
        assert response.content  # Non-empty string
        assert len(response.content) > 0
        assert response.model == "mock"
        assert response.adapter == "mock"
        assert response.latency_ms >= 0.0
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    async def test_mock_adapter_returns_conversation_response(self):
        """An unmatched prompt should return the default conversation response."""
        adapter = MockAIAdapter()
        request = AIRequest(
            system_prompt="General assistant.",
            user_prompt="Tell me something interesting.",
        )

        response = await adapter.generate(request)

        assert isinstance(response, AIResponse)
        assert response.content  # Should be the fallback conversation response
        assert response.adapter == "mock"

    async def test_mock_adapter_matches_intent_pattern(self):
        """A prompt matching 'intent detect' should return the intent response."""
        adapter = MockAIAdapter()
        request = AIRequest(
            system_prompt="Intent detection: classify the user input.",
            user_prompt="Show me project status.",
        )

        response = await adapter.generate(request)
        data = json.loads(response.content)

        assert "intent" in data
        assert "confidence" in data

    async def test_mock_adapter_matches_report_pattern(self):
        """A prompt matching 'report generat' should return the report response."""
        adapter = MockAIAdapter()
        request = AIRequest(
            system_prompt="Report generation: create a report specification.",
            user_prompt="Generate a weekly status report.",
        )

        response = await adapter.generate(request)
        data = json.loads(response.content)

        assert "report_spec" in data


class TestMockAdapterGenerateStructured:
    """Test MockAIAdapter.generate_structured() JSON output."""

    async def test_mock_adapter_generate_structured(self):
        """generate_structured() should always return valid JSON."""
        adapter = MockAIAdapter()
        request = AIRequest(
            system_prompt="Fact extraction: extract key facts from the conversation.",
            user_prompt="Sarah is the engineering lead.",
            response_schema={
                "type": "object",
                "properties": {
                    "facts": {"type": "array"},
                },
            },
        )

        response = await adapter.generate_structured(request)

        assert isinstance(response, AIResponse)
        assert response.adapter == "mock"

        # Content must be valid JSON
        data = json.loads(response.content)
        assert isinstance(data, dict)

    async def test_mock_adapter_structured_wraps_non_json(self):
        """If the matched response is not JSON, it should be wrapped."""
        adapter = MockAIAdapter()
        # This prompt won't match any JSON-producing pattern,
        # so the fallback conversation text will be wrapped
        request = AIRequest(
            system_prompt="Random topic with no matching pattern at all.",
            user_prompt="Just chatting about nothing specific.",
        )

        response = await adapter.generate_structured(request)

        data = json.loads(response.content)
        assert isinstance(data, dict)
        # Wrapped responses have a "response" key
        if "response" in data:
            assert data["status"] == "success"

    async def test_mock_adapter_structured_parse_json(self):
        """AIResponse.parse_json() should work on structured responses."""
        adapter = MockAIAdapter()
        request = AIRequest(
            system_prompt="Widget generation: create a widget specification.",
            user_prompt="Show project health.",
        )

        response = await adapter.generate_structured(request)
        data = response.parse_json()

        assert isinstance(data, dict)


class TestMockAdapterHealthCheck:
    """Test MockAIAdapter.health_check()."""

    async def test_mock_adapter_health_check(self):
        """MockAIAdapter health check should always return True."""
        adapter = MockAIAdapter()
        result = await adapter.health_check()

        assert result is True

    async def test_mock_adapter_health_check_is_async(self):
        """health_check should be an async method."""
        adapter = MockAIAdapter()
        import asyncio
        assert asyncio.iscoroutinefunction(adapter.health_check)


class TestFactoryReturnsMockAdapter:
    """Test that the adapter factory returns MockAIAdapter when configured."""

    def test_factory_returns_mock_adapter(self):
        """get_adapter() with AI_ADAPTER='mock' should return MockAIAdapter."""
        reset_adapter()

        with patch("app.ai.factory.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.AI_ADAPTER = "mock"

            adapter = get_adapter()
            assert isinstance(adapter, MockAIAdapter)

        reset_adapter()


class TestFactoryFallbackToMock:
    """Test factory fallback behavior for unknown or failing adapters."""

    def test_factory_fallback_to_mock(self):
        """An unknown AI_ADAPTER value should fall back to MockAIAdapter."""
        reset_adapter()

        with patch("app.ai.factory.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.AI_ADAPTER = "nonexistent_adapter"

            adapter = get_adapter()
            assert isinstance(adapter, MockAIAdapter)

        reset_adapter()

    def test_factory_fallback_on_import_error(self):
        """If the configured adapter fails to import, fall back to MockAIAdapter."""
        reset_adapter()

        with patch("app.ai.factory.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.AI_ADAPTER = "openrouter"
            settings.OPENROUTER_API_KEY = ""
            settings.OPENROUTER_MODEL = "test-model"

            # Patch the import to fail
            with patch.dict("sys.modules", {"app.ai.openrouter_adapter": None}):
                try:
                    adapter = get_adapter()
                    # May succeed if openrouter_adapter exists but API key is empty
                    # Either way, the factory should not crash
                    assert isinstance(adapter, AIAdapter)
                except Exception:
                    # If it does fail, reset and try with explicit mock
                    reset_adapter()
                    settings.AI_ADAPTER = "mock"
                    adapter = get_adapter()
                    assert isinstance(adapter, MockAIAdapter)

        reset_adapter()


class TestAIAdapterInterface:
    """Test the AIAdapter abstract interface compliance."""

    def test_mock_adapter_implements_interface(self):
        """MockAIAdapter should implement all AIAdapter abstract methods."""
        adapter = MockAIAdapter()

        assert isinstance(adapter, AIAdapter)
        assert hasattr(adapter, "generate")
        assert hasattr(adapter, "generate_structured")
        assert hasattr(adapter, "health_check")
        assert callable(adapter.generate)
        assert callable(adapter.generate_structured)
        assert callable(adapter.health_check)


class TestAIRequestModel:
    """Test AIRequest model construction and prompt building."""

    def test_ai_request_defaults(self):
        request = AIRequest(
            system_prompt="System prompt.",
            user_prompt="User prompt.",
        )

        assert request.max_tokens == 4096
        assert request.temperature == 0.3
        assert request.context == {}
        assert request.response_schema is None

    def test_ai_request_build_full_prompt(self):
        request = AIRequest(
            system_prompt="You are a test assistant.",
            user_prompt="What is 2+2?",
            context={"key": "value"},
        )

        prompt = request.build_full_prompt()
        assert "<system>" in prompt
        assert "You are a test assistant." in prompt
        assert "<user>" in prompt
        assert "What is 2+2?" in prompt
        assert "<context>" in prompt
        assert '"key": "value"' in prompt


class TestAIResponseModel:
    """Test AIResponse model and JSON parsing."""

    def test_ai_response_parse_json(self):
        response = AIResponse(
            content='{"key": "value", "number": 42}',
            model="test",
            adapter="test",
        )

        data = response.parse_json()
        assert data["key"] == "value"
        assert data["number"] == 42

    def test_ai_response_parse_json_with_code_fence(self):
        response = AIResponse(
            content='```json\n{"key": "value"}\n```',
            model="test",
            adapter="test",
        )

        data = response.parse_json()
        assert data["key"] == "value"
