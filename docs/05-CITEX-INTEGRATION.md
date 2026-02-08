# Citex Integration: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | **Citex Integration** | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Overview

**Citex** is a portable, multi-modal context retrieval runtime built by YENSI Solutions. It is deployed as a Docker instance and serves as the **RAG backbone** for ChiefOps. Citex is a **context provider only** — it does NOT generate answers. It ingests documents, parses them, chunks them, embeds them, indexes them, and returns relevant chunks with citation-grade evidence when queried.

ChiefOps does NOT duplicate any of Citex's capabilities. The division of responsibility is strict:

### What Citex Handles

| Capability | Detail |
|-----------|--------|
| Document ingestion | PDF, DOCX, PPTX, XLSX, HTML, MD, TXT (via Docling parser) |
| Audio/Video ingestion | MP3, MP4, WAV (via adapters, speech-to-text) |
| Parsing & chunking | Section-aware chunking (~600 char chunks with overlap, page/section provenance) |
| Vector search | Via Qdrant with metadata filtering |
| Keyword search | Via MongoDB |
| Hybrid retrieval | Vector + keyword + graph + temporal |
| Graph queries | Via Neo4j (entity relationships, timelines) |
| Temporal queries | Time-based retrieval and filtering |
| Citations | Citation-grade evidence bundles (page, section, bbox, text spans) |
| Project isolation | All data scoped by `project_id` |
| MCP tools | `citex_query` and `citex_store` |
| APIs | REST + WebSocket |
| Custom file types | Adapter pattern for extensibility |

### What ChiefOps Handles

| Capability | Detail |
|-----------|--------|
| Answer generation | Via the AI adapter layer (Claude CLI, Codex CLI, Gemini CLI, Open Router) |
| Conversation memory | Multi-stream memory with compaction (see [Memory System](./04-MEMORY-SYSTEM.md)) |
| People intelligence | Entity resolution, role inference, activity tracking (see [People Intelligence](./09-PEOPLE-INTELLIGENCE.md)) |
| Project analysis | Sprint health, gap detection, backward planning, technical feasibility |
| Report generation | Template-driven report composition and PDF export (see [Report Generation](./07-REPORT-GENERATION.md)) |
| Dashboard & widgets | NL-configurable dashboard with live visualizations (see [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md)) |
| Structured data storage | MongoDB for metrics, people, projects, alerts, widget specs |

### Key Design Principle

Citex is a **black box** to ChiefOps. ChiefOps sends files for ingestion and queries for retrieval. It never directly accesses Citex's internal stores (Qdrant, Neo4j, MinIO). All interaction goes through Citex's REST API.

---

## 2. What Gets Indexed in Citex

Everything that needs to be semantically searchable goes into Citex. Structured data that only needs exact lookups stays in ChiefOps MongoDB.

### 2.1 Google Drive Documents

**ALL** Google Drive documents are indexed in Citex — full content, parsed and searchable.

| File Type | Handling |
|-----------|----------|
| PDF | Full text extraction, page-level provenance |
| DOCX | Full text extraction, section-level provenance |
| PPTX | Slide-by-slide extraction |
| XLSX | Sheet-by-sheet extraction, table structure preserved |
| HTML | Rendered text extraction |
| MD, TXT | Direct text ingestion |

**Metadata tags:** `source: "google_drive"`, `filename`, `file_type`, `upload_date`, `project_id`

### 2.2 Slack Messages

Slack messages are converted to text/markdown files by ChiefOps, then ingested into Citex. One file per channel per time period (e.g., per day or per week depending on volume).

**Metadata tags:**

| Tag | Example |
|-----|---------|
| `source` | `"slack"` |
| `channel` | `"#project-alpha"` |
| `date_range` | `"2025-01-15/2025-01-21"` |
| `participants` | `["sarah", "raj", "anil"]` |
| `project_id` | `"proj_alpha_001"` |

This means the COO can ask "What did the team discuss about the database migration last week?" and Citex will return the relevant Slack conversation chunks with channel and date provenance.

### 2.3 Jira Task Data

Jira tasks are converted to structured text documents by ChiefOps, then ingested into Citex. Each task becomes a text document containing the key, summary, description, status, assignee, comments, and related fields in a human-readable format.

**Metadata tags:**

| Tag | Example |
|-----|---------|
| `source` | `"jira"` |
| `project` | `"ALPHA"` |
| `sprint` | `"Sprint 14"` |
| `assignee` | `"raj.kumar"` |
| `status` | `"In Progress"` |
| `priority` | `"High"` |
| `task_key` | `"ALPHA-142"` |
| `project_id` | `"proj_alpha_001"` |

### 2.4 Session Summaries

Compacted conversation summaries from the memory system are stored in Citex so that old conversation context is semantically searchable. When the memory system compacts a conversation (see [Memory System](./04-MEMORY-SYSTEM.md)), the summary is:

1. Stored in ChiefOps MongoDB (canonical record)
2. Indexed in Citex (for semantic retrieval)

**Metadata tags:** `source: "memory"`, `stream_id`, `session_id`, `compacted_at`, `project_id`

This enables the AI to recall past conversations: "Last time we discussed the database migration, you mentioned wanting to use PostgreSQL instead of MySQL."

### 2.5 COO Corrections as Facts

When the COO corrects a fact (e.g., "Raj is the lead architect, not a junior dev"), the correction is stored as a "fact" document in Citex with high retrieval priority.

**Metadata tags:** `source: "coo_correction"`, `entity_type` (person/project/task), `entity_id`, `correction_date`, `project_id`

This ensures corrections surface in future queries about the corrected entity.

---

## 3. Integration Architecture

### 3.1 System Diagram

```
+------------------------------------------------------------------+
|                        ChiefOps Backend                          |
|                                                                  |
|  +-------------------+    +-------------------+                  |
|  | File Ingestion    |    | AI Adapter Layer  |                  |
|  | Pipeline          |    | (Claude/OR/etc.)  |                  |
|  +--------+----------+    +--------+----------+                  |
|           |                        ^                             |
|           | upload files           | context chunks              |
|           v                        |                             |
|  +--------+------------------------+----------+                  |
|  |              Citex Client                  |                  |
|  |  (async HTTP client, retry, error handling)|                  |
|  +--------+-----------------------------------+                  |
|           |                                                      |
+-----------|------------------------------------------------------+
            | HTTP (REST API)
            v
+------------------------------------------------------------------+
|                     Citex Runtime (Docker)                        |
|                                                                  |
|  +-------------+   +-----------+   +-----------+   +-----------+ |
|  | Citex API   |   | Qdrant    |   | Neo4j     |   | MinIO     | |
|  | :23004      |   | :23005    |   | :23008    |   | :23007    | |
|  +-------------+   +-----------+   +-----------+   +-----------+ |
|  +-------------+   +-----------+                                 |
|  | MongoDB     |   | Redis     |                                 |
|  | :23006      |   | :23009    |                                 |
|  +-------------+   +-----------+                                 |
|                                                                  |
+------------------------------------------------------------------+
```

