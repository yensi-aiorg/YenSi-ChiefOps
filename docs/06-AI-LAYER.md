# AI Layer: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | **AI Layer** | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Overview

The AI layer is the core processing engine of ChiefOps. It is not simply a question-answering chatbot — it is the intelligence backbone that drives every major feature in the system. The AI layer powers:

- **People identification and role detection** from unstructured Slack messages, Jira task descriptions, and Google Drive documents
- **Project analysis and status assessment** — synthesizing information across all data sources to determine project health, completion percentage, and risks
- **Technical feasibility checking and gap detection** — backward planning from deadlines, missing prerequisite identification, capacity analysis
- **Briefing and report generation** — creating structured report specifications that the report engine renders into professional PDFs
- **Chart specification generation** — producing ECharts-compatible JSON from data and natural language requests
- **NL intent detection** — classifying user input as corrections, queries, or commands (add widget, generate report, modify dashboard)
- **Conversation summarization and fact extraction** — compacting conversation history into progressive summaries and extracting hard facts for the memory system
- **Slack message summarization** — distilling hundreds of Slack messages into concise project-level summaries during ingestion

The AI layer is accessed exclusively through the **Adapter Pattern**, as mandated by `technical.md`. No business logic in ChiefOps directly calls any AI provider. All AI operations go through an abstract interface with concrete implementations for development (CLI subprocess) and production (Open Router API).

---

## 2. Adapter Pattern Implementation

The Adapter Pattern is the foundation of ChiefOps's AI integration. It ensures:

1. **No vendor lock-in** — switch between Claude, GPT, Gemini, or any model available on Open Router
2. **Development flexibility** — use CLI tools locally (free tier, no API key management) and Open Router in production
3. **Testability** — mock the adapter interface for unit tests without touching any AI provider
4. **Configuration-driven selection** — a single environment variable switches the entire AI backend

### 2.1 Abstract Base Class

```python
# app/ai/adapter.py

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AIRequest(BaseModel):
    """Standard request payload for all AI operations."""
    system_prompt: str = Field(..., description="System-level instructions for the AI")
    user_prompt: str = Field(..., description="The user's query or task description")
    context: str = Field(default="", description="Additional context: facts, summaries, chunks")
    response_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON schema for structured output. If provided, response must conform."
    )
    max_tokens: int = Field(default=4096, description="Maximum tokens in the response")
    temperature: float = Field(default=0.3, description="Sampling temperature (0.0-1.0)")


class AIResponse(BaseModel):
    """Standard response from any AI adapter."""
    content: str = Field(..., description="Raw text response from the model")
    model: str = Field(..., description="Model identifier that produced the response")
    input_tokens: int = Field(default=0, description="Number of input tokens consumed")
    output_tokens: int = Field(default=0, description="Number of output tokens produced")
    adapter: str = Field(..., description="Adapter type used: 'cli' or 'openrouter'")
    latency_ms: float = Field(default=0.0, description="Round-trip latency in milliseconds")


class AIAdapter(ABC):
    """
    Abstract base class for all AI adapters.

    Every AI integration in ChiefOps goes through this interface.
    Business logic never imports or references a specific provider.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> AIResponse:
        """
        Generate a free-text response from the AI model.

        Used for: general queries, briefings, conversational responses,
        Slack summarization, conversation summarization.
        """
        ...

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        response_schema: dict[str, Any] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AIResponse:
        """
        Generate a structured JSON response from the AI model.

        Used for: chart specs, report specs, people analysis, intent detection,
        fact extraction. The response content is guaranteed to be valid JSON
        conforming to response_schema (validated post-generation).
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify that the adapter can reach its underlying AI provider."""
        ...
```

### 2.2 CLIAdapter (Development / Testing)

The CLI adapter invokes command-line AI tools (Claude CLI, Codex CLI, Gemini CLI) as Python subprocesses. This is the primary development mode — developers use their authenticated CLI tools directly, with no API key management or billing setup required.

```python
# app/ai/cli_adapter.py

import asyncio
import json
import time
from typing import Any

from app.ai.adapter import AIAdapter, AIResponse
from app.core.config import settings


class CLIAdapter(AIAdapter):
    """
    AI adapter that invokes CLI tools as Python subprocesses.

    Supports: claude, codex, gemini CLIs.
    Configured via AI_CLI_TOOL environment variable.
    """

    # Map CLI tool names to their executable commands and argument formats
    CLI_CONFIGS = {
        "claude": {
            "command": "claude",
            "args_builder": "_build_claude_args",
        },
        "codex": {
            "command": "codex",
            "args_builder": "_build_codex_args",
        },
        "gemini": {
            "command": "gemini",
            "args_builder": "_build_gemini_args",
        },
    }

    def __init__(self) -> None:
        self.cli_tool: str = settings.AI_CLI_TOOL  # "claude", "codex", or "gemini"
        if self.cli_tool not in self.CLI_CONFIGS:
            raise ValueError(
                f"Unsupported CLI tool: {self.cli_tool}. "
                f"Supported: {list(self.CLI_CONFIGS.keys())}"
            )
        self.config = self.CLI_CONFIGS[self.cli_tool]
        self.timeout_seconds: int = settings.AI_CLI_TIMEOUT  # default: 120

    def _build_full_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
    ) -> str:
        """Assemble the full prompt string sent to the CLI tool."""
        parts = [system_prompt]
        if context:
            parts.append(f"\n--- CONTEXT ---\n{context}\n--- END CONTEXT ---")
        parts.append(f"\n--- USER QUERY ---\n{user_prompt}")
        return "\n".join(parts)

    def _build_claude_args(
        self,
        full_prompt: str,
        max_tokens: int,
        json_mode: bool = False,
    ) -> list[str]:
        """Build argument list for Claude CLI."""
        args = [
            self.config["command"],
            "--print",              # Output response to stdout, no interactive mode
            "--max-tokens", str(max_tokens),
        ]
        if json_mode:
            args.extend(["--output-format", "json"])
        args.extend(["--prompt", full_prompt])
        return args

    def _build_codex_args(
        self,
        full_prompt: str,
        max_tokens: int,
        json_mode: bool = False,
    ) -> list[str]:
        """Build argument list for Codex CLI."""
        args = [
            self.config["command"],
            "--quiet",
            "--prompt", full_prompt,
        ]
        return args

    def _build_gemini_args(
        self,
        full_prompt: str,
        max_tokens: int,
        json_mode: bool = False,
    ) -> list[str]:
        """Build argument list for Gemini CLI."""
        args = [
            self.config["command"],
            "--prompt", full_prompt,
        ]
        return args

    async def _invoke_cli(
        self,
        full_prompt: str,
        max_tokens: int,
        json_mode: bool = False,
    ) -> tuple[str, float]:
        """
        Invoke the CLI tool as an async subprocess.

        Returns: (response_text, latency_ms)
        """
        builder_method = getattr(self, self.config["args_builder"])
        args = builder_method(full_prompt, max_tokens, json_mode)

        start_time = time.monotonic()

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise TimeoutError(
                f"CLI tool '{self.cli_tool}' timed out after {self.timeout_seconds}s"
            )

        latency_ms = (time.monotonic() - start_time) * 1000

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"CLI tool '{self.cli_tool}' exited with code {process.returncode}: "
                f"{error_msg}"
            )

        response_text = stdout.decode("utf-8", errors="replace").strip()
        return response_text, latency_ms

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> AIResponse:
        """Generate a free-text response via CLI subprocess."""
        full_prompt = self._build_full_prompt(system_prompt, user_prompt, context)
        response_text, latency_ms = await self._invoke_cli(
            full_prompt, max_tokens, json_mode=False
        )

        return AIResponse(
            content=response_text,
            model=f"cli:{self.cli_tool}",
            input_tokens=0,   # CLI tools don't report token counts
            output_tokens=0,
            adapter="cli",
            latency_ms=latency_ms,
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        response_schema: dict[str, Any] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AIResponse:
        """
        Generate a structured JSON response via CLI subprocess.

        Appends JSON formatting instructions to the prompt and validates
        the response is valid JSON post-generation.
        """
        # Inject JSON formatting instructions into the system prompt
        schema_instruction = ""
        if response_schema:
            schema_instruction = (
                f"\n\nYou MUST respond with valid JSON matching this schema:\n"
                f"```json\n{json.dumps(response_schema, indent=2)}\n```\n"
                f"Respond ONLY with JSON. No markdown, no explanation, no code fences."
            )

        augmented_system = system_prompt + schema_instruction
        full_prompt = self._build_full_prompt(augmented_system, user_prompt, context)

        response_text, latency_ms = await self._invoke_cli(
            full_prompt, max_tokens, json_mode=True
        )

        # Strip any markdown code fences the model may have included
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Validate it's valid JSON
        try:
            json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"CLI tool returned invalid JSON: {e}\n"
                f"Raw response (first 500 chars): {response_text[:500]}"
            )

        return AIResponse(
            content=cleaned,
            model=f"cli:{self.cli_tool}",
            input_tokens=0,
            output_tokens=0,
            adapter="cli",
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        """Check if the CLI tool is available on the system PATH."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.config["command"], "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=10)
            return process.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
```

