"""
Abstract base class and data models for AI adapters.

All AI backends (CLI, OpenRouter, Mock) implement the AIAdapter interface
so the rest of ChiefOps can swap providers without changing calling code.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AIRequest(BaseModel):
    """Payload sent to any AI adapter."""

    system_prompt: str = Field(
        ...,
        description="System-level instruction that sets the AI's role and constraints.",
    )
    user_prompt: str = Field(
        ...,
        description="The end-user (COO) prompt or question.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured context data injected into the prompt "
            "(e.g. project records, people records, prior conversation)."
        ),
    )
    response_schema: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional JSON Schema that the AI response must conform to. "
            "When provided, the adapter should attempt to return valid JSON."
        ),
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128_000,
        description="Maximum number of tokens in the response.",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature. Lower values produce more deterministic output.",
    )

    def build_full_prompt(self) -> str:
        """Combine system prompt, context, and user prompt into a single string.

        Useful for CLI adapters that accept a single prompt argument rather
        than structured message arrays.
        """
        parts: list[str] = []

        parts.append(f"<system>\n{self.system_prompt}\n</system>")

        if self.context:
            context_str = json.dumps(self.context, indent=2, default=str)
            parts.append(f"<context>\n{context_str}\n</context>")

        if self.response_schema:
            schema_str = json.dumps(self.response_schema, indent=2)
            parts.append(
                "<output_format>\n"
                "You MUST respond with valid JSON matching this schema:\n"
                f"{schema_str}\n"
                "</output_format>"
            )

        parts.append(f"<user>\n{self.user_prompt}\n</user>")

        return "\n\n".join(parts)


class AIResponse(BaseModel):
    """Standardised response returned by every AI adapter."""

    content: str = Field(
        ...,
        description="The raw text content of the AI response.",
    )
    model: str = Field(
        default="unknown",
        description="Identifier of the model that produced this response.",
    )
    input_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of input tokens consumed.",
    )
    output_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of output tokens generated.",
    )
    adapter: str = Field(
        default="unknown",
        description="Name of the adapter that handled the request (e.g. 'cli', 'openrouter', 'mock').",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Wall-clock time in milliseconds for the AI call.",
    )

    def parse_json(self) -> dict[str, Any]:
        """Attempt to parse the content as JSON.

        Handles cases where the model wraps its response in markdown
        code fences (```json ... ```).
        """
        text = self.content.strip()

        # Strip markdown code fence if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            elif lines[0].strip().startswith("```"):
                lines = lines[1:]
            text = "\n".join(lines).strip()

        return json.loads(text)


class AIAdapter(ABC):
    """Abstract interface that all AI backends must implement."""

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Send a prompt to the AI and return a free-text response.

        Args:
            request: The AI request containing prompts, context, and parameters.

        Returns:
            An AIResponse with the model's text output.

        Raises:
            RuntimeError: If the AI backend is unreachable or returns an error.
        """

    @abstractmethod
    async def generate_structured(self, request: AIRequest) -> AIResponse:
        """Send a prompt and enforce structured (JSON) output.

        The request.response_schema field should be populated so the adapter
        can instruct the model to return valid JSON.  The returned
        AIResponse.content will contain a JSON string.

        Args:
            request: The AI request with a response_schema defined.

        Returns:
            An AIResponse whose content is parseable JSON.

        Raises:
            RuntimeError: If the AI backend is unreachable or returns an error.
            ValueError: If the response cannot be parsed as valid JSON.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify that the AI backend is reachable and operational.

        Returns:
            True if the backend is healthy, False otherwise.
        """