### 3.2 Integration Flow

```
1. INGESTION FLOW
   ┌──────────┐     ┌──────────────┐     ┌───────────┐
   │ COO      │────>│ ChiefOps     │────>│ Citex     │
   │ Uploads  │     │ Pre-process  │     │ Ingest    │
   │ Files    │     │ + Metadata   │     │ API       │
   └──────────┘     └──────────────┘     └─────┬─────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │ Citex Internal:     │
                                    │ Parse → Chunk →     │
                                    │ Embed → Index       │
                                    │ (Qdrant + Neo4j +   │
                                    │  MongoDB)           │
                                    └─────────────────────┘

2. QUERY FLOW
   ┌──────────┐     ┌──────────────┐     ┌───────────┐
   │ COO      │────>│ ChiefOps     │────>│ Citex     │
   │ Asks     │     │ Build Query  │     │ Query     │
   │ Question │     │ + Filters    │     │ API       │
   └──────────┘     └──────────────┘     └─────┬─────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │ Returns:            │
                                    │ - Relevant chunks   │
                                    │ - Evidence bundles  │
                                    │ - Source metadata    │
                                    └──────────┬──────────┘
                                               │
   ┌──────────┐     ┌──────────────┐           │
   │ COO      │<────│ AI Adapter   │<──────────┘
   │ Sees     │     │ Generates    │  (chunks as context)
   │ Answer   │     │ Answer       │
   └──────────┘     └──────────────┘
```

### 3.3 Project-Level Isolation

Every ChiefOps project maps to exactly one Citex project. All ingestion and queries are scoped by `project_id`.

| ChiefOps Concept | Citex Concept |
|-------------------|---------------|
| Project | `project_id` scope |
| Document upload | `POST /ingest` with `project_id` |
| NL query | `POST /query` with `project_id` filter |
| Cross-project query | Multiple Citex queries, one per project, results merged by ChiefOps |

Cross-project queries (from the main dashboard) are handled by ChiefOps issuing parallel queries to Citex for each relevant project, then merging the results before sending to the AI adapter.

---

## 4. Citex Client Implementation

The Citex client follows the same patterns used across the YENSI platform (httpx async, Pydantic v2, pydantic-settings).

### 4.1 Configuration

```python
# app/integrations/citex/config.py

from pydantic_settings import BaseSettings


class CitexConfig(BaseSettings):
    """Configuration for Citex RAG runtime connection."""

    model_config = {"env_prefix": "CITEX_"}

    host: str = "citex-api"
    port: int = 23004
    protocol: str = "http"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    default_top_k: int = 15
    default_search_type: str = "hybrid"  # hybrid | vector | keyword | graph

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"
```

### 4.2 Response Models

```python
# app/integrations/citex/models.py

from datetime import datetime
from pydantic import BaseModel, Field


class EvidenceBundle(BaseModel):
    """Citation-grade evidence from Citex retrieval."""

    page: int | None = None
    section: str | None = None
    bbox: list[float] | None = None  # [x0, y0, x1, y1] bounding box
    text_span: str | None = None
    source_file: str | None = None
    chunk_index: int | None = None


class QueryChunk(BaseModel):
    """A single retrieved chunk from Citex."""

    text: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
    evidence: EvidenceBundle | None = None
    source: str | None = None
    project_id: str | None = None


class QueryResponse(BaseModel):
    """Response from a Citex query."""

    query: str
    chunks: list[QueryChunk] = Field(default_factory=list)
    total_results: int = 0
    search_type: str = "hybrid"
    query_time_ms: float = 0.0


class IngestResponse(BaseModel):
    """Response from a Citex document ingestion."""

    document_id: str
    filename: str
    project_id: str
    status: str  # "processing" | "completed" | "failed"
    chunks_created: int = 0
    file_type: str | None = None
    message: str | None = None


class IngestStatusResponse(BaseModel):
    """Status of an ongoing ingestion job."""

    document_id: str
    status: str  # "queued" | "processing" | "completed" | "failed"
    progress: float = 0.0  # 0.0 to 1.0
    chunks_created: int = 0
    error: str | None = None
    completed_at: datetime | None = None


class ProjectResponse(BaseModel):
    """Response from Citex project operations."""

    project_id: str
    name: str
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None


class HealthResponse(BaseModel):
    """Citex health check response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str | None = None
    stores: dict = Field(default_factory=dict)
    # e.g., {"mongodb": "ok", "qdrant": "ok", "neo4j": "ok", "minio": "ok", "redis": "ok"}
```

### 4.3 Client Implementation