### 2.3 OpenRouterAdapter (Production)

The Open Router adapter calls the Open Router API via `httpx`. Open Router provides a unified API for 100+ models from Anthropic, OpenAI, Google, Meta, Mistral, and others. This is the production AI backend.

```python
# app/ai/openrouter_adapter.py

import json
import time
from typing import Any

import httpx

from app.ai.adapter import AIAdapter, AIResponse
from app.core.config import settings


class OpenRouterAdapter(AIAdapter):
    """
    AI adapter that calls the Open Router API.

    Open Router provides a unified OpenAI-compatible API for
    multiple model providers. Used in production deployments.
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self) -> None:
        self.api_key: str = settings.OPENROUTER_API_KEY
        self.default_model: str = settings.OPENROUTER_MODEL  # e.g. "anthropic/claude-sonnet-4"
        self.timeout_seconds: int = settings.AI_OPENROUTER_TIMEOUT  # default: 120
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://chiefops.yensi.ai",
                "X-Title": "ChiefOps Step Zero",
                "Content-Type": "application/json",
            },
        )

    async def _call_api(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool = False,
        response_schema: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], float]:
        """
        Make a single API call to Open Router.

        Returns: (api_response_dict, latency_ms)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        payload: dict[str, Any] = {
            "model": self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Enable JSON mode if structured output is needed
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Some models support JSON schema enforcement
        if response_schema and json_mode:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }

        start_time = time.monotonic()

        response = await self.http_client.post(self.BASE_URL, json=payload)
        response.raise_for_status()

        latency_ms = (time.monotonic() - start_time) * 1000
        return response.json(), latency_ms

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> AIResponse:
        """Generate a free-text response via Open Router API."""
        user_content = user_prompt
        if context:
            user_content = f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n{user_prompt}"

        api_response, latency_ms = await self._call_api(
            system_prompt=system_prompt,
            user_content=user_content,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=False,
        )

        choice = api_response["choices"][0]
        usage = api_response.get("usage", {})

        return AIResponse(
            content=choice["message"]["content"],
            model=api_response.get("model", self.default_model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            adapter="openrouter",
            latency_ms=latency_ms,
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        response_schema: dict[str, Any] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AIResponse:
        """
        Generate a structured JSON response via Open Router API.

        Uses JSON mode and optionally JSON schema enforcement depending
        on model support.
        """
        user_content = user_prompt
        if context:
            user_content = f"--- CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n{user_prompt}"

        # Augment system prompt with schema instructions as fallback
        augmented_system = system_prompt
        if response_schema:
            augmented_system += (
                f"\n\nRespond ONLY with valid JSON matching this schema:\n"
                f"{json.dumps(response_schema, indent=2)}"
            )

        api_response, latency_ms = await self._call_api(
            system_prompt=augmented_system,
            user_content=user_content,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
            response_schema=response_schema,
        )

        choice = api_response["choices"][0]
        usage = api_response.get("usage", {})
        content = choice["message"]["content"]

        # Validate JSON
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Open Router returned invalid JSON: {e}\n"
                f"Model: {api_response.get('model')}\n"
                f"Raw response (first 500 chars): {content[:500]}"
            )

        return AIResponse(
            content=content,
            model=api_response.get("model", self.default_model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            adapter="openrouter",
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        """Verify connectivity to Open Router API."""
        try:
            response = await self.http_client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.http_client.aclose()
```

### 2.4 Factory Pattern

The factory function reads environment configuration and returns the appropriate adapter. All service code calls `get_ai_adapter()` and receives an `AIAdapter` — it never knows or cares which concrete implementation is behind it.

```python
# app/ai/factory.py

from functools import lru_cache

from app.ai.adapter import AIAdapter
from app.ai.cli_adapter import CLIAdapter
from app.ai.openrouter_adapter import OpenRouterAdapter
from app.core.config import settings


@lru_cache(maxsize=1)
def get_ai_adapter() -> AIAdapter:
    """
    Factory function that returns the configured AI adapter.

    Configured via environment variables:
      - AI_ADAPTER: "cli" or "openrouter"
      - AI_CLI_TOOL: "claude", "codex", or "gemini" (only when AI_ADAPTER=cli)
      - OPENROUTER_API_KEY: API key (only when AI_ADAPTER=openrouter)
      - OPENROUTER_MODEL: Model identifier (only when AI_ADAPTER=openrouter)

    Usage in service code:
        adapter = get_ai_adapter()
        response = await adapter.generate(system_prompt, user_prompt, context)
    """
    adapter_type = settings.AI_ADAPTER.lower()

    if adapter_type == "cli":
        return CLIAdapter()
    elif adapter_type == "openrouter":
        return OpenRouterAdapter()
    else:
        raise ValueError(
            f"Unknown AI_ADAPTER: '{adapter_type}'. "
            f"Must be 'cli' or 'openrouter'."
        )
```

### 2.5 Configuration (Settings)

```python
# app/core/config.py (AI-related settings excerpt)

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- AI Adapter Selection ---
    AI_ADAPTER: str = "cli"                           # "cli" or "openrouter"

    # --- CLI Adapter Settings ---
    AI_CLI_TOOL: str = "claude"                       # "claude", "codex", or "gemini"
    AI_CLI_TIMEOUT: int = 120                         # Subprocess timeout in seconds

    # --- Open Router Settings ---
    OPENROUTER_API_KEY: str = ""                      # Open Router API key
    OPENROUTER_MODEL: str = "anthropic/claude-sonnet-4"  # Default model
    AI_OPENROUTER_TIMEOUT: int = 120                  # API timeout in seconds

    # --- Shared AI Settings ---
    AI_MAX_CONTEXT_TOKENS: int = 16000                # Max tokens for context window
    AI_DEFAULT_TEMPERATURE: float = 0.3               # Default sampling temperature
    AI_MAX_RETRIES: int = 3                           # Max retry attempts
    AI_RETRY_DELAY_BASE: float = 1.0                  # Base delay for exponential backoff

    class Config:
        env_file = ".env"
        case_sensitive = True
```

### 2.6 Docker Compose Environment Variables

```yaml
# docker-compose.yml (AI configuration excerpt)
services:
  backend:
    environment:
      # Switch between development and production AI:
      - AI_ADAPTER=cli                        # "cli" for dev, "openrouter" for prod
      - AI_CLI_TOOL=claude                    # Which CLI tool to use in dev
      - AI_CLI_TIMEOUT=120
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENROUTER_MODEL=anthropic/claude-sonnet-4
      - AI_OPENROUTER_TIMEOUT=120
```

### 2.7 Usage in Service Code

Every service that needs AI uses the adapter through dependency injection:

```python
# app/services/query_service.py (example usage)

from app.ai.factory import get_ai_adapter
from app.ai.prompts import GENERAL_QUERY_SYSTEM_PROMPT


class QueryService:
    def __init__(self) -> None:
        self.ai = get_ai_adapter()

    async def answer_query(
        self,
        user_query: str,
        context: str,
    ) -> str:
        """
        Answer a COO query using the AI adapter.
        The service never knows if this goes to Claude CLI or Open Router.
        """
        response = await self.ai.generate(
            system_prompt=GENERAL_QUERY_SYSTEM_PROMPT,
            user_prompt=user_query,
            context=context,
            temperature=0.3,
        )
        return response.content
```

### 2.8 Mock Adapter (Testing)

