"""
OpenRouter HTTP adapter for AI generation.

Calls the OpenRouter API (OpenAI-compatible chat completions endpoint)
using httpx async client.  Supports both streaming and non-streaming modes.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator

import httpx

from app.config import get_settings

from .adapter import AIAdapter, AIRequest, AIResponse

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
COMPLETIONS_ENDPOINT = f"{OPENROUTER_BASE_URL}/chat/completions"
MODELS_ENDPOINT = f"{OPENROUTER_BASE_URL}/models"


class OpenRouterAdapter(AIAdapter):
    """AI adapter that calls the OpenRouter chat completions API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: str = settings.OPENROUTER_API_KEY
        self._model: str = settings.OPENROUTER_MODEL

        if not self._api_key:
            logger.warning(
                "OPENROUTER_API_KEY is not set; OpenRouter calls will fail."
            )

        self._client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            headers=self._build_headers(),
            http2=True,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build default headers for all OpenRouter requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://chiefops.app",
            "X-Title": "ChiefOps",
        }

    def _build_messages(self, request: AIRequest) -> list[dict[str, str]]:
        """Convert an AIRequest into OpenAI-compatible chat messages."""
        messages: list[dict[str, str]] = []

        # System message
        system_content = request.system_prompt
        if request.context:
            context_str = json.dumps(request.context, indent=2, default=str)
            system_content += (
                "\n\n<context>\n"
                f"{context_str}\n"
                "</context>"
            )
        messages.append({"role": "system", "content": system_content})

        # User message
        user_content = request.user_prompt
        if request.response_schema:
            schema_str = json.dumps(request.response_schema, indent=2)
            user_content += (
                "\n\nYou MUST respond with valid JSON matching this schema:\n"
                f"```json\n{schema_str}\n```\n"
                "Return ONLY the JSON object, no other text."
            )
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_payload(
        self,
        request: AIRequest,
        *,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Build the JSON payload for the chat completions endpoint."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": self._build_messages(request),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": stream,
        }

        if request.response_schema:
            payload["response_format"] = {"type": "json_object"}

        return payload

    async def generate(self, request: AIRequest) -> AIResponse:
        """Send a non-streaming request to OpenRouter and return the response."""
        payload = self._build_payload(request, stream=False)

        start = time.perf_counter()
        try:
            http_response = await self._client.post(
                COMPLETIONS_ENDPOINT,
                json=payload,
            )
            http_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            error_body = exc.response.text[:500]
            logger.error(
                "OpenRouter HTTP %d after %.0fms: %s",
                exc.response.status_code,
                elapsed_ms,
                error_body,
            )
            raise RuntimeError(
                f"OpenRouter API error ({exc.response.status_code}): {error_body}"
            ) from exc
        except httpx.RequestError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "OpenRouter request failed after %.0fms: %s",
                elapsed_ms,
                str(exc),
            )
            raise RuntimeError(
                f"OpenRouter connection error: {exc}"
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        data = http_response.json()

        # Extract the response content
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no choices in the response.")

        content = choices[0].get("message", {}).get("content", "")

        # Extract usage stats
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        model_used = data.get("model", self._model)

        logger.info(
            "OpenRouter call completed in %.0fms (model=%s, in=%d, out=%d tokens)",
            elapsed_ms,
            model_used,
            input_tokens,
            output_tokens,
        )

        return AIResponse(
            content=content,
            model=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            adapter="openrouter",
            latency_ms=elapsed_ms,
        )

    async def generate_structured(self, request: AIRequest) -> AIResponse:
        """Send a request and enforce JSON output format."""
        if request.response_schema is None:
            request = request.model_copy(
                update={"response_schema": {"type": "object"}}
            )

        response = await self.generate(request)

        # Validate JSON
        try:
            response.parse_json()
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "OpenRouter response is not valid JSON: %s",
                response.content[:200],
            )
            raise ValueError(
                f"OpenRouter did not return valid JSON: {exc}"
            ) from exc

        return response

    async def generate_stream(
        self, request: AIRequest
    ) -> AsyncIterator[str]:
        """Stream tokens from OpenRouter using server-sent events.

        Yields:
            Individual text chunks as they arrive from the API.
        """
        payload = self._build_payload(request, stream=True)

        try:
            async with self._client.stream(
                "POST",
                COMPLETIONS_ENDPOINT,
                json=payload,
            ) as http_response:
                http_response.raise_for_status()

                async for line in http_response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Strip "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.debug("Skipping non-JSON SSE line: %s", data_str[:100])
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    text = delta.get("content")
                    if text:
                        yield text

        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:500]
            logger.error(
                "OpenRouter streaming HTTP %d: %s",
                exc.response.status_code,
                error_body,
            )
            raise RuntimeError(
                f"OpenRouter streaming error ({exc.response.status_code}): {error_body}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("OpenRouter streaming connection error: %s", str(exc))
            raise RuntimeError(
                f"OpenRouter streaming connection error: {exc}"
            ) from exc

    async def health_check(self) -> bool:
        """Check OpenRouter connectivity by listing available models."""
        if not self._api_key:
            logger.warning("Cannot health-check OpenRouter: no API key configured.")
            return False

        try:
            response = await self._client.get(
                MODELS_ENDPOINT,
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                logger.info(
                    "OpenRouter health check passed (%d models available)",
                    model_count,
                )
                return True
            logger.warning(
                "OpenRouter health check returned HTTP %d",
                response.status_code,
            )
            return False
        except Exception:
            logger.exception("OpenRouter health check failed")
            return False

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()