```python
# app/integrations/citex/client.py

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from app.integrations.citex.config import CitexConfig
from app.integrations.citex.models import (
    HealthResponse,
    IngestResponse,
    IngestStatusResponse,
    ProjectResponse,
    QueryChunk,
    QueryResponse,
)

logger = logging.getLogger(__name__)


class CitexError(Exception):
    """Base exception for Citex client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CitexConnectionError(CitexError):
    """Raised when Citex is unreachable."""
    pass


class CitexIngestionError(CitexError):
    """Raised when document ingestion fails."""
    pass


class CitexQueryError(CitexError):
    """Raised when a query fails."""
    pass


class CitexClient:
    """
    Async client for the Citex RAG runtime.

    All interaction with Citex goes through this client. ChiefOps never
    accesses Citex's internal stores directly.

    Usage:
        config = CitexConfig()
        async with CitexClient(config) as client:
            health = await client.health_check()
            response = await client.query("What is the sprint status?", project_id="proj_001")
    """

    def __init__(self, config: CitexConfig | None = None):
        self.config = config or CitexConfig()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CitexClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout_seconds),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "CitexClient not initialized. Use 'async with CitexClient() as client:'"
            )
        return self._client

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            except httpx.ConnectError as e:
                last_error = CitexConnectionError(
                    f"Cannot connect to Citex at {self.config.base_url}: {e}"
                )
                logger.warning(
                    "Citex connection failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.config.max_retries,
                    e,
                )
            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    raise CitexError(
                        f"Citex request failed: {e.response.text}",
                        status_code=e.response.status_code,
                    )
                last_error = CitexError(
                    f"Citex server error: {e.response.text}",
                    status_code=e.response.status_code,
                )
                logger.warning(
                    "Citex request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.config.max_retries,
                    e,
                )
            except httpx.TimeoutException as e:
                last_error = CitexError(f"Citex request timed out: {e}")
                logger.warning(
                    "Citex request timed out (attempt %d/%d): %s",
                    attempt + 1,
                    self.config.max_retries,
                    e,
                )

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay_seconds * (2 ** attempt)
                await asyncio.sleep(delay)

        raise last_error or CitexError("Citex request failed after all retries")

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthResponse:
        """Check Citex runtime health and store connectivity."""
        try:
            response = await self._request_with_retry("GET", "/health")
            return HealthResponse.model_validate(response.json())
        except CitexConnectionError:
            return HealthResponse(status="unhealthy", stores={})

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------

    async def create_project(
        self,
        project_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectResponse:
        """Create a new Citex project for scoped document storage."""
        payload = {
            "project_id": project_id,
            "name": name,
        }
        if metadata:
            payload["metadata"] = metadata

        response = await self._request_with_retry(
            "POST", "/projects", json=payload
        )
        return ProjectResponse.model_validate(response.json())

    async def get_project(self, project_id: str) -> ProjectResponse:
        """Get project details from Citex."""
        response = await self._request_with_retry(
            "GET", f"/projects/{project_id}"
        )
        return ProjectResponse.model_validate(response.json())

    async def delete_project(self, project_id: str) -> None:
        """
        Delete a Citex project and all its indexed content.

        WARNING: This permanently removes all documents, chunks, vectors,
        and graph data for this project from Citex.
        """
        await self._request_with_retry("DELETE", f"/projects/{project_id}")
        logger.info("Deleted Citex project: %s", project_id)

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------

    async def ingest_document(
        self,
        file_path: Path | str,
        filename: str,
        project_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestResponse:
        """
        Upload a document to Citex for ingestion.

        Citex will parse, chunk, embed, and index the document.
        The response may indicate "processing" if ingestion is async.

        Args:
            file_path: Local path to the file.
            filename: Display name for the document.
            project_id: Citex project to ingest into.
            metadata: Additional metadata tags (source, channel, etc.).

        Returns:
            IngestResponse with document_id and status.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise CitexIngestionError(f"File not found: {file_path}")

        # Build multipart form data
        files = {
            "file": (filename, file_path.open("rb"), "application/octet-stream"),
        }
        data: dict[str, str] = {
            "project_id": project_id,
            "filename": filename,
        }
        if metadata:
            # Citex expects metadata as a JSON string in the form field
            import json
            data["metadata"] = json.dumps(metadata)

        response = await self._request_with_retry(
            "POST",
            "/ingest",
            files=files,
            data=data,
        )
        return IngestResponse.model_validate(response.json())

    async def ingest_text(
        self,
        text: str,
        document_name: str,
        project_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestResponse:
        """
        Ingest raw text content directly into Citex.

        Used for Slack message exports, Jira task documents,
        session summaries, and COO corrections.

        Args:
            text: The text content to ingest.
            document_name: Identifier for this document.
            project_id: Citex project to ingest into.
            metadata: Additional metadata tags.

        Returns:
            IngestResponse with document_id and status.
        """
        payload = {
            "text": text,
            "document_name": document_name,
            "project_id": project_id,
        }
        if metadata:
            payload["metadata"] = metadata

        response = await self._request_with_retry(
            "POST", "/ingest/text", json=payload
        )
        return IngestResponse.model_validate(response.json())

    async def get_ingestion_status(
        self,
        document_id: str,
    ) -> IngestStatusResponse:
        """Check the status of an ongoing ingestion job."""
        response = await self._request_with_retry(
            "GET", f"/ingest/{document_id}/status"
        )
        return IngestStatusResponse.model_validate(response.json())

    async def wait_for_ingestion(
        self,
        document_id: str,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> IngestStatusResponse:
        """
        Poll ingestion status until completion or timeout.

        Args:
            document_id: The document being ingested.
            poll_interval: Seconds between status checks.
            max_wait: Maximum seconds to wait before raising.

        Returns:
            Final IngestStatusResponse.

        Raises:
            CitexIngestionError: If ingestion fails or times out.
        """
        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.get_ingestion_status(document_id)
            if status.status == "completed":
                return status
            if status.status == "failed":
                raise CitexIngestionError(
                    f"Ingestion failed for {document_id}: {status.error}"
                )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise CitexIngestionError(
            f"Ingestion timed out for {document_id} after {max_wait}s"
        )

    # ------------------------------------------------------------------
    # Query / Retrieval
    # ------------------------------------------------------------------

    async def query(
        self,
        query: str,
        project_id: str,
        top_k: int | None = None,
        search_type: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """
        Query Citex for relevant content chunks.

        Args:
            query: Natural language query string.
            project_id: Scope to this project.
            top_k: Maximum chunks to return (default from config).
            search_type: "hybrid" | "vector" | "keyword" | "graph"
            metadata_filter: Filter results by metadata fields
                (e.g., {"source": "slack", "channel": "#project-alpha"}).

        Returns:
            QueryResponse with ranked chunks and evidence.
        """
        payload: dict[str, Any] = {
            "query": query,
            "project_id": project_id,
            "top_k": top_k or self.config.default_top_k,
            "search_type": search_type or self.config.default_search_type,
        }
        if metadata_filter:
            payload["metadata_filter"] = metadata_filter

        response = await self._request_with_retry(
            "POST", "/query", json=payload
        )
        data = response.json()

        chunks = [QueryChunk.model_validate(c) for c in data.get("chunks", [])]
        return QueryResponse(
            query=query,
            chunks=chunks,
            total_results=data.get("total_results", len(chunks)),
            search_type=data.get("search_type", payload["search_type"]),
            query_time_ms=data.get("query_time_ms", 0.0),
        )

    async def get_all_content(
        self,
        project_id: str,
        source: str | None = None,
        limit: int = 1000,
    ) -> list[QueryChunk]:
        """
        Retrieve all indexed content for a project (paginated).

        Useful for full project exports or bulk analysis.

        Args:
            project_id: Scope to this project.
            source: Optional filter by source type ("slack", "jira", "google_drive").
            limit: Maximum documents to return.

        Returns:
            List of all content chunks.
        """
        params: dict[str, Any] = {
            "project_id": project_id,
            "limit": limit,
        }
        if source:
            params["source"] = source

        response = await self._request_with_retry(
            "GET", "/content", params=params
        )
        data = response.json()
        return [QueryChunk.model_validate(c) for c in data.get("chunks", [])]


# ------------------------------------------------------------------
# Singleton / Factory
# ------------------------------------------------------------------

_citex_client: CitexClient | None = None


async def get_citex_client() -> CitexClient:
    """
    Get or create the global CitexClient instance.

    Used as a FastAPI dependency:
        @router.get("/search")
        async def search(client: CitexClient = Depends(get_citex_client)):
            ...
    """
    global _citex_client
    if _citex_client is None:
        _citex_client = CitexClient()
        await _citex_client.__aenter__()
    return _citex_client


async def shutdown_citex_client() -> None:
    """Close the global CitexClient. Call on app shutdown."""
    global _citex_client
    if _citex_client is not None:
        await _citex_client.__aexit__(None, None, None)
        _citex_client = None
```