```python
# tests/mocks/mock_ai_adapter.py

from typing import Any

from app.ai.adapter import AIAdapter, AIResponse


class MockAIAdapter(AIAdapter):
    """
    Mock adapter for unit tests. Returns canned responses
    without calling any AI provider.
    """

    def __init__(self, default_response: str = "Mock AI response") -> None:
        self.default_response = default_response
        self.call_log: list[dict[str, Any]] = []

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> AIResponse:
        self.call_log.append({
            "method": "generate",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "context": context,
        })
        return AIResponse(
            content=self.default_response,
            model="mock",
            input_tokens=100,
            output_tokens=50,
            adapter="mock",
            latency_ms=1.0,
        )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = "",
        response_schema: dict[str, Any] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AIResponse:
        self.call_log.append({
            "method": "generate_structured",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "context": context,
            "response_schema": response_schema,
        })
        return AIResponse(
            content=self.default_response,
            model="mock",
            input_tokens=100,
            output_tokens=50,
            adapter="mock",
            latency_ms=1.0,
        )

    async def health_check(self) -> bool:
        return True
```

---

## 3. What Data Is Sent to the LLM

Understanding exactly what data leaves the system and enters an AI model is critical for data sensitivity, cost management, and debugging. Every AI request in ChiefOps is assembled from specific components, each with a predictable token budget.

### 3.1 Per-Request Token Budget

| Component | Est. Tokens | Content | Source |
|-----------|-------------|---------|--------|
| System prompt | ~800 | Role definition, behavioral rules, output format instructions. Contains NO user data. | Static template from `app/ai/prompts.py` |
| Hard facts | ~300-500 | Corrections and decisions stored in `conversation_facts` (e.g., "Raj is the lead architect", "Sprint deadline moved to March 20") | MongoDB `conversation_facts` collection |
| Global stream facts | ~200-300 | Cross-project context that applies to all queries (e.g., "Company uses Salesforce for CRM", "Engineering team is 30 people") | MongoDB `conversation_facts` with `stream_id = "global"` |
| Compacted summary | ~1,500-2,000 | Progressive summary of all past conversations in the current stream. Built by the memory compaction system. | MongoDB `conversation_summaries` collection |
| Last 10 raw turns | ~3,000-5,000 | The most recent conversation turns with full detail — user query + AI response for each turn | MongoDB `conversation_turns` collection |
| Citex retrieved chunks | ~3,000-6,000 | 10-20 chunks (~300-600 characters each) retrieved via semantic search from Citex. These are the most relevant Slack messages, Jira task details, and document excerpts. | Citex RAG API response |
| Structured data summaries | ~1,000-2,000 | Pre-computed summaries from MongoDB: people directory snapshot, project metrics, active alerts, health scores | MongoDB structured collections |
| User query | ~100-200 | The COO's current question or command | Live user input |
| **TOTAL** | **~10,000-17,000** | | |

### 3.2 What Is NOT Sent

This is equally important. The following data **never** leaves the system:

| Data | Why Not Sent | Where It Stays |
|------|-------------|----------------|
| Entire Slack message dumps | Only semantically relevant chunks are retrieved via Citex | MongoDB + Citex vector store |
| Entire Jira CSV contents | Only matching tasks (by project, assignee, or keyword) are included | MongoDB `jira_tasks` collection |
| All Google Drive documents | Only relevant sections retrieved by semantic search | MongoDB + Citex vector store |
| Raw uploaded files | Files are parsed, chunked, and indexed — raw files are never sent | Docker volume (temp storage) |
| PII that matches redaction patterns | Filtered before sending (see Section 4) | Replaced with tokens |
| Channels/files tagged "never send to AI" | Opt-out tags exclude content from AI context assembly | Stored locally, excluded from Citex queries |
| Historical conversation turns beyond the last 10 | Represented by the compacted summary instead | MongoDB (archived turns) |

### 3.3 Context Assembly Pipeline

The context assembly pipeline runs before every AI request. It gathers the right data from the right sources and fits it within the token budget.

```python
# app/ai/context_assembler.py

from dataclasses import dataclass, field

from app.ai.pii_filter import PIIFilter
from app.services.citex_service import CitexService
from app.services.memory_service import MemoryService
from app.services.structured_data_service import StructuredDataService


@dataclass
class AssembledContext:
    """All context components for a single AI request."""
    hard_facts: str = ""
    global_facts: str = ""
    compacted_summary: str = ""
    recent_turns: str = ""
    citex_chunks: str = ""
    structured_summaries: str = ""
    total_estimated_tokens: int = 0
    chunk_sources: list[dict] = field(default_factory=list)  # For the audit log


class ContextAssembler:
    """
    Assembles the full context payload for an AI request.

    Respects token budgets, applies PII redaction, and logs
    which chunks were included (for the chunk audit log).
    """

    # Token budgets per component (approximate, using ~4 chars per token)
    TOKEN_BUDGETS = {
        "hard_facts": 500,
        "global_facts": 300,
        "compacted_summary": 2000,
        "recent_turns": 5000,
        "citex_chunks": 6000,
        "structured_summaries": 2000,
    }

    def __init__(
        self,
        memory_service: MemoryService,
        citex_service: CitexService,
        structured_data_service: StructuredDataService,
        pii_filter: PIIFilter,
    ) -> None:
        self.memory = memory_service
        self.citex = citex_service
        self.structured = structured_data_service
        self.pii_filter = pii_filter

    async def assemble(
        self,
        stream_id: str,
        user_query: str,
        max_total_tokens: int = 16000,
    ) -> AssembledContext:
        """
        Assemble the full context for an AI request.

        Priority order (if token budget is exceeded, truncate in this order):
          1. Hard facts (NEVER truncated — corrections are sacred)
          2. Global facts (NEVER truncated)
          3. Recent turns (truncate oldest first)
          4. Citex chunks (reduce chunk count)
          5. Compacted summary (truncate end)
          6. Structured summaries (truncate)
        """
        ctx = AssembledContext()

        # 1. Hard facts — always included in full
        facts = await self.memory.get_facts(stream_id)
        ctx.hard_facts = self._format_facts(facts)

        # 2. Global facts — always included in full
        global_facts = await self.memory.get_facts("global")
        ctx.global_facts = self._format_facts(global_facts)

        # 3. Compacted summary
        summary = await self.memory.get_latest_summary(stream_id)
        ctx.compacted_summary = summary.content if summary else ""

        # 4. Recent conversation turns (last 10)
        turns = await self.memory.get_recent_turns(stream_id, limit=10)
        ctx.recent_turns = self._format_turns(turns)

        # 5. Citex semantic search
        chunks = await self.citex.search(
            query=user_query,
            stream_id=stream_id,
            top_k=20,
        )
        ctx.citex_chunks = self._format_chunks(chunks)
        ctx.chunk_sources = [
            {
                "source": c.metadata.get("source", "unknown"),
                "source_type": c.metadata.get("source_type", "unknown"),
                "chunk_id": c.id,
                "relevance_score": c.score,
            }
            for c in chunks
        ]

        # 6. Structured data summaries
        structured = await self.structured.get_summary_for_stream(stream_id)
        ctx.structured_summaries = structured

        # Apply PII redaction to all text components
        ctx.hard_facts = self.pii_filter.redact(ctx.hard_facts)
        ctx.global_facts = self.pii_filter.redact(ctx.global_facts)
        ctx.compacted_summary = self.pii_filter.redact(ctx.compacted_summary)
        ctx.recent_turns = self.pii_filter.redact(ctx.recent_turns)
        ctx.citex_chunks = self.pii_filter.redact(ctx.citex_chunks)
        ctx.structured_summaries = self.pii_filter.redact(ctx.structured_summaries)

        # Estimate total tokens
        all_text = (
            ctx.hard_facts + ctx.global_facts + ctx.compacted_summary
            + ctx.recent_turns + ctx.citex_chunks + ctx.structured_summaries
        )
        ctx.total_estimated_tokens = len(all_text) // 4  # ~4 chars per token

        return ctx

    def to_context_string(self, ctx: AssembledContext) -> str:
        """Format the assembled context into a single string for the AI prompt."""
        sections = []

        if ctx.hard_facts:
            sections.append(f"=== ESTABLISHED FACTS (corrections and decisions) ===\n{ctx.hard_facts}")

        if ctx.global_facts:
            sections.append(f"=== GLOBAL CONTEXT ===\n{ctx.global_facts}")

        if ctx.compacted_summary:
            sections.append(f"=== CONVERSATION HISTORY SUMMARY ===\n{ctx.compacted_summary}")

        if ctx.recent_turns:
            sections.append(f"=== RECENT CONVERSATION (last 10 turns) ===\n{ctx.recent_turns}")

        if ctx.citex_chunks:
            sections.append(f"=== RELEVANT DATA (from Slack, Jira, Drive) ===\n{ctx.citex_chunks}")

        if ctx.structured_summaries:
            sections.append(f"=== STRUCTURED DATA ===\n{ctx.structured_summaries}")

        return "\n\n".join(sections)

    def _format_facts(self, facts: list) -> str:
        return "\n".join(f"- {f.content}" for f in facts)

    def _format_turns(self, turns: list) -> str:
        lines = []
        for t in turns:
            lines.append(f"[{t.role.upper()}]: {t.content}")
        return "\n".join(lines)

    def _format_chunks(self, chunks: list) -> str:
        lines = []
        for i, c in enumerate(chunks, 1):
            source = c.metadata.get("source", "unknown")
            lines.append(f"[Chunk {i} | Source: {source}]\n{c.text}")
        return "\n\n".join(lines)
```