### 4.4 FastAPI Lifecycle Integration

```python
# app/main.py (relevant excerpt)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.integrations.citex.client import get_citex_client, shutdown_citex_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize Citex client and verify connectivity
    client = await get_citex_client()
    health = await client.health_check()
    if health.status == "unhealthy":
        logger.warning("Citex is not available at startup — running in degraded mode")
    else:
        logger.info("Citex connected: %s", health.stores)

    yield

    # Shutdown: close Citex client
    await shutdown_citex_client()


app = FastAPI(title="ChiefOps API", lifespan=lifespan)
```

---

## 5. Data Ingestion Patterns

### 5.1 Google Drive Documents

Google Drive files are uploaded directly to Citex — Citex handles all parsing internally via its Docling parser.

```python
# app/services/ingestion/drive_ingestion.py

import logging
from pathlib import Path
from typing import Any

from app.integrations.citex.client import CitexClient
from app.integrations.citex.models import IngestResponse

logger = logging.getLogger(__name__)


async def ingest_drive_folder(
    client: CitexClient,
    folder_path: Path,
    project_id: str,
) -> list[IngestResponse]:
    """
    Ingest all files from a Google Drive folder into Citex.

    Supported: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT
    """
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".pptx", ".xlsx",
        ".html", ".htm", ".md", ".txt",
    }
    results: list[IngestResponse] = []

    for file_path in sorted(folder_path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.warning("Skipping unsupported file: %s", file_path.name)
            continue

        metadata: dict[str, Any] = {
            "source": "google_drive",
            "filename": file_path.name,
            "file_type": file_path.suffix.lower().lstrip("."),
            "relative_path": str(file_path.relative_to(folder_path)),
        }

        try:
            response = await client.ingest_document(
                file_path=file_path,
                filename=file_path.name,
                project_id=project_id,
                metadata=metadata,
            )
            results.append(response)
            logger.info(
                "Ingested Drive file: %s → document_id=%s",
                file_path.name,
                response.document_id,
            )
        except Exception as e:
            logger.error("Failed to ingest %s: %s", file_path.name, e)
            results.append(
                IngestResponse(
                    document_id="",
                    filename=file_path.name,
                    project_id=project_id,
                    status="failed",
                    message=str(e),
                )
            )

    return results
```

### 5.2 Slack Messages

Slack messages are pre-processed by ChiefOps into markdown documents, then ingested as text.

```python
# app/services/ingestion/slack_ingestion.py

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.integrations.citex.client import CitexClient
from app.integrations.citex.models import IngestResponse

logger = logging.getLogger(__name__)


def _slack_messages_to_markdown(
    messages: list[dict],
    channel_name: str,
) -> str:
    """Convert a list of Slack messages to a readable markdown document."""
    lines = [f"# Slack Channel: {channel_name}\n"]

    for msg in messages:
        user = msg.get("user", msg.get("username", "unknown"))
        timestamp = msg.get("ts", "")
        text = msg.get("text", "")

        if timestamp:
            try:
                dt = datetime.fromtimestamp(float(timestamp))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                time_str = timestamp
        else:
            time_str = "unknown time"

        lines.append(f"**{user}** ({time_str}):")
        lines.append(f"{text}\n")

        # Include thread replies if present
        if "replies" in msg:
            for reply in msg["replies"]:
                reply_user = reply.get("user", "unknown")
                reply_text = reply.get("text", "")
                lines.append(f"  > **{reply_user}**: {reply_text}")
            lines.append("")

    return "\n".join(lines)


def _extract_participants(messages: list[dict]) -> list[str]:
    """Extract unique participant usernames from messages."""
    participants = set()
    for msg in messages:
        user = msg.get("user", msg.get("username"))
        if user:
            participants.add(user)
    return sorted(participants)


async def ingest_slack_channel(
    client: CitexClient,
    messages: list[dict],
    channel_name: str,
    project_id: str,
    date_range: str | None = None,
) -> IngestResponse:
    """
    Convert Slack messages to markdown and ingest into Citex.

    Args:
        client: Citex client instance.
        messages: List of Slack message dicts.
        channel_name: Channel name (e.g., "#project-alpha").
        project_id: ChiefOps project ID.
        date_range: ISO date range string (e.g., "2025-01-15/2025-01-21").
    """
    markdown = _slack_messages_to_markdown(messages, channel_name)
    participants = _extract_participants(messages)

    metadata: dict[str, Any] = {
        "source": "slack",
        "channel": channel_name,
        "participants": participants,
        "message_count": len(messages),
    }
    if date_range:
        metadata["date_range"] = date_range

    document_name = f"slack_{channel_name}_{date_range or 'all'}"

    return await client.ingest_text(
        text=markdown,
        document_name=document_name,
        project_id=project_id,
        metadata=metadata,
    )
```

### 5.3 Jira Tasks

Each Jira task is converted to a structured text document for semantic searchability.

```python
# app/services/ingestion/jira_ingestion.py

import logging
from typing import Any

from app.integrations.citex.client import CitexClient
from app.integrations.citex.models import IngestResponse

logger = logging.getLogger(__name__)


def _jira_task_to_text(task: dict) -> str:
    """Convert a Jira task dict to a structured text document."""
    lines = [
        f"# {task.get('key', 'UNKNOWN')}: {task.get('summary', 'No summary')}",
        "",
        f"**Status:** {task.get('status', 'Unknown')}",
        f"**Assignee:** {task.get('assignee', 'Unassigned')}",
        f"**Priority:** {task.get('priority', 'None')}",
        f"**Sprint:** {task.get('sprint', 'None')}",
        f"**Story Points:** {task.get('story_points', 'None')}",
        f"**Created:** {task.get('created', 'Unknown')}",
        f"**Updated:** {task.get('updated', 'Unknown')}",
        f"**Due Date:** {task.get('due_date', 'None')}",
        "",
    ]

    if task.get("description"):
        lines.append("## Description")
        lines.append(task["description"])
        lines.append("")

    if task.get("comments"):
        lines.append("## Comments")
        for comment in task["comments"]:
            author = comment.get("author", "Unknown")
            body = comment.get("body", "")
            date = comment.get("created", "")
            lines.append(f"**{author}** ({date}): {body}")
            lines.append("")

    if task.get("labels"):
        lines.append(f"**Labels:** {', '.join(task['labels'])}")

    if task.get("components"):
        lines.append(f"**Components:** {', '.join(task['components'])}")

    return "\n".join(lines)


async def ingest_jira_tasks(
    client: CitexClient,
    tasks: list[dict],
    project_id: str,
) -> list[IngestResponse]:
    """
    Convert Jira tasks to text documents and ingest into Citex.

    Each task becomes a separate document with metadata tags for
    filtered retrieval.
    """
    results: list[IngestResponse] = []

    for task in tasks:
        text = _jira_task_to_text(task)
        task_key = task.get("key", "UNKNOWN")

        metadata: dict[str, Any] = {
            "source": "jira",
            "task_key": task_key,
            "project": task.get("project", ""),
            "sprint": task.get("sprint", ""),
            "assignee": task.get("assignee", ""),
            "status": task.get("status", ""),
            "priority": task.get("priority", ""),
        }

        try:
            response = await client.ingest_text(
                text=text,
                document_name=f"jira_{task_key}",
                project_id=project_id,
                metadata=metadata,
            )
            results.append(response)
        except Exception as e:
            logger.error("Failed to ingest Jira task %s: %s", task_key, e)
            results.append(
                IngestResponse(
                    document_id="",
                    filename=f"jira_{task_key}",
                    project_id=project_id,
                    status="failed",
                    message=str(e),
                )
            )

    return results
```

### 5.4 Session Summaries

Compacted conversation summaries are indexed in Citex for future semantic retrieval.

```python
# app/services/ingestion/memory_ingestion.py

from typing import Any

from app.integrations.citex.client import CitexClient
from app.integrations.citex.models import IngestResponse


async def ingest_session_summary(
    client: CitexClient,
    summary_text: str,
    session_id: str,
    stream_id: str,
    project_id: str,
    compacted_at: str,
) -> IngestResponse:
    """
    Index a compacted session summary in Citex for semantic retrieval.

    Called by the memory compaction service after a conversation
    summary is generated.
    """
    metadata: dict[str, Any] = {
        "source": "memory",
        "session_id": session_id,
        "stream_id": stream_id,
        "compacted_at": compacted_at,
    }

    return await client.ingest_text(
        text=summary_text,
        document_name=f"session_{session_id}_summary",
        project_id=project_id,
        metadata=metadata,
    )


async def ingest_coo_correction(
    client: CitexClient,
    correction_text: str,
    entity_type: str,
    entity_id: str,
    project_id: str,
    correction_date: str,
) -> IngestResponse:
    """
    Index a COO correction as a high-priority fact in Citex.

    Corrections surface prominently in future queries about
    the corrected entity.
    """
    metadata: dict[str, Any] = {
        "source": "coo_correction",
        "entity_type": entity_type,  # "person" | "project" | "task"
        "entity_id": entity_id,
        "correction_date": correction_date,
    }

    return await client.ingest_text(
        text=correction_text,
        document_name=f"correction_{entity_type}_{entity_id}_{correction_date}",
        project_id=project_id,
        metadata=metadata,
    )
```

---

## 6. Query Patterns

### 6.1 Natural Language Query Flow

Every user question follows the same flow through the system:

```
User Question
     │
     ▼
┌─────────────────────────────────┐
│ 1. ChiefOps Query Router        │
│    - Determine project scope    │
│    - Identify query type        │
│    - Build metadata filters     │
└──────────────┬──────────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
┌────────────┐   ┌──────────────┐
│ 2a. Citex  │   │ 2b. MongoDB  │
│ Semantic + │   │ Structured   │
│ Keyword    │   │ Queries      │
│ Search     │   │ (metrics,    │
│            │   │  people,     │
│ Returns:   │   │  projects)   │
│ - chunks   │   │              │
│ - evidence │   │ Returns:     │
│ - scores   │   │ - records    │
└──────┬─────┘   └──────┬───────┘
       │                │
       └────────┬───────┘
                ▼
┌─────────────────────────────────┐
│ 3. Context Assembly              │
│    - Citex chunks (semantic)    │
│    - MongoDB records (structured)│
│    - Memory context (recent)    │
│    - COO corrections (facts)    │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────┐
│ 4. AI Adapter                    │
│    - System prompt + context    │
│    - Generates natural language │
│      answer with citations      │
└──────────────┬──────────────────┘
               ▼
         User sees answer
         with source attribution
```

### 6.2 Hybrid Retrieval Strategy

For each user question, ChiefOps queries **both** Citex and MongoDB. Neither alone is sufficient.

| Source | What It Provides | Example |
|--------|-----------------|---------|
| Citex (semantic search) | Relevant text chunks from all documents, Slack messages, Jira descriptions | "The team discussed switching to PostgreSQL in #backend channel" |
| Citex (keyword search) | Exact matches for names, task keys, technical terms | "ALPHA-142", "Raj Kumar", "database migration" |
| Citex (graph query) | Entity relationships — who works with whom, task dependencies | "Raj → assigned to → ALPHA-142 → blocks → ALPHA-156" |
| MongoDB (structured) | Exact metrics, people records, project summaries, computed scores | Sprint velocity = 12.5 pts/week, completion = 67% |