---

## 4. PII Redaction Filter

Before **any** data is sent to an AI model, it passes through the PII redaction filter. This is a mandatory step in the context assembly pipeline (see Section 3.3). The filter scans for personally identifiable information using regex patterns, replaces matches with tokens, and maintains a mapping so the AI response can be de-tokenized for display.

### 4.1 Implementation

```python
# app/ai/pii_filter.py

import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class PIIMapping:
    """Stores the mapping between PII tokens and original values."""
    token_to_original: dict[str, str] = field(default_factory=dict)
    original_to_token: dict[str, str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=lambda: {
        "EMAIL": 0, "PHONE": 0, "SSN": 0, "CREDIT_CARD": 0,
        "IP_ADDRESS": 0, "PASSPORT": 0,
    })


class PIIFilter:
    """
    Scans text for PII patterns and replaces them with reversible tokens.

    Usage:
        pii_filter = PIIFilter()
        redacted_text = pii_filter.redact(raw_text)
        # ... send redacted_text to AI ...
        original_text = pii_filter.restore(ai_response)
    """

    # Regex patterns for different PII types
    PATTERNS: ClassVar[list[tuple[str, re.Pattern]]] = [
        # Email addresses
        ("EMAIL", re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )),
        # US phone numbers (various formats)
        ("PHONE", re.compile(
            r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        )),
        # US Social Security Numbers
        ("SSN", re.compile(
            r"\b\d{3}[-]\d{2}[-]\d{4}\b"
        )),
        # Credit card numbers (basic pattern: 4 groups of 4 digits)
        ("CREDIT_CARD", re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        )),
        # IP addresses (IPv4)
        ("IP_ADDRESS", re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        )),
        # Passport numbers (generic alphanumeric pattern)
        ("PASSPORT", re.compile(
            r"\b[A-Z]{1,2}\d{6,9}\b"
        )),
    ]

    def __init__(self) -> None:
        self.mapping = PIIMapping()

    def redact(self, text: str) -> str:
        """
        Scan text for PII and replace with tokens.

        Each unique PII value gets a unique token: [EMAIL_1], [EMAIL_2], etc.
        The same value always maps to the same token within a session.
        """
        if not text:
            return text

        result = text
        for pii_type, pattern in self.PATTERNS:
            matches = pattern.findall(result)
            for match in matches:
                if match in self.mapping.original_to_token:
                    # Already seen this PII value — reuse the same token
                    token = self.mapping.original_to_token[match]
                else:
                    # New PII value — create a new token
                    self.mapping.counters[pii_type] += 1
                    token = f"[{pii_type}_{self.mapping.counters[pii_type]}]"
                    self.mapping.token_to_original[token] = match
                    self.mapping.original_to_token[match] = token

                result = result.replace(match, token)

        return result

    def restore(self, text: str) -> str:
        """
        Replace PII tokens in AI response with original values.

        Called after receiving the AI response, before displaying to the COO.
        """
        if not text:
            return text

        result = text
        for token, original in self.mapping.token_to_original.items():
            result = result.replace(token, original)

        return result

    def reset(self) -> None:
        """Clear all mappings. Called at the start of each new request."""
        self.mapping = PIIMapping()

    def get_redaction_summary(self) -> dict[str, int]:
        """Return a count of how many PII items were redacted per type."""
        return {
            pii_type: count
            for pii_type, count in self.mapping.counters.items()
            if count > 0
        }
```

### 4.2 Opt-Out Tags

The COO can tag specific Slack channels or Drive files as "never send to AI" during or after ingestion. When the context assembler retrieves chunks from Citex, it filters out any chunks whose source is tagged with an opt-out flag.

```python
# Opt-out check during chunk retrieval (in CitexService)

async def search(self, query: str, stream_id: str, top_k: int = 20) -> list:
    """Search Citex for relevant chunks, excluding opt-out sources."""
    raw_chunks = await self._citex_api_search(query, top_k=top_k * 2)

    # Load opt-out sources from MongoDB
    opt_out_sources = await self.db.opt_out_tags.distinct("source_id")

    # Filter out chunks from opted-out sources
    filtered = [
        chunk for chunk in raw_chunks
        if chunk.metadata.get("source_id") not in opt_out_sources
    ]

    return filtered[:top_k]
```

---

## 5. Chunk Audit Log

Every AI request produces an audit log entry that records exactly which data was sent to the LLM. This provides full transparency to the COO — they can see the provenance of every AI response.

### 5.1 Audit Log Schema

```python
# app/models/ai_audit.py

from datetime import datetime

from pydantic import BaseModel, Field


class ChunkReference(BaseModel):
    """Reference to a single chunk included in an AI request."""
    chunk_id: str
    source_type: str              # "slack", "jira", "drive"
    source_identifier: str        # Channel name, Jira key, file name
    relevance_score: float        # Semantic search score (0.0 - 1.0)
    char_count: int               # Length of the chunk text


class FactReference(BaseModel):
    """Reference to a fact included in an AI request."""
    fact_id: str
    content: str                  # The fact text
    fact_type: str                # "correction", "decision", "context"
    stream_id: str                # Which project stream this fact belongs to


class AIAuditEntry(BaseModel):
    """Complete audit log for a single AI request."""
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stream_id: str                # Project stream context
    user_query: str               # What the COO asked
    operation_type: str           # "general_query", "people_analysis", "report_gen", etc.

    # What was sent
    chunks_included: list[ChunkReference] = []
    facts_included: list[FactReference] = []
    turns_included: int = 0       # Number of recent turns sent
    summary_included: bool = False
    structured_data_included: bool = False

    # Token accounting
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    total_tokens: int = 0

    # PII redaction stats
    pii_redactions: dict[str, int] = {}  # {"EMAIL": 2, "PHONE": 1}

    # Response metadata
    adapter_used: str = ""        # "cli" or "openrouter"
    model_used: str = ""          # "cli:claude" or "anthropic/claude-sonnet-4"
    latency_ms: float = 0.0
    response_length: int = 0      # Character count of the response

    # Human-readable source summary (displayed in the UI)
    source_summary: str = ""      # e.g., "Used 12 chunks from: Slack (#engineering), ..."
```

### 5.2 Audit Log Service