### 6.3 Query Implementation

```python
# app/services/query/context_builder.py

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.integrations.citex.client import CitexClient
from app.integrations.citex.models import QueryChunk

logger = logging.getLogger(__name__)


@dataclass
class AssembledContext:
    """All context assembled for an AI prompt."""

    citex_chunks: list[QueryChunk] = field(default_factory=list)
    structured_data: dict[str, Any] = field(default_factory=dict)
    memory_context: str = ""
    corrections: list[str] = field(default_factory=list)
    total_token_estimate: int = 0

    def to_prompt_context(self) -> str:
        """Format all context into a single string for the AI prompt."""
        sections = []

        # Citex retrieval results
        if self.citex_chunks:
            sections.append("## Retrieved Context (from documents, messages, tasks)")
            for i, chunk in enumerate(self.citex_chunks, 1):
                source = chunk.metadata.get("source", "unknown")
                source_detail = ""
                if source == "slack":
                    source_detail = f" (Slack: {chunk.metadata.get('channel', '')})"
                elif source == "jira":
                    source_detail = f" (Jira: {chunk.metadata.get('task_key', '')})"
                elif source == "google_drive":
                    source_detail = f" (Drive: {chunk.metadata.get('filename', '')})"
                elif source == "coo_correction":
                    source_detail = " (COO Correction — treat as authoritative)"

                sections.append(
                    f"[{i}]{source_detail} (relevance: {chunk.score:.2f}):\n{chunk.text}"
                )

        # Structured data from MongoDB
        if self.structured_data:
            sections.append("\n## Structured Data (metrics, records)")
            for key, value in self.structured_data.items():
                sections.append(f"- {key}: {value}")

        # Recent conversation memory
        if self.memory_context:
            sections.append(f"\n## Recent Conversation Context\n{self.memory_context}")

        # COO corrections (highest priority)
        if self.corrections:
            sections.append("\n## COO Corrections (authoritative, override other data)")
            for correction in self.corrections:
                sections.append(f"- {correction}")

        context = "\n".join(sections)
        self.total_token_estimate = len(context) // 4  # rough estimate
        return context


async def build_context(
    citex_client: CitexClient,
    query: str,
    project_id: str,
    structured_data: dict[str, Any] | None = None,
    memory_context: str = "",
    source_filter: str | None = None,
) -> AssembledContext:
    """
    Build complete context for an AI prompt by querying Citex
    and assembling all relevant information.

    Args:
        citex_client: Citex client instance.
        query: The user's natural language question.
        project_id: Scope to this project.
        structured_data: Pre-fetched structured data from MongoDB.
        memory_context: Recent conversation context from memory system.
        source_filter: Optional filter to specific source type.

    Returns:
        AssembledContext with all components ready for prompt assembly.
    """
    context = AssembledContext(
        structured_data=structured_data or {},
        memory_context=memory_context,
    )

    # Build metadata filter
    metadata_filter: dict[str, Any] | None = None
    if source_filter:
        metadata_filter = {"source": source_filter}

    # Query Citex with hybrid search and also fetch COO corrections
    # Run both in parallel
    citex_query = citex_client.query(
        query=query,
        project_id=project_id,
        top_k=15,
        search_type="hybrid",
        metadata_filter=metadata_filter,
    )

    corrections_query = citex_client.query(
        query=query,
        project_id=project_id,
        top_k=5,
        search_type="vector",
        metadata_filter={"source": "coo_correction"},
    )

    citex_response, corrections_response = await asyncio.gather(
        citex_query,
        corrections_query,
        return_exceptions=True,
    )

    # Process Citex results
    if isinstance(citex_response, Exception):
        logger.error("Citex query failed: %s", citex_response)
    else:
        context.citex_chunks = citex_response.chunks
        logger.info(
            "Citex returned %d chunks in %.1fms",
            len(citex_response.chunks),
            citex_response.query_time_ms,
        )

    # Process corrections
    if isinstance(corrections_response, Exception):
        logger.error("Corrections query failed: %s", corrections_response)
    else:
        context.corrections = [
            chunk.text for chunk in corrections_response.chunks
            if chunk.score > 0.5  # only high-relevance corrections
        ]

    return context
```

### 6.4 Source-Specific Query Patterns

| Query Type | Citex Search Config | Metadata Filter | Example |
|-----------|-------------------|-----------------|---------|
| General project question | hybrid, top_k=15 | `project_id` only | "How's the sprint going?" |
| Slack-specific | hybrid, top_k=20 | `source: "slack"` | "What did the team discuss about X?" |
| Jira-specific | hybrid, top_k=15 | `source: "jira"` | "What tasks are blocked?" |
| Document search | vector, top_k=10 | `source: "google_drive"` | "What does the architecture doc say about auth?" |
| Person query | hybrid, top_k=15 | None (search across all) | "What has Raj been working on?" |
| Correction lookup | vector, top_k=5 | `source: "coo_correction"` | Internal — always included |
| Cross-project | parallel hybrid per project | `project_id` varies | "Which project is most at risk?" |
| Temporal | hybrid + temporal filter | `date_range` | "What happened last week?" |

---

## 7. Docker Compose Configuration

Citex runs as a set of Docker services alongside ChiefOps. All services use the sequential port allocation starting at 23004.