```python
# app/services/ai_audit_service.py

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.ai.adapter import AIResponse
from app.ai.context_assembler import AssembledContext
from app.models.ai_audit import AIAuditEntry, ChunkReference, FactReference


class AIAuditService:
    """Logs every AI request for transparency and debugging."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db["ai_audit_log"]

    async def log_request(
        self,
        stream_id: str,
        user_query: str,
        operation_type: str,
        context: AssembledContext,
        response: AIResponse,
        pii_redactions: dict[str, int],
    ) -> AIAuditEntry:
        """Create and persist an audit log entry."""

        # Build human-readable source summary
        source_summary = self._build_source_summary(context.chunk_sources)

        entry = AIAuditEntry(
            stream_id=stream_id,
            user_query=user_query,
            operation_type=operation_type,
            chunks_included=[
                ChunkReference(
                    chunk_id=cs["chunk_id"],
                    source_type=cs["source_type"],
                    source_identifier=cs["source"],
                    relevance_score=cs["relevance_score"],
                    char_count=0,  # Could be computed during assembly
                )
                for cs in context.chunk_sources
            ],
            turns_included=context.recent_turns.count("[USER]:"),
            summary_included=bool(context.compacted_summary),
            structured_data_included=bool(context.structured_summaries),
            estimated_input_tokens=response.input_tokens or context.total_estimated_tokens,
            estimated_output_tokens=response.output_tokens,
            total_tokens=(response.input_tokens or context.total_estimated_tokens)
                        + response.output_tokens,
            pii_redactions=pii_redactions,
            adapter_used=response.adapter,
            model_used=response.model,
            latency_ms=response.latency_ms,
            response_length=len(response.content),
            source_summary=source_summary,
        )

        await self.collection.insert_one(entry.model_dump())
        return entry

    def _build_source_summary(self, chunk_sources: list[dict]) -> str:
        """
        Build a human-readable summary like:
        'Used 12 chunks from: Slack (#engineering, #product), Jira (PROJ-142, PROJ-155),
         Drive (architecture.pdf page 3)'
        """
        if not chunk_sources:
            return "No external data sources used"

        by_type: dict[str, set[str]] = {}
        for cs in chunk_sources:
            source_type = cs["source_type"]
            source_id = cs["source"]
            by_type.setdefault(source_type, set()).add(source_id)

        total = len(chunk_sources)
        parts = []
        for source_type, sources in sorted(by_type.items()):
            source_list = ", ".join(sorted(sources)[:5])  # Show up to 5 sources per type
            if len(sources) > 5:
                source_list += f", +{len(sources) - 5} more"
            parts.append(f"{source_type.title()} ({source_list})")

        return f"Used {total} chunks from: {', '.join(parts)}"
```

### 5.3 UI Display

The audit log is surfaced to the COO in the conversation interface. Every AI response includes a collapsible "Sources" section:

```
> This answer used 12 chunks from:
> - Slack: #engineering (4), #product (2), #general (1)
> - Jira: PROJ-142, PROJ-155, PROJ-201
> - Drive: architecture.pdf (page 3), roadmap.docx (section 2)
>
> 2 PII items were redacted before processing.
> Processed in 2.3s using cli:claude.
```

---

## 6. Prompt Templates

Each AI operation in ChiefOps has a dedicated system prompt that defines the AI's role, the context structure it will receive, the output format expected, and behavioral constraints. All prompts are stored in `app/ai/prompts.py` as constants.

### 6.1 General Query Answering

```python
GENERAL_QUERY_SYSTEM_PROMPT = """You are ChiefOps, an AI-powered Chief Operations Officer assistant.
You help a startup COO understand their organization's operational state by analyzing data from
Slack conversations, Jira tasks, and Google Drive documents.

CONTEXT STRUCTURE:
You will receive context in clearly labeled sections:
- ESTABLISHED FACTS: Corrections and decisions made by the COO. These override any conflicting data.
- GLOBAL CONTEXT: Organization-wide context that applies to all queries.
- CONVERSATION HISTORY SUMMARY: A condensed summary of previous conversations in this project stream.
- RECENT CONVERSATION: The last several conversation turns for immediate context.
- RELEVANT DATA: Chunks retrieved from Slack, Jira, and Google Drive via semantic search.
- STRUCTURED DATA: Pre-computed metrics, people directory entries, and project summaries.

BEHAVIORAL RULES:
1. ESTABLISHED FACTS always take priority. If a fact says "Raj is the lead architect" but
   Slack data suggests otherwise, use the established fact.
2. Cite your sources naturally: "Based on Slack messages in #engineering..." or
   "According to the Jira data..."
3. If you don't have enough data to answer confidently, say so. Never fabricate information.
4. Be concise but thorough. The COO is busy and wants actionable intelligence.
5. When identifying risks or concerns, be specific about what data supports the concern.
6. Use bullet points and clear structure for complex answers.
7. If the query is about a specific person or project, focus your response accordingly.

OUTPUT FORMAT:
Respond in clear, professional prose with structured formatting when appropriate.
Use markdown for emphasis, lists, and headers when the answer warrants structure."""
```

### 6.2 People Analysis

```python
PEOPLE_ANALYSIS_SYSTEM_PROMPT = """You are an organizational analyst. Your task is to identify people,
their roles, and their task assignments from raw operational data.

INPUT: You will receive Slack messages, Jira task descriptions, and document excerpts.

YOUR TASK:
1. Identify every unique person mentioned (by name, @mention, or email).
2. Determine their likely role based on context (developer, designer, PM, architect, etc.).
3. Map them to specific tasks or projects based on:
   - Jira task assignee fields
   - Informal assignments in Slack ("Hey Raj, can you pick up PROJ-142?")
   - Task descriptions mentioning their name
   - Code review or PR mentions
4. Assess their engagement level: active (contributing regularly), moderate, or inactive.
5. Note any conflicting information (e.g., two different roles suggested for the same person).

IMPORTANT:
- One task CAN be assigned to multiple people.
- Informal Slack assignments are as valid as Jira assignee fields.
- If a person's role is ambiguous, provide your best assessment with a confidence indicator.

OUTPUT FORMAT: Respond with valid JSON matching the provided schema."""
```

### 6.3 Project Analysis

```python
PROJECT_ANALYSIS_SYSTEM_PROMPT = """You are a project intelligence analyst. Your task is to assess
the current state of a project using all available data sources.

INPUT: You will receive Slack messages, Jira task data, document excerpts, and any established facts
about this project.

YOUR ANALYSIS MUST COVER:
1. OVERALL STATUS: On track, at risk, behind schedule, or blocked. Justify with data.
2. COMPLETION ASSESSMENT: Estimate percentage complete based on task completion rates, remaining work,
   and team velocity.
3. TIMELINE ANALYSIS: Current deadline, whether it's achievable, and what milestones remain.
4. TEAM ASSESSMENT: Who is actively contributing, who is overloaded, who has gone quiet.
5. RISKS AND CONCERNS: Specific, data-backed risks. Not generic warnings.
6. BLOCKERS: Any tasks or dependencies that are blocking progress.
7. RECENT ACTIVITY: What happened in the last reporting period (based on Slack activity and Jira transitions).

RULES:
- Be specific. Instead of "the team is behind," say "7 of 23 sprint tasks are incomplete with 3 days
  remaining, and velocity over the last 2 weeks was 4 tasks/week."
- If data is insufficient for a section, explicitly state what data is missing.
- Established facts override any conflicting data from other sources.

OUTPUT FORMAT: Respond with valid JSON matching the provided schema."""
```

### 6.4 Technical Feasibility

```python
TECHNICAL_FEASIBILITY_SYSTEM_PROMPT = """You are a technical feasibility advisor. Your task is to
analyze a project's technical plan and identify gaps, missing prerequisites, and risks.

ANALYSIS APPROACH:
1. BACKWARD PLANNING: Start from the deadline and work backward. What must be done by when?
   Account for dependencies, lead times, and realistic task durations.

2. MISSING PREREQUISITES: Identify tasks that SHOULD exist but don't. Common examples:
   - App Store developer account setup (4-7 day approval)
   - SSL certificate provisioning
   - Third-party API credential acquisition
   - Database migration rollback plans
   - Load testing before launch
   - Security audit or penetration testing
   - Documentation for handoff

3. CAPACITY ANALYSIS: Compare remaining work against team capacity.
   - How many tasks remain?
   - What is the team's observed velocity?
   - How many people are actively contributing?
   - Is the deadline achievable at current velocity?

4. EXTERNAL DEPENDENCIES: Identify tasks with external lead times:
   - Vendor approvals, app store reviews, compliance certifications
   - Third-party integrations with unknown complexity
   - Hardware or infrastructure procurement

5. TECHNICAL RISK QUESTIONS: Generate questions the COO should ask the technical lead.
   These should be specific to the project, not generic.

OUTPUT FORMAT: Respond with valid JSON matching the provided schema.
Each finding should include: category, severity (critical/high/medium/low),
description, and recommended action."""
```

### 6.5 Report Generation