```yaml
# docker-compose.yml (Citex services section)

services:
  # ------------------------------------------------------------------
  # ChiefOps services (23000-23003)
  # ------------------------------------------------------------------
  frontend:
    build: ./frontend
    ports:
      - "23000:23000"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "23001:23001"
    environment:
      - CITEX_HOST=citex-api
      - CITEX_PORT=23004
      - MONGODB_URI=mongodb://chiefops-mongo:23002
      - REDIS_URL=redis://chiefops-redis:23003
    depends_on:
      - chiefops-mongo
      - chiefops-redis
      - citex-api
    networks:
      - chiefops-net

  chiefops-mongo:
    image: mongo:7
    ports:
      - "23002:27017"
    command: mongod --port 27017
    volumes:
      - chiefops-mongo-data:/data/db
    networks:
      - chiefops-net

  chiefops-redis:
    image: redis:7-alpine
    ports:
      - "23003:6379"
    volumes:
      - chiefops-redis-data:/data
    networks:
      - chiefops-net

  # ------------------------------------------------------------------
  # Citex services (23004-23009)
  # ------------------------------------------------------------------
  citex-api:
    image: yensi/citex:latest
    ports:
      - "23004:23004"
    environment:
      - CITEX_PORT=23004
      - MONGODB_URI=mongodb://citex-mongo:27017
      - QDRANT_HOST=citex-qdrant
      - QDRANT_PORT=6333
      - NEO4J_URI=bolt://citex-neo4j:7687
      - MINIO_ENDPOINT=citex-minio:9000
      - MINIO_ACCESS_KEY=citex
      - MINIO_SECRET_KEY=citex_secret
      - REDIS_URL=redis://citex-redis:6379
    depends_on:
      - citex-mongo
      - citex-qdrant
      - citex-neo4j
      - citex-minio
      - citex-redis
    networks:
      - chiefops-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:23004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  citex-qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "23005:6333"
    volumes:
      - citex-qdrant-data:/qdrant/storage
    networks:
      - chiefops-net

  citex-mongo:
    image: mongo:7
    ports:
      - "23006:27017"
    command: mongod --port 27017
    volumes:
      - citex-mongo-data:/data/db
    networks:
      - chiefops-net

  citex-minio:
    image: minio/minio:latest
    ports:
      - "23007:9000"
    environment:
      - MINIO_ROOT_USER=citex
      - MINIO_ROOT_PASSWORD=citex_secret
    command: server /data
    volumes:
      - citex-minio-data:/data
    networks:
      - chiefops-net

  citex-neo4j:
    image: neo4j:5
    ports:
      - "23008:7474"
      - "23009:7687"
    environment:
      - NEO4J_AUTH=none
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - citex-neo4j-data:/data
    networks:
      - chiefops-net

  citex-redis:
    image: redis:7-alpine
    ports:
      - "23009:6379"
    volumes:
      - citex-redis-data:/data
    networks:
      - chiefops-net

# ------------------------------------------------------------------
# Volumes
# ------------------------------------------------------------------
volumes:
  chiefops-mongo-data:
  chiefops-redis-data:
  citex-qdrant-data:
  citex-mongo-data:
  citex-minio-data:
  citex-neo4j-data:
  citex-redis-data:

# ------------------------------------------------------------------
# Networks
# ------------------------------------------------------------------
networks:
  chiefops-net:
    driver: bridge
```

**Key points:**

- ChiefOps backend connects to `citex-api` via the internal Docker network (`chiefops-net`). No authentication — Citex is an internal service, isolated at the network level.
- External ports (23004-23009) are exposed for development/debugging only. In production, only the ChiefOps frontend (23000) and backend (23001) ports need to be exposed.
- Each service has its own persistent volume so data survives container restarts.
- The `citex-api` healthcheck ensures Docker Compose waits for Citex to be ready before starting ChiefOps backend.

### Port Allocation Summary

| Port | Service | Purpose |
|------|---------|---------|
| 23000 | ChiefOps Frontend | React UI |
| 23001 | ChiefOps Backend | FastAPI |
| 23002 | ChiefOps MongoDB | Application data |
| 23003 | ChiefOps Redis | Cache + queues |
| 23004 | Citex API | RAG runtime |
| 23005 | Citex Qdrant | Vector store |
| 23006 | Citex MongoDB | Document store |
| 23007 | Citex MinIO | Raw file store |
| 23008 | Citex Neo4j (HTTP) | Graph store (browser) |
| 23009 | Citex Neo4j (Bolt) / Citex Redis | Graph store (driver) / Cache |

---

## 8. Error Handling

### 8.1 Citex Unavailable

When Citex is down or unreachable, ChiefOps degrades gracefully rather than failing entirely.

```python
# app/services/query/fallback.py

import logging
from typing import Any

from app.integrations.citex.client import CitexClient, CitexConnectionError
from app.services.query.context_builder import AssembledContext, build_context

logger = logging.getLogger(__name__)


async def query_with_fallback(
    citex_client: CitexClient,
    query: str,
    project_id: str,
    structured_data: dict[str, Any] | None = None,
    memory_context: str = "",
) -> tuple[AssembledContext, bool]:
    """
    Query with graceful fallback when Citex is unavailable.

    Returns:
        Tuple of (context, citex_available).
        When Citex is down, context contains only structured data
        and memory, and citex_available is False.
    """
    try:
        context = await build_context(
            citex_client=citex_client,
            query=query,
            project_id=project_id,
            structured_data=structured_data,
            memory_context=memory_context,
        )
        return context, True

    except CitexConnectionError as e:
        logger.error("Citex unavailable, falling back to structured data only: %s", e)

        # Build context without Citex — structured data + memory only
        fallback_context = AssembledContext(
            citex_chunks=[],  # no semantic search results
            structured_data=structured_data or {},
            memory_context=memory_context,
            corrections=[],
        )
        return fallback_context, False
```

**UI behavior when Citex is down:**

| Component | Behavior |
|-----------|----------|
| Dashboard | Shows cached data, displays amber "Citex Offline" banner |
| NL queries | Answers from structured data only, prefixed with "Note: semantic search is currently unavailable" |
| Ingestion | Queued — files stored locally, ingested when Citex recovers |
| Reports | Generated from cached/structured data with a note about limited context |

### 8.2 Ingestion Failure

```python
# app/services/ingestion/retry.py

import asyncio
import logging
from typing import Any

from app.integrations.citex.client import CitexClient, CitexIngestionError
from app.integrations.citex.models import IngestResponse

logger = logging.getLogger(__name__)


async def ingest_with_retry(
    client: CitexClient,
    ingest_fn,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    **kwargs: Any,
) -> IngestResponse:
    """
    Retry wrapper for document ingestion.

    Handles transient failures (network issues, Citex overloaded)
    with exponential backoff. Permanent failures (unsupported format,
    corrupted file) are not retried.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = await ingest_fn(client, **kwargs)
            if response.status == "failed":
                raise CitexIngestionError(
                    f"Ingestion failed: {response.message}"
                )
            return response
        except CitexIngestionError as e:
            # Check if this is a permanent failure
            if "unsupported" in str(e).lower() or "corrupted" in str(e).lower():
                logger.error("Permanent ingestion failure (not retrying): %s", e)
                raise
            last_error = e
            logger.warning(
                "Ingestion attempt %d/%d failed: %s",
                attempt + 1,
                max_retries,
                e,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "Ingestion attempt %d/%d failed: %s",
                attempt + 1,
                max_retries,
                e,
            )

        if attempt < max_retries - 1:
            delay = retry_delay * (2 ** attempt)
            logger.info("Retrying ingestion in %.1f seconds...", delay)
            await asyncio.sleep(delay)

    raise CitexIngestionError(
        f"Ingestion failed after {max_retries} attempts: {last_error}"
    )
```

### 8.3 Query Timeout

```python
# In the CitexClient.query method, timeout is handled by httpx.
# Additional application-level timeout:

async def query_with_timeout(
    citex_client: CitexClient,
    query: str,
    project_id: str,
    timeout_seconds: float = 10.0,
    **kwargs,
):
    """Query Citex with an application-level timeout."""
    try:
        return await asyncio.wait_for(
            citex_client.query(query=query, project_id=project_id, **kwargs),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Citex query timed out after %.1fs, returning empty results",
            timeout_seconds,
        )
        return QueryResponse(
            query=query,
            chunks=[],
            total_results=0,
            search_type="timeout_fallback",
        )
```

### 8.4 Error Summary

| Failure Mode | Detection | Response | User Impact |
|-------------|-----------|----------|-------------|
| Citex unreachable | `CitexConnectionError` | Use structured data only | Amber banner, limited search |
| Ingestion failed (transient) | Retry with backoff | Auto-retry up to 3 times | Delayed ingestion, progress bar pauses |
| Ingestion failed (permanent) | Unsupported/corrupted file | Report to user | Error toast with filename and reason |
| Query timeout | `asyncio.TimeoutError` | Return empty Citex results | Answer from structured data only |
| Citex degraded (partial stores) | Health check `status: "degraded"` | Continue with available stores | Possible reduced quality |

---

## 9. Performance Considerations

### 9.1 Retrieval Performance

| Metric | Target | How Achieved |
|--------|--------|-------------|
| Typical query latency | < 300ms | Qdrant in-memory vectors, project_id filtering narrows search space |
| Complex hybrid query | < 500ms | Parallel vector + keyword + graph execution inside Citex |
| Ingestion throughput | ~10 docs/minute | Async ingestion queue, Docling parser |
| Large PDF (200 pages) | < 2 minutes | Streamed parsing, chunked processing |

### 9.2 Caching Strategy

```python
# app/services/cache/citex_cache.py

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from app.integrations.citex.models import QueryResponse

logger = logging.getLogger(__name__)


class CitexQueryCache:
    """
    Cache for Citex query results.

    Caches are scoped by project_id and invalidated when new
    data is ingested into the project.
    """

    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 300):
        self.redis = redis_client
        self.ttl = ttl_seconds  # 5 minute default TTL

    def _cache_key(
        self,
        query: str,
        project_id: str,
        search_type: str,
        metadata_filter: dict | None,
    ) -> str:
        """Generate a deterministic cache key."""
        key_data = {
            "query": query,
            "project_id": project_id,
            "search_type": search_type,
            "metadata_filter": metadata_filter or {},
        }
        key_hash = hashlib.sha256(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()[:16]
        return f"citex:query:{project_id}:{key_hash}"

    async def get(
        self,
        query: str,
        project_id: str,
        search_type: str = "hybrid",
        metadata_filter: dict | None = None,
    ) -> QueryResponse | None:
        """Get cached query result if available."""
        key = self._cache_key(query, project_id, search_type, metadata_filter)
        cached = await self.redis.get(key)
        if cached:
            logger.debug("Cache hit for query: %s", query[:50])
            return QueryResponse.model_validate_json(cached)
        return None

    async def set(
        self,
        query: str,
        project_id: str,
        response: QueryResponse,
        search_type: str = "hybrid",
        metadata_filter: dict | None = None,
    ) -> None:
        """Cache a query result."""
        key = self._cache_key(query, project_id, search_type, metadata_filter)
        await self.redis.setex(
            key,
            self.ttl,
            response.model_dump_json(),
        )

    async def invalidate_project(self, project_id: str) -> None:
        """
        Invalidate all cached queries for a project.

        Called after new data is ingested into the project.
        """
        pattern = f"citex:query:{project_id}:*"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        if deleted > 0:
            logger.info(
                "Invalidated %d cached queries for project %s",
                deleted,
                project_id,
            )
```

### 9.3 Token Usage Optimization

Citex chunks are ~600 characters each. With a default `top_k=15`, that is approximately 9,000 characters (~2,250 tokens) of retrieval context per query. Combined with structured data and memory context, total context per query stays within 7,000-17,000 tokens — well within the AI adapter's context window.

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Default `top_k` | 15 | Good recall without excessive tokens |
| Max `top_k` | 20 | Hard limit to prevent token overflow |
| Chunk size (Citex) | ~600 chars | Citex default, good granularity |
| Cache TTL | 5 minutes | Fresh enough for interactive use |
| Metadata filtering | Always use `project_id` | Narrows search space significantly |
| Source filtering | When query type is clear | Reduces noise (e.g., Jira-only for task queries) |

### 9.4 Scaling Notes

For Step Zero (single user, single tenant), Citex performance is not a bottleneck. The default configuration handles thousands of documents and sub-second queries. Future phases may require:

- **Phase 2+:** Qdrant collection sharding for very large document sets
- **Phase 3+:** Citex horizontal scaling (multiple API instances behind a load balancer)
- **Phase 3+:** Separate Citex instances per tenant for multi-tenant isolation

These changes happen at the Citex infrastructure level and do not affect the ChiefOps integration code — the client API remains the same.

---

## Related Documents

- **Architecture:** [Architecture](./02-ARCHITECTURE.md) — overall system design
- **Data Models:** [Data Models](./03-DATA-MODELS.md) — MongoDB schema for ChiefOps structured data
- **Memory System:** [Memory System](./04-MEMORY-SYSTEM.md) — conversation memory and compaction
- **AI Layer:** [AI Layer](./06-AI-LAYER.md) — how retrieved context is used for answer generation
- **File Ingestion:** [File Ingestion](./08-FILE-INGESTION.md) — end-to-end ingestion pipeline
- **People Intelligence:** [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) — entity resolution from ingested data
- **Report Generation:** [Report Generation](./07-REPORT-GENERATION.md) — how reports use Citex context