```python
REPORT_GENERATION_SYSTEM_PROMPT = """You are a report specification generator. Your task is to
produce a structured JSON specification that the report rendering engine will use to create
a professional PDF document.

INPUT: You will receive the COO's report request (type, scope, time period) along with
operational data from all sources.

REPORT SPEC STRUCTURE:
You must output a JSON object with:
- title: Report title
- subtitle: Time period or scope descriptor
- generated_at: ISO timestamp
- sections: Array of section objects, each with:
  - heading: Section title
  - content_type: "prose" | "table" | "chart" | "kpi_grid" | "list"
  - content: The actual content (text for prose, data for tables/charts)
  - chart_spec: (if content_type is "chart") ECharts-compatible JSON

RULES:
- Structure the report logically: executive summary first, then details, then recommendations.
- Include specific data points, not vague statements.
- For charts, generate valid ECharts option objects.
- For tables, provide headers and rows as arrays.
- Keep prose sections concise — this is a board report, not a novel.
- Include an "Areas of Concern" section if there are risks worth highlighting.
- End with actionable recommendations.

OUTPUT FORMAT: Respond ONLY with valid JSON. No markdown, no explanation."""
```

### 6.6 Chart Specification

```python
CHART_SPECIFICATION_SYSTEM_PROMPT = """You are a data visualization specialist. Your task is to
generate Apache ECharts option JSON from data and a natural language description.

INPUT: You will receive:
1. The COO's request (e.g., "Show me a person vs. tasks chart")
2. Available data (people, tasks, metrics, timelines)

OUTPUT: A valid Apache ECharts option JSON object that can be passed directly to
echarts.setOption().

CHART TYPES YOU SUPPORT:
- bar: Standard and stacked bar charts
- line: Single and multi-series line charts
- pie: Pie and donut charts
- gantt: Timeline/Gantt charts (using custom series)
- heatmap: Activity density heatmaps
- scatter: Scatter plots for correlation analysis

RULES:
1. Choose the most appropriate chart type for the data and request.
2. Use a professional color palette: ["#5470c6", "#91cc75", "#fac858", "#ee6666",
   "#73c0de", "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"]
3. Always include: title, tooltip, legend (if multi-series), and axis labels.
4. Make the chart responsive (don't hardcode pixel dimensions).
5. Include meaningful axis labels and data labels where appropriate.
6. For Gantt charts, use the custom series type with renderItem.

OUTPUT FORMAT: Respond ONLY with a valid JSON object. No markdown, no explanation, no code fences."""
```

### 6.7 NL Intent Detection

```python
NL_INTENT_DETECTION_SYSTEM_PROMPT = """You are an intent classifier for a COO operations assistant.
Your task is to classify the user's input into one of the following intent categories and extract
relevant parameters.

INTENT CATEGORIES:

1. "query" — The user is asking a question about their organization, projects, or people.
   Parameters: { topic, scope, time_range }

2. "correction" — The user is correcting a fact. E.g., "Raj is the lead architect, not a junior dev."
   Parameters: { entity, attribute, old_value, new_value }

3. "command_add_widget" — The user wants to add a widget to their dashboard.
   Parameters: { widget_type, data_scope, chart_type }

4. "command_remove_widget" — The user wants to remove a widget.
   Parameters: { widget_identifier }

5. "command_modify_widget" — The user wants to change an existing widget.
   Parameters: { widget_identifier, changes }

6. "command_generate_report" — The user wants to generate a report.
   Parameters: { report_type, scope, time_period }

7. "command_set_alert" — The user wants to configure an alert threshold.
   Parameters: { metric, operator, threshold, scope }

8. "greeting" — Social interaction, greetings, or meta-conversation.
   Parameters: {}

9. "clarification_needed" — The input is ambiguous and needs clarification.
   Parameters: { possible_intents, clarification_question }

OUTPUT FORMAT: Respond with valid JSON:
{
  "intent": "<intent_category>",
  "confidence": <0.0-1.0>,
  "parameters": { ... },
  "reasoning": "<one sentence explaining the classification>"
}"""
```

### 6.8 Conversation Summary

```python
CONVERSATION_SUMMARY_SYSTEM_PROMPT = """You are a conversation summarizer for an operations
intelligence system. Your task is to summarize a set of conversation turns into a concise
session summary.

INPUT: A sequence of conversation turns between the COO and the AI assistant.

YOUR TASK:
1. Capture the KEY TOPICS discussed (projects, people, decisions).
2. Note any DECISIONS made or ACTIONS agreed upon.
3. Record any CORRECTIONS the COO made to the system's understanding.
4. Summarize INSIGHTS the AI provided that the COO found valuable (evidenced by follow-up questions
   or acknowledgment).
5. Note any UNRESOLVED QUESTIONS or topics the COO may return to.

RULES:
- Be concise. Target 200-400 words for a 10-turn conversation.
- Use present tense for ongoing states: "Project Alpha is behind schedule."
- Use past tense for completed actions: "COO requested a board report."
- Do NOT include verbatim quotes from the conversation.
- Focus on information density — every sentence should convey useful context.
- This summary will be used as context for future conversations, so it must be self-contained.

OUTPUT FORMAT: A structured summary with labeled sections:
TOPICS: ...
DECISIONS: ...
CORRECTIONS: ...
KEY INSIGHTS: ...
OPEN ITEMS: ..."""
```

### 6.9 Fact Extraction

```python
FACT_EXTRACTION_SYSTEM_PROMPT = """You are a fact extractor for an operations intelligence system.
Your task is to identify hard facts from conversation turns that should be persisted and used in
all future interactions.

A "hard fact" is:
- A CORRECTION: The COO corrects the system's understanding.
  Examples: "Raj is the lead architect, not a junior dev."
            "The deadline moved to April 1."
            "Project Beta was cancelled."
- A DECISION: The COO states a decision that affects operations.
  Examples: "We're going with vendor X for the payment integration."
            "Hiring is frozen until Q2."
- A STANDING INSTRUCTION: A rule the system should always follow.
  Examples: "Always prioritize Project Alpha in briefings."
            "Never include salary data in reports."

INPUT: Recent conversation turns.

OUTPUT: A JSON array of fact objects:
[
  {
    "content": "Clear, self-contained statement of the fact",
    "fact_type": "correction" | "decision" | "instruction",
    "entity": "Person, project, or topic this fact is about",
    "confidence": 0.0-1.0,
    "source_turn_index": <index of the conversation turn that contains this fact>
  }
]

RULES:
- Only extract EXPLICIT facts stated by the COO (the user), not inferences.
- Each fact must be self-contained — understandable without the surrounding conversation.
- Do NOT extract opinions, questions, or speculative statements.
- If no facts are found, return an empty array: []

OUTPUT FORMAT: Respond ONLY with valid JSON array. No markdown, no explanation."""
```

### 6.10 Slack Summarization

```python
SLACK_SUMMARIZATION_SYSTEM_PROMPT = """You are a Slack message summarizer for an operations
intelligence system. Your task is to distill a batch of Slack messages into a concise,
project-level summary.

INPUT: A batch of Slack messages from one or more channels, including:
- Channel name
- Sender name/handle
- Timestamp
- Message text
- Thread context (if applicable)

YOUR TASK:
1. Identify the KEY TOPICS discussed.
2. Note any DECISIONS made in the conversation.
3. Identify TASK ASSIGNMENTS (explicit or informal).
4. Flag any CONCERNS, BLOCKERS, or ESCALATIONS.
5. Note who the ACTIVE PARTICIPANTS are and their roles in the discussion.
6. Capture any DEADLINES or DATES mentioned.
7. Identify SENTIMENT: is the team positive, frustrated, neutral?

RULES:
- Group related messages into coherent topic summaries.
- Attribute actions and decisions to specific people.
- Distinguish between decisions and open discussions.
- Ignore social chatter, emoji reactions, and off-topic messages unless they reveal team sentiment.
- Target 100-300 words per channel summary.
- This summary will be stored in the system's knowledge base, so it must be self-contained.

OUTPUT FORMAT:
CHANNEL: #channel-name
PERIOD: [date range]
SUMMARY: ...
DECISIONS: ...
ASSIGNMENTS: ...
CONCERNS: ...
PARTICIPANTS: ...
SENTIMENT: ..."""
```

---

## 7. Structured Output

Many AI operations in ChiefOps require structured JSON output rather than free-form text. Charts need ECharts-compatible JSON. Reports need a section-based specification. People analysis needs structured person objects. Intent detection needs a classified intent with parameters.

### 7.1 Structured Output Strategy

ChiefOps enforces structured output through three layers:

**Layer 1: Prompt Instructions**
Every structured-output prompt explicitly specifies the expected JSON format and includes the instruction "Respond ONLY with valid JSON." This works across all models and adapters.

**Layer 2: JSON Mode / Schema Enforcement**
When using the Open Router adapter, the API call includes `response_format: { type: "json_object" }` or `response_format: { type: "json_schema", json_schema: {...} }` depending on model support. This provides model-level enforcement.

**Layer 3: Post-Processing Validation with Pydantic v2**
Every structured response is validated against a Pydantic v2 model after generation. If validation fails, the system re-prompts with stricter instructions.

### 7.2 Response Schemas (Pydantic v2 Models)

```python
# app/ai/schemas.py

from pydantic import BaseModel, Field


# --- Chart Specification ---
class ChartSpec(BaseModel):
    """ECharts-compatible chart specification."""
    title: dict = Field(..., description="ECharts title configuration")
    tooltip: dict = Field(default_factory=dict)
    legend: dict | None = None
    xAxis: dict | list[dict] | None = None
    yAxis: dict | list[dict] | None = None
    series: list[dict] = Field(..., description="ECharts series array")
    color: list[str] | None = None
    grid: dict | None = None


# --- Report Specification ---
class ReportSection(BaseModel):
    heading: str
    content_type: str = Field(..., pattern="^(prose|table|chart|kpi_grid|list)$")
    content: str | list | dict
    chart_spec: ChartSpec | None = None

class ReportSpec(BaseModel):
    title: str
    subtitle: str
    generated_at: str
    sections: list[ReportSection]


# --- People Analysis ---
class PersonAnalysis(BaseModel):
    name: str
    identifiers: list[str] = Field(default_factory=list, description="@handles, emails")
    inferred_role: str
    role_confidence: float = Field(ge=0.0, le=1.0)
    assigned_tasks: list[str] = Field(default_factory=list)
    engagement_level: str = Field(..., pattern="^(active|moderate|inactive)$")
    projects: list[str] = Field(default_factory=list)
    notes: str = ""

class PeopleAnalysisResult(BaseModel):
    people: list[PersonAnalysis]
    conflicts: list[str] = Field(default_factory=list, description="Conflicting data notes")


# --- Intent Detection ---
class DetectedIntent(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    parameters: dict = Field(default_factory=dict)
    reasoning: str = ""


# --- Fact Extraction ---
class ExtractedFact(BaseModel):
    content: str
    fact_type: str = Field(..., pattern="^(correction|decision|instruction)$")
    entity: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_turn_index: int

class FactExtractionResult(BaseModel):
    facts: list[ExtractedFact]
```

### 7.3 Validation Pipeline

```python
# app/ai/structured_output.py

import json
from typing import TypeVar, Type

from pydantic import BaseModel, ValidationError

from app.ai.adapter import AIAdapter, AIResponse

T = TypeVar("T", bound=BaseModel)


async def generate_and_validate(
    adapter: AIAdapter,
    system_prompt: str,
    user_prompt: str,
    context: str,
    response_model: Type[T],
    max_retries: int = 2,
) -> T:
    """
    Generate a structured response and validate it against a Pydantic model.

    If validation fails, re-prompts with the validation error for self-correction.
    """
    schema = response_model.model_json_schema()

    for attempt in range(max_retries + 1):
        response: AIResponse = await adapter.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=context,
            response_schema=schema,
        )

        try:
            parsed = json.loads(response.content)
            validated = response_model.model_validate(parsed)
            return validated
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == max_retries:
                raise ValueError(
                    f"Failed to get valid structured output after {max_retries + 1} attempts. "
                    f"Last error: {e}"
                )

            # Re-prompt with the error for self-correction
            user_prompt = (
                f"Your previous response had a validation error:\n{e}\n\n"
                f"Please fix the JSON and respond again. Original request:\n{user_prompt}"
            )

    # This line should be unreachable, but satisfies the type checker
    raise ValueError("Exhausted retries for structured output")
```

---

## 8. Error Handling

The AI layer must handle failures gracefully without crashing the system or returning unintelligible errors to the COO.

### 8.1 Error Categories and Strategies

| Error | Adapter | Strategy | User-Facing Message |
|-------|---------|----------|-------------------|
| CLI subprocess timeout | CLI | Retry with shorter context (remove oldest turns, reduce chunk count) | "Processing took longer than expected. Retrying with condensed context..." |
| CLI tool not found | CLI | Raise startup error, log instructions for installing the CLI tool | "AI tool not configured. Please install [tool] CLI." |
| CLI non-zero exit code | CLI | Parse stderr, retry once. If persistent, surface the error. | "AI processing encountered an error. Retrying..." |
| API rate limit (429) | OpenRouter | Exponential backoff: 1s, 2s, 4s, 8s. Max 4 retries. | "AI service is busy. Retrying shortly..." |
| API timeout | OpenRouter | Retry with shorter context | "AI service is slow. Retrying with condensed context..." |
| API auth error (401/403) | OpenRouter | Do not retry. Surface configuration error. | "AI service authentication failed. Check API key." |
| API server error (500/502/503) | OpenRouter | Retry with exponential backoff, max 3 retries | "AI service temporarily unavailable. Retrying..." |
| Malformed JSON response | Both | Re-prompt with stricter format instructions + the validation error | (Transparent retry, no user-facing message unless all retries fail) |
| Context too large | Both | Truncate in priority order: structured summaries, compacted summary (tail), Citex chunks (reduce count), recent turns (oldest first). NEVER remove facts. | (Transparent, no user-facing message) |
| Invalid response content | Both | Re-prompt with clarified instructions | "I had trouble understanding the AI response. Let me try again..." |

### 8.2 Retry Implementation

```python
# app/ai/retry.py

import asyncio
import logging
from typing import Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (
        TimeoutError,
        httpx.HTTPStatusError,
        httpx.ConnectError,
        RuntimeError,
    ),
) -> T:
    """
    Execute an async operation with exponential backoff retry.

    Does NOT retry on:
    - ValueError (malformed response — handled by structured_output.py)
    - Authentication errors (401/403)
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except httpx.HTTPStatusError as e:
            # Don't retry auth errors
            if e.response.status_code in (401, 403):
                raise
            last_exception = e
        except retryable_exceptions as e:
            last_exception = e

        if attempt < max_retries:
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"AI request failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{last_exception}. Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    raise last_exception
```

### 8.3 Context Truncation Strategy

When the assembled context exceeds the token budget, the system truncates in a strict priority order. Hard facts and global facts are NEVER truncated — they represent the COO's corrections and are sacred.

```python
# app/ai/context_truncator.py

def truncate_context(
    context: "AssembledContext",
    max_tokens: int = 16000,
    chars_per_token: int = 4,
) -> "AssembledContext":
    """
    Truncate context components to fit within the token budget.

    Priority (NEVER truncated first → truncated first):
    1. Hard facts — NEVER truncated
    2. Global facts — NEVER truncated
    3. User query — NEVER truncated
    4. Recent turns — truncate oldest turns first
    5. Citex chunks — remove lowest-scoring chunks
    6. Compacted summary — truncate from the end
    7. Structured summaries — truncate from the end
    """
    max_chars = max_tokens * chars_per_token

    # Calculate immutable content size (facts)
    immutable_size = len(context.hard_facts) + len(context.global_facts)

    # Calculate total current size
    total = (
        len(context.hard_facts) + len(context.global_facts)
        + len(context.compacted_summary) + len(context.recent_turns)
        + len(context.citex_chunks) + len(context.structured_summaries)
    )

    if total <= max_chars:
        return context  # No truncation needed

    excess = total - max_chars

    # Truncation order: structured_summaries, compacted_summary, citex_chunks, recent_turns
    # We truncate from the end of each section
    truncation_targets = [
        "structured_summaries",
        "compacted_summary",
        "citex_chunks",
        "recent_turns",
    ]

    for attr in truncation_targets:
        if excess <= 0:
            break
        current_value = getattr(context, attr)
        if len(current_value) > 0:
            trim_amount = min(excess, len(current_value))
            setattr(context, attr, current_value[:-trim_amount])
            excess -= trim_amount

    context.total_estimated_tokens = (
        len(context.hard_facts) + len(context.global_facts)
        + len(context.compacted_summary) + len(context.recent_turns)
        + len(context.citex_chunks) + len(context.structured_summaries)
    ) // chars_per_token

    return context
```

---

## 9. Cost and Token Management

AI usage drives the primary operational cost of ChiefOps. Tracking and managing token consumption is essential for both development budgets and production cost control.

### 9.1 Token Tracking

Every AI request records token usage via the `AIResponse` object and the audit log. The system aggregates this data for monitoring.

```python
# app/services/token_tracking_service.py

from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field


class TokenUsageSummary(BaseModel):
    """Aggregated token usage statistics."""
    period: str                            # "today", "this_week", "this_month"
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_requests: int = 0
    avg_tokens_per_request: float = 0.0
    breakdown_by_operation: dict[str, int] = Field(default_factory=dict)
    breakdown_by_model: dict[str, int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0


class TokenTrackingService:
    """Tracks and reports on AI token usage."""

    # Approximate cost per million tokens (varies by model)
    COST_PER_MILLION_TOKENS = {
        "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
        "anthropic/claude-haiku-3.5": {"input": 0.25, "output": 1.25},
        "openai/gpt-4o": {"input": 2.5, "output": 10.0},
        "cli:claude": {"input": 3.0, "output": 15.0},   # Same as API pricing
        "cli:codex": {"input": 2.5, "output": 10.0},
        "cli:gemini": {"input": 1.25, "output": 5.0},
    }

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.audit_collection = db["ai_audit_log"]

    async def get_usage_summary(self, period: str = "today") -> TokenUsageSummary:
        """Get aggregated token usage for a time period."""
        now = datetime.utcnow()

        if period == "today":
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "this_week":
            since = now - timedelta(days=now.weekday())
            since = since.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "this_month":
            since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            since = now - timedelta(days=1)

        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "total_input_tokens": {"$sum": "$estimated_input_tokens"},
                "total_output_tokens": {"$sum": "$estimated_output_tokens"},
                "total_tokens": {"$sum": "$total_tokens"},
                "total_requests": {"$sum": 1},
            }},
        ]

        result = await self.audit_collection.aggregate(pipeline).to_list(1)

        if not result:
            return TokenUsageSummary(period=period)

        r = result[0]
        total_requests = r.get("total_requests", 0)
        total_tokens = r.get("total_tokens", 0)

        return TokenUsageSummary(
            period=period,
            total_input_tokens=r.get("total_input_tokens", 0),
            total_output_tokens=r.get("total_output_tokens", 0),
            total_tokens=total_tokens,
            total_requests=total_requests,
            avg_tokens_per_request=total_tokens / total_requests if total_requests > 0 else 0,
        )
```

### 9.2 Cost Estimation

For the CLI adapter, token counts are not directly reported by the subprocess. The system estimates token usage based on the input/output character counts (approximately 4 characters per token). For the Open Router adapter, token counts come directly from the API response.

### 9.3 Budget Controls

| Environment | Control Mechanism |
|-------------|------------------|
| Development (CLI) | Token usage logged locally. Developer monitors their AI provider's billing dashboard (Anthropic Console, OpenAI Platform, etc.). |
| Production (Open Router) | Open Router provides built-in budget controls: daily/monthly spending limits, per-model caps, and usage alerts configurable via the Open Router dashboard. |

### 9.4 Token Optimization Strategies

1. **Progressive context loading** — start with minimal context (facts + recent turns only). If the response indicates insufficient information, retry with Citex chunks.
2. **Chunk deduplication** — Citex may return overlapping chunks. Deduplicate before including in context.
3. **Summary reuse** — the compacted summary avoids resending all historical turns. A 50-turn conversation history (~25,000 tokens) is represented as a ~1,500-token summary.
4. **Operation-specific budgets** — intent detection uses ~2,000 tokens total (small context, small response). Full project analysis uses ~15,000 tokens. Budget allocation is per operation type.
5. **Caching** — identical queries within a short window (e.g., the COO refreshes the page) can serve cached responses without a new AI call. Cache key: hash of (system_prompt + context + user_query). TTL: 5 minutes.

---

## 10. Data Privacy Guarantees

ChiefOps handles sensitive operational data — Slack conversations, task assignments, project plans, and organizational structure. The data privacy architecture ensures that this data is handled responsibly at every stage.

### 10.1 Data Flow and Privacy Boundaries

```
+-------------------------------------------------------------------+
|                    COO's Machine (Docker)                          |
|                                                                    |
|  [Uploaded Files] --> [Parsers] --> [MongoDB] --> [Citex Vectors]  |
|                                                                    |
|  All data resides here. Nothing leaves except AI request payloads. |
+-------------------------------------------------------------------+
          |
          | Only relevant chunks (~10K-17K tokens)
          | PII redacted before transmission
          |
          v
+-----------------------------------+
|  AI Provider (External)           |
|                                   |
|  Receives: system prompt +        |
|    redacted context + query       |
|                                   |
|  Returns: response text           |
|                                   |
|  Does NOT retain data for         |
|  training (policy-dependent)      |
+-----------------------------------+
```

### 10.2 Provider Privacy Policies

| Provider | Training on API Data? | Data Retention | Notes |
|----------|----------------------|----------------|-------|
| Anthropic (Claude API) | No | 30-day safety retention, then deleted | Anthropic's usage policy explicitly states API data is not used for training. |
| Open Router | Depends on underlying model provider | Varies | Open Router acts as a proxy. Most enterprise-grade models (Claude, GPT-4) offer no-training guarantees through Open Router. Check per-model policies. |
| CLI Tools (dev) | Same as API | Same as API | CLI tools use the same API endpoints as direct API calls. Same policies apply. |

### 10.3 Privacy Controls Available to the COO

| Control | Description | Implementation |
|---------|-------------|----------------|
| PII Redaction | Automatic scanning and masking of emails, phone numbers, SSNs, credit cards, IPs | `PIIFilter` class (Section 4). Runs before every AI request. |
| Opt-Out Tags | Mark specific Slack channels or Drive files as "never send to AI" | MongoDB `opt_out_tags` collection. Chunks from these sources are excluded from Citex search results. |
| Chunk Audit Log | See exactly which data was sent in each AI request | `AIAuditService` (Section 5). Displayed in the UI with every AI response. |
| Data Locality | All raw data stays on the COO's machine in Docker volumes | No cloud sync, no telemetry, no external data storage. |
| Minimal Data Transmission | Only relevant chunks sent, not full dumps | Context assembly pipeline (Section 3) retrieves only semantically relevant content. |

### 10.4 What Happens to Data at Each Stage

| Stage | Data Location | Encrypted? | Who Can Access? |
|-------|-------------|------------|-----------------|
| File upload | Docker volume (`/data/uploads/`) | At rest: depends on host disk encryption | COO only (local machine) |
| Parsed data | MongoDB (Docker volume) | MongoDB at rest encryption available | COO only |
| Vector embeddings | Citex/Qdrant (Docker volume) | Qdrant supports encryption at rest | COO only |
| AI request payload | In transit to AI provider | TLS 1.2+ (HTTPS) | AI provider processes, does not store for training |
| AI response | In transit from AI provider | TLS 1.2+ (HTTPS) | Stored in MongoDB conversation history |
| Audit log | MongoDB (Docker volume) | Same as parsed data | COO only |

### 10.5 What ChiefOps Does NOT Do

- Does NOT send telemetry or usage analytics to YENSI or any third party
- Does NOT phone home or check for updates
- Does NOT store data outside the Docker volumes
- Does NOT require internet access except for AI model API calls
- Does NOT share data between different ChiefOps deployments
- Does NOT retain AI request payloads after the response is received (only the audit log metadata is kept, not the full context text)

---

## Related Documents

- **Architecture:** [Architecture](./02-ARCHITECTURE.md) for system-level design and service boundaries
- **Memory System:** [Memory System](./04-MEMORY-SYSTEM.md) for conversation history, facts, and compaction
- **Citex Integration:** [Citex Integration](./05-CITEX-INTEGRATION.md) for RAG pipeline and chunk retrieval
- **Data Models:** [Data Models](./03-DATA-MODELS.md) for MongoDB schema definitions
- **Report Generation:** [Report Generation](./07-REPORT-GENERATION.md) for how report specs are rendered
- **People Intelligence:** [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) for the people analysis pipeline
- **Dashboard & Widgets:** [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) for chart rendering from AI-generated specs
