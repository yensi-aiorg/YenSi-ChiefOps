# Architecture Document: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | **Architecture** | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. High-Level System Diagram

```
+============================================================================+
|                          ChiefOps Step Zero                                |
|                     Docker Compose Environment                             |
+============================================================================+
|                                                                            |
|  +----------------------------------------------------------------------+  |
|  |                    FRONTEND  :23000                                   |  |
|  |              React 19 / Vite / TypeScript (strict)                   |  |
|  |              Tailwind CSS / Zustand / Axios                          |  |
|  |                                                                      |  |
|  |  +------------------+  +------------------+  +--------------------+  |  |
|  |  |  Main Dashboard  |  |  Project Dashboard|  | Custom Dashboard  |  |  |
|  |  |  - Health Score   |  |  - Gantt Timeline |  | - NL-created     |  |  |
|  |  |  - Alert Banner   |  |  - People Grid   |  |   widgets         |  |  |
|  |  |  - Briefing Panel |  |  - Completion %  |  | - Persisted per   |  |  |
|  |  |  - Activity Feed  |  |  - Risk Flags    |  |   project         |  |  |
|  |  |  - Team Overview  |  |  - Milestones    |  | - Auto-refresh    |  |  |
|  |  +------------------+  +------------------+  +--------------------+  |  |
|  |                                                                      |  |
|  |  +------------------------------------------------------------------+|  |
|  |  |              NL Query Interface                                   ||  |
|  |  |  +----------------------------------------------------+         ||  |
|  |  |  | [Search bar — top of every page]                    |         ||  |
|  |  |  +----------------------------------------------------+         ||  |
|  |  |  +----------------------------------------------------+         ||  |
|  |  |  | [Expandable Chat Sidebar]                           |         ||  |
|  |  |  | - Context-aware (scoped to current project)         |         ||  |
|  |  |  | - Follow-up support                                 |         ||  |
|  |  |  | - Inline charts via echarts-for-react               |         ||  |
|  |  |  | - Report trigger + preview                          |         ||  |
|  |  |  | - Widget management commands                        |         ||  |
|  |  |  +----------------------------------------------------+         ||  |
|  |  +------------------------------------------------------------------+|  |
|  |                                                                      |  |
|  |  +------------------------------------------------------------------+|  |
|  |  |              Report Preview Panel                                 ||  |
|  |  |  - Rich HTML preview with live ECharts                           ||  |
|  |  |  - NL editing ("Add a section on hiring")                        ||  |
|  |  |  - Export to PDF button                                          ||  |
|  |  +------------------------------------------------------------------+|  |
|  |                                                                      |  |
|  |  +------------------------------------------------------------------+|  |
|  |  |              Dynamic Widget Renderer                              ||  |
|  |  |  - Reads widget_spec JSON from API                               ||  |
|  |  |  - Renders: bar, line, pie, Gantt, table, KPI card,             ||  |
|  |  |    summary text, person grid, timeline, activity feed            ||  |
|  |  |  - echarts-for-react for all chart types                         ||  |
|  |  +------------------------------------------------------------------+|  |
|  +----------------------------------------------------------------------+  |
|            |                                                               |
|            | HTTP (REST API) + WebSocket (real-time updates)                |
|            v                                                               |
|  +----------------------------------------------------------------------+  |
|  |                    BACKEND  :23001                                    |  |
|  |              Python 3.11+ / FastAPI / Pydantic v2                    |  |
|  |              Async throughout (Motor, httpx, aiofiles)               |  |
|  |                                                                      |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |  |       REST API Layer        |  |     File Ingestion Pipeline   |  |  |
|  |  |  - OpenAPI auto-docs        |  |  +-------------------------+  |  |  |
|  |  |  - /api/v1/query            |  |  | Slack Parser            |  |  |  |
|  |  |  - /api/v1/ingest           |  |  | - Admin Export ZIP      |  |  |  |
|  |  |  - /api/v1/projects         |  |  | - API Extract JSON      |  |  |  |
|  |  |  - /api/v1/people           |  |  +-------------------------+  |  |  |
|  |  |  - /api/v1/reports          |  |  +-------------------------+  |  |  |
|  |  |  - /api/v1/widgets          |  |  | Jira Parser             |  |  |  |
|  |  |  - /api/v1/alerts           |  |  | - CSV export format     |  |  |  |
|  |  |  - /api/v1/briefings        |  |  +-------------------------+  |  |  |
|  |  |  - /api/v1/health           |  |  +-------------------------+  |  |  |
|  |  |  - /api/v1/dashboards       |  |  | Drive Processor         |  |  |  |
|  |  +-----------------------------+  |  | - PDF, DOCX, PPTX, etc. |  |  |  |
|  |                                   |  | - Routes to Citex       |  |  |  |
|  |                                   |  +-------------------------+  |  |  |
|  |                                   +-------------------------------+  |  |
|  |                                                                      |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |  |       AI Service            |  |  People Intelligence Engine  |  |  |
|  |  |  (Adapter Pattern)          |  |  - Identity resolution       |  |  |
|  |  |  +------------------+       |  |  - Role inference            |  |  |
|  |  |  | CLIAdapter (dev) |       |  |  - Task-person mapping       |  |  |
|  |  |  | - Claude CLI     |       |  |  - Activity tracking         |  |  |
|  |  |  | - Codex CLI      |       |  |  - COO corrections           |  |  |
|  |  |  | - Gemini CLI     |       |  +-------------------------------+  |  |
|  |  |  +------------------+       |                                     |  |
|  |  |  +------------------+       |  +-------------------------------+  |  |
|  |  |  | OpenRouterAdapter|       |  |  Project Analysis Engine     |  |  |
|  |  |  | (prod)           |       |  |  - Project identification     |  |  |
|  |  |  +------------------+       |  |  - Timeline construction      |  |  |
|  |  |  Config-driven via          |  |  - Completion estimation      |  |  |
|  |  |  AI_ADAPTER env var         |  |  - Risk detection             |  |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |                                                                      |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |  | Technical Feasibility       |  |  Report Generator            |  |  |
|  |  | Advisor                     |  |  - Jinja2 HTML templates     |  |  |
|  |  | - Backward planning         |  |  - 7+ report types           |  |  |
|  |  | - Missing task detection    |  |  - WeasyPrint HTML->PDF      |  |  |
|  |  | - Capacity estimation       |  |  - pyecharts for PDF charts  |  |  |
|  |  | - Lead time analysis        |  |  - Version history           |  |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |                                                                      |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |  |       Memory Manager        |  |     Alert Engine             |  |  |
|  |  |  - Hard Facts (immutable)   |  |  - NL-defined thresholds     |  |  |
|  |  |  - Compacted Summary        |  |  - Re-evaluated per extract  |  |  |
|  |  |  - Recent Turns (last 10)   |  |  - Dashboard banner display  |  |  |
|  |  |  - Per-project streams      |  |  - Sprint, communication,   |  |  |
|  |  |  - Global stream            |  |    timeline, capacity types  |  |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |                                                                      |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |  |       Widget Manager        |  |     Briefing Generator       |  |  |
|  |  |  - CRUD widget_spec JSON    |  |  - Post-extract auto-gen     |  |  |
|  |  |  - Data query re-execution  |  |  - Highlights / lowlights    |  |  |
|  |  |  - AI-driven placement      |  |  - Risk flags                |  |  |
|  |  |  - Per-project persistence  |  |  - Delta briefings           |  |  |
|  |  +-----------------------------+  +-------------------------------+  |  |
|  |                                                                      |  |
|  |  +------------------------------------------------------------------+|  |
|  |  |       Chart Renderer (Server-Side for PDF)                        ||  |
|  |  |  - pyecharts for static SVG/PNG generation                       ||  |
|  |  |  - Mirrors echarts-for-react chart specs                         ||  |
|  |  |  - Embedded into Jinja2 report templates                         ||  |
|  |  +------------------------------------------------------------------+|  |
|  +----------------------------------------------------------------------+  |
|            |                    |                     |                     |
|            v                    v                     v                     |
|  +------------------+  +-----------------+  +------------------------+     |
|  |   MongoDB :23002 |  |  Redis :23003   |  |   Citex RAG System     |     |
|  |  (Main App DB)   |  | (Cache/Pub-Sub) |  |   :23004 - :23009      |     |
|  |                  |  |                 |  |                        |     |
|  | Collections:     |  | - Query cache   |  | :23004 Citex API       |     |
|  | - slack_messages  |  | - Session store |  | :23005 Qdrant (vectors)|     |
|  | - jira_tasks      |  | - Pub/Sub for   |  | :23006 MongoDB (docs)  |     |
|  | - drive_documents |  |   real-time UI  |  | :23007 MinIO (files)   |     |
|  | - people          |  |   updates       |  | :23008 Neo4j (graph)   |     |
|  | - projects        |  | - Rate limiting |  | :23009 Redis (cache)   |     |
|  | - conversations   |  | - Ingestion job |  |                        |     |
|  | - memory_facts    |  |   status        |  | Capabilities:          |     |
|  | - memory_summaries|  +-----------------+  | - Semantic search      |     |
|  | - widget_specs    |                       | - Document chunking    |     |
|  | - report_specs    |                       | - Vector embeddings    |     |
|  | - report_history  |                       | - Graph relationships  |     |
|  | - alerts          |                       | - File storage         |     |
|  | - briefings       |                       +------------------------+     |
|  | - health_scores   |                                                     |
|  | - ingestion_jobs  |                                                     |
|  | - analysis_results|                                                     |
|  | - audit_log       |                                                     |
|  +------------------+                                                      |
+============================================================================+
```

---

## 2. Container Topology

All services are managed via a single `docker-compose.yml`. Every container uses a custom, sequential port starting at 23000 to avoid conflicts with other local services.

### 2.1 Service Definitions

| # | Service Name | Image / Build | Port | Role | Dependencies | Volumes |
|---|-------------|--------------|------|------|-------------|---------|
| 1 | `chiefops-frontend` | Build: `./frontend` (Node 20, Vite dev server) | 23000 | React 19 SPA. Vite dev server with HMR. Proxies `/api` to backend. | `chiefops-backend` | `./frontend/src` (HMR mount) |
| 2 | `chiefops-backend` | Build: `./backend` (Python 3.11-slim) | 23001 | FastAPI application server. All business logic, AI integration, ingestion, report generation. | `chiefops-mongo`, `chiefops-redis`, `citex-api` | `./backend/app` (HMR mount), `uploads:/app/uploads`, `exports:/app/exports` |
| 3 | `chiefops-mongo` | `mongo:7` | 23002 | Primary application database. Stores all structured data, conversations, memory, widget specs, reports, alerts, audit logs. | None | `mongo-data:/data/db` |
| 4 | `chiefops-redis` | `redis:7-alpine` | 23003 | Caching layer and real-time pub/sub. Query result caching, ingestion job status, WebSocket event bus. | None | `redis-data:/data` |
| 5 | `citex-api` | Build or image: Citex API service | 23004 | RAG gateway. Exposes REST endpoints for document ingestion, semantic search, and chunk retrieval. | `citex-qdrant`, `citex-mongo`, `citex-minio`, `citex-neo4j`, `citex-redis` | None |
| 6 | `citex-qdrant` | `qdrant/qdrant:latest` | 23005 | Vector database. Stores document chunk embeddings for semantic similarity search. | None | `qdrant-data:/qdrant/storage` |
| 7 | `citex-mongo` | `mongo:7` | 23006 | Citex document store. Stores raw chunks, metadata, and document records for Citex. | None | `citex-mongo-data:/data/db` |
| 8 | `citex-minio` | `minio/minio:latest` | 23007 | Object storage. Stores original uploaded files (PDFs, DOCX, etc.) for Citex processing. | None | `minio-data:/data` |
| 9 | `citex-neo4j` | `neo4j:5-community` | 23008 | Graph database. Stores entity relationships, document-chunk-entity graphs for Citex. | None | `neo4j-data:/data` |
| 10 | `citex-redis` | `redis:7-alpine` | 23009 | Citex internal cache. Caching layer for Citex operations. | None | `citex-redis-data:/data` |

### 2.2 Docker Compose Structure

```yaml
# docker-compose.yml (structural overview)
version: "3.9"

services:
  # ── Application Layer ──────────────────────────────────
  chiefops-frontend:
    build: ./frontend
    ports: ["23000:23000"]
    depends_on: [chiefops-backend]
    volumes: ["./frontend/src:/app/src"]            # HMR
    environment:
      VITE_API_URL: http://chiefops-backend:23001

  chiefops-backend:
    build: ./backend
    ports: ["23001:23001"]
    depends_on:
      chiefops-mongo:  { condition: service_healthy }
      chiefops-redis:  { condition: service_healthy }
      citex-api:       { condition: service_started }
    volumes:
      - ./backend/app:/app/app                      # HMR
      - uploads:/app/uploads
      - exports:/app/exports
    environment:
      MONGO_URI: mongodb://chiefops-mongo:27017
      REDIS_URL: redis://chiefops-redis:6379
      CITEX_API_URL: http://citex-api:8000
      AI_ADAPTER: cli                               # cli | openrouter
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
      LOG_LEVEL: INFO

  # ── Data Layer ─────────────────────────────────────────
  chiefops-mongo:
    image: mongo:7
    ports: ["23002:27017"]
    volumes: ["mongo-data:/data/db"]
    healthcheck:
      test: mongosh --eval "db.adminCommand('ping')"

  chiefops-redis:
    image: redis:7-alpine
    ports: ["23003:6379"]
    volumes: ["redis-data:/data"]
    healthcheck:
      test: redis-cli ping

  # ── Citex RAG System ───────────────────────────────────
  citex-api:
    # Citex service definition (external system)
    ports: ["23004:23004"]
    depends_on: [citex-qdrant, citex-mongo, citex-minio, citex-neo4j, citex-redis]

  citex-qdrant:
    image: qdrant/qdrant:latest
    ports: ["23005:6333"]
    volumes: ["qdrant-data:/qdrant/storage"]

  citex-mongo:
    image: mongo:7
    ports: ["23006:27017"]
    volumes: ["citex-mongo-data:/data/db"]

  citex-minio:
    image: minio/minio:latest
    ports: ["23007:9000"]
    volumes: ["minio-data:/data"]
    command: server /data

  citex-neo4j:
    image: neo4j:5-community
    ports: ["23008:7687"]
    volumes: ["neo4j-data:/data"]
    environment:
      NEO4J_AUTH: none

  citex-redis:
    image: redis:7-alpine
    ports: ["23009:6379"]
    volumes: ["citex-redis-data:/data"]

volumes:
  mongo-data:
  redis-data:
  qdrant-data:
  citex-mongo-data:
  minio-data:
  neo4j-data:
  citex-redis-data:
  uploads:
  exports:
```

### 2.3 Network Topology

All containers share a single Docker bridge network (`chiefops-net`). Inter-service communication uses Docker DNS (service names resolve to container IPs). Only the frontend port (23000) needs to be exposed externally in production; all other ports are exposed for local development convenience.

```
chiefops-net (bridge)
  |
  +-- chiefops-frontend  (23000)  ──> chiefops-backend (23001)
  |
  +-- chiefops-backend   (23001)  ──> chiefops-mongo   (23002)
  |                                ──> chiefops-redis   (23003)
  |                                ──> citex-api        (23004)
  |
  +-- chiefops-mongo     (23002)
  +-- chiefops-redis     (23003)
  |
  +-- citex-api          (23004)  ──> citex-qdrant     (23005)
  |                                ──> citex-mongo      (23006)
  |                                ──> citex-minio      (23007)
  |                                ──> citex-neo4j      (23008)
  |                                ──> citex-redis      (23009)
  |
  +-- citex-qdrant       (23005)
  +-- citex-mongo        (23006)
  +-- citex-minio        (23007)
  +-- citex-neo4j        (23008)
  +-- citex-redis        (23009)
```

---

## 3. Request Flow -- NL Query

This is the primary interaction flow. The COO types a natural-language question and receives an AI-powered response with optional inline charts.

```
 COO                   Frontend              Backend               Memory        Citex       MongoDB      AI Adapter
  |                       |                     |                    |             |            |             |
  |  1. Types question    |                     |                    |             |            |             |
  |  "How is Project      |                     |                    |             |            |             |
  |   Alpha doing?"       |                     |                    |             |            |             |
  |---------------------->|                     |                    |             |            |             |
  |                       |  2. POST /api/v1/   |                    |             |            |             |
  |                       |  query              |                    |             |            |             |
  |                       |  { message,         |                    |             |            |             |
  |                       |    project_id,      |                    |             |            |             |
  |                       |    conversation_id } |                    |             |            |             |
  |                       |-------------------->|                    |             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 3. Load memory     |             |            |             |
  |                       |                     | context            |             |            |             |
  |                       |                     |------------------->|             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | <-- hard_facts     |             |            |             |
  |                       |                     | <-- compacted_     |             |            |             |
  |                       |                     |     summary        |             |            |             |
  |                       |                     | <-- recent_turns   |             |            |             |
  |                       |                     |     (last 10)      |             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 4. Semantic search |             |            |             |
  |                       |                     | for relevant       |             |            |             |
  |                       |                     | chunks             |             |            |             |
  |                       |                     |------------------------------>  |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | <-- ranked chunks  |             |            |             |
  |                       |                     |    (Slack msgs,    |             |            |             |
  |                       |                     |     Jira tasks,    |             |            |             |
  |                       |                     |     Drive docs)    |             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 5. Load structured |             |            |             |
  |                       |                     | data from MongoDB  |             |            |             |
  |                       |                     |---------------------------------------------->|             |
  |                       |                     |                    |             |            |             |
  |                       |                     | <-- project record |             |            |             |
  |                       |                     | <-- people records |             |            |             |
  |                       |                     | <-- analysis data  |             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 6. Assemble prompt |             |            |             |
  |                       |                     | [system_prompt +   |             |            |             |
  |                       |                     |  hard_facts +      |             |            |             |
  |                       |                     |  compacted_summary |             |            |             |
  |                       |                     |  + recent_turns +  |             |            |             |
  |                       |                     |  RAG_chunks +      |             |            |             |
  |                       |                     |  structured_data + |             |            |             |
  |                       |                     |  user_question]    |             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 7. Call AI adapter |             |            |             |
  |                       |                     |---------------------------------------------------------------->|
  |                       |                     |                    |             |            |             |
  |                       |                     | <-- AI response    |             |            |             |
  |                       |                     |     { text,        |             |            |             |
  |                       |                     |       chart_specs?,|             |            |             |
  |                       |                     |       corrections?,|             |            |             |
  |                       |                     |       sources }    |             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 8. Update memory   |             |            |             |
  |                       |                     | - Store turn       |             |            |             |
  |                       |                     | - Extract facts    |             |            |             |
  |                       |                     | - Detect           |             |            |             |
  |                       |                     |   corrections      |             |            |             |
  |                       |                     | - Compact if       |             |            |             |
  |                       |                     |   needed           |             |            |             |
  |                       |                     |------------------->|             |            |             |
  |                       |                     |                    |             |            |             |
  |                       |                     | 9. Log audit trail |             |            |             |
  |                       |                     | (chunks sent,      |             |            |             |
  |                       |                     |  sources used)     |             |            |             |
  |                       |                     |---------------------------------------------->|             |
  |                       |                     |                    |             |            |             |
  |                       | 10. Return response |                    |             |            |             |
  |                       | { text, charts,     |                    |             |            |             |
  |                       |   sources }         |                    |             |            |             |
  |                       |<--------------------|                    |             |            |             |
  |                       |                     |                    |             |            |             |
  |  11. Render response  |                     |                    |             |            |             |
  |  - Markdown text      |                     |                    |             |            |             |
  |  - Inline ECharts     |                     |                    |             |            |             |
  |    (if chart_specs)   |                     |                    |             |            |             |
  |  - Source indicators  |                     |                    |             |            |             |
  |<----------------------|                     |                    |             |            |             |
```

### 3.1 Prompt Assembly Detail

The backend assembles the prompt in a structured format before sending to the AI adapter. The total context window budget is managed to stay within model limits (typically 100K-200K tokens depending on the model).

```
+----------------------------------------------------------+
|                    PROMPT STRUCTURE                        |
+----------------------------------------------------------+
| SECTION 1: System Prompt (~500 tokens)                    |
|   - Role: "You are ChiefOps, an AI COO assistant..."     |
|   - Output format instructions                            |
|   - Chart spec format (JSON)                              |
|   - Correction detection instructions                     |
+----------------------------------------------------------+
| SECTION 2: Hard Facts (~1-5K tokens)                      |
|   - COO corrections that override all other data          |
|   - "Raj is the lead architect, NOT a junior dev"         |
|   - Immutable; never compacted; always included           |
+----------------------------------------------------------+
| SECTION 3: Compacted Summary (~2-8K tokens)               |
|   - Progressive summary of all prior conversation         |
|   - Updated after every 10 turns via AI compaction        |
|   - Contains key decisions, context, ongoing threads      |
+----------------------------------------------------------+
| SECTION 4: Recent Turns (~3-10K tokens)                   |
|   - Last 10 raw conversation turns (user + assistant)     |
|   - Provides immediate conversational context             |
+----------------------------------------------------------+
| SECTION 5: RAG Chunks (~5-15K tokens)                     |
|   - Semantically relevant chunks from Citex               |
|   - Slack messages, Jira task descriptions, Drive docs    |
|   - Ranked by relevance score                             |
|   - PII-redacted before inclusion                         |
+----------------------------------------------------------+
| SECTION 6: Structured Data (~1-5K tokens)                 |
|   - Relevant MongoDB records (project, people, tasks)     |
|   - Pre-formatted as concise JSON or markdown             |
+----------------------------------------------------------+
| SECTION 7: User Question                                  |
|   - The current message from the COO                      |
+----------------------------------------------------------+
| TOTAL: ~12-44K tokens typical, max ~50K tokens            |
+----------------------------------------------------------+
```

### 3.2 Response Parsing

The AI adapter returns a structured response. The backend parses it to extract:

1. **Text content** -- Markdown-formatted response text.
2. **Chart specifications** -- Optional JSON objects describing charts to render (type, data, options). These are ECharts option objects.
3. **Corrections detected** -- If the AI detects the COO correcting a fact, it flags it for the Memory Manager to store as a Hard Fact.
4. **Data sources** -- Which chunks/records were used, for the audit trail and the "data scope" indicator in the UI.

---

## 4. Request Flow -- File Ingestion

The COO uploads data files (Slack ZIP, Jira CSV, Drive folder) and the system processes them through a multi-stage pipeline.

```
 COO              Frontend            Backend                 MongoDB         Citex           AI Adapter
  |                  |                   |                       |               |                |
  | 1. Drag-drop     |                   |                       |               |                |
  |  files onto      |                   |                       |               |                |
  |  upload zone     |                   |                       |               |                |
  |----------------->|                   |                       |               |                |
  |                  |                   |                       |               |                |
  |                  | 2. POST /api/v1/  |                       |               |                |
  |                  | ingest            |                       |               |                |
  |                  | (multipart/form)  |                       |               |                |
  |                  |------------------>|                       |               |                |
  |                  |                   |                       |               |                |
  |                  |                   | 3. Create ingestion   |               |                |
  |                  |                   | job record            |               |                |
  |                  |                   |---------------------->|               |                |
  |                  |                   |                       |               |                |
  |                  | <-- 202 Accepted  |                       |               |                |
  |                  |    { job_id }     |                       |               |                |
  |                  |<------------------|                       |               |                |
  |                  |                   |                       |               |                |
  |  Progress via    |                   |                       |               |                |
  |  WebSocket/      |   (ASYNC PIPELINE BEGINS)                |               |                |
  |  polling         |                   |                       |               |                |
  |                  |                   | 4. Detect file types  |               |                |
  |                  |                   | +---------+           |               |                |
  |                  |                   | | .zip    |-> Slack   |               |                |
  |                  |                   | | .json   |   Parser  |               |                |
  |                  |                   | | .csv    |-> Jira    |               |                |
  |                  |                   | |         |   Parser  |               |                |
  |                  |                   | | .pdf    |-> Drive   |               |                |
  |                  |                   | | .docx   |   Proc.   |               |                |
  |                  |                   | | .pptx   |           |               |                |
  |                  |                   | | .xlsx   |           |               |                |
  |                  |                   | | etc.    |           |               |                |
  |                  |                   | +---------+           |               |                |
  |                  |                   |                       |               |                |
  |                  |                   | 5A. SLACK PARSER      |               |                |
  |                  |                   | - Unzip archive       |               |                |
  |                  |                   | - Parse channel JSON  |               |                |
  |                  |                   | - Extract messages,   |               |                |
  |                  |                   |   threads, reactions  |               |                |
  |                  |                   | - Content hash check  |               |                |
  |                  |                   |   (skip duplicates)   |               |                |
  |                  |                   | - Normalize to schema |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       |  slack_messages|                |
  |                  |                   |                       |  collection)  |                |
  |                  |                   | - Send to Citex for   |               |                |
  |                  |                   |   semantic indexing   |               |                |
  |                  |                   |-------------------------------------->|                |
  |                  |                   |                       |               |                |
  |                  |                   | 5B. JIRA PARSER       |               |                |
  |                  |                   | - Parse CSV rows      |               |                |
  |                  |                   | - Map columns to      |               |                |
  |                  |                   |   schema fields       |               |                |
  |                  |                   | - Content hash check  |               |                |
  |                  |                   | - Normalize to schema |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       |  jira_tasks   |                |
  |                  |                   |                       |  collection)  |                |
  |                  |                   | - Send to Citex       |               |                |
  |                  |                   |-------------------------------------->|                |
  |                  |                   |                       |               |                |
  |                  |                   | 5C. DRIVE PROCESSOR   |               |                |
  |                  |                   | - Detect file formats |               |                |
  |                  |                   | - Store metadata in   |               |                |
  |                  |                   |   MongoDB             |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       | drive_documents|               |
  |                  |                   |                       |  collection)  |                |
  |                  |                   | - Send full files to  |               |                |
  |                  |                   |   Citex for parsing,  |               |                |
  |                  |                   |   chunking, embedding |               |                |
  |                  |                   |-------------------------------------->|                |
  |                  |                   |                       |               |                |
  |                  |                   | 6. UPDATE JOB STATUS  |               |                |
  |                  |                   |  "parsing_complete"   |               |                |
  |  <-- progress    |                   |                       |               |                |
  |     update       |                   |                       |               |                |
  |                  |                   |                       |               |                |
  |                  |                   | ===========================           |                |
  |                  |                   | = AI ANALYSIS PIPELINE   =           |                |
  |                  |                   | ===========================           |                |
  |                  |                   |                       |               |                |
  |                  |                   | 7A. People            |               |                |
  |                  |                   | Identification        |               |                |
  |                  |                   | - Scan all new data   |               |                |
  |                  |                   | - Identify unique     |               |                |
  |                  |                   |   people              |               |                |
  |                  |                   | - Resolve aliases     |               |                |
  |                  |                   |   (Slack handle =     |               |                |
  |                  |                   |    Jira username =    |               |                |
  |                  |                   |    Drive author)      |               |                |
  |                  |                   |--------------------------------------------------------------->|
  |                  |                   | <-- people list with  |               |                |
  |                  |                   |     inferred roles    |               |                |
  |                  |                   |---------------------->| (upsert       |                |
  |                  |                   |                       |  people       |                |
  |                  |                   |                       |  collection)  |                |
  |                  |                   |                       |               |                |
  |                  |                   | 7B. Project           |               |                |
  |                  |                   | Identification        |               |                |
  |                  |                   | - Cluster tasks by    |               |                |
  |                  |                   |   Jira project/epic   |               |                |
  |                  |                   | - Map Slack channels  |               |                |
  |                  |                   |   to projects         |               |                |
  |                  |                   |--------------------------------------------------------------->|
  |                  |                   | <-- project list      |               |                |
  |                  |                   |---------------------->| (upsert       |                |
  |                  |                   |                       |  projects     |                |
  |                  |                   |                       |  collection)  |                |
  |                  |                   |                       |               |                |
  |                  |                   | 7C. Task-Person       |               |                |
  |                  |                   | Mapping               |               |                |
  |                  |                   | - Jira assignees      |               |                |
  |                  |                   | - Slack informal      |               |                |
  |                  |                   |   assignments         |               |                |
  |                  |                   |   "Hey Raj, pick up   |               |                |
  |                  |                   |    PROJ-142"          |               |                |
  |                  |                   |--------------------------------------------------------------->|
  |                  |                   | <-- mappings          |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       | analysis_     |                |
  |                  |                   |                       | results)      |                |
  |                  |                   |                       |               |                |
  |                  |                   | 7D. Timeline          |               |                |
  |                  |                   | Construction &        |               |                |
  |                  |                   | Gap Detection         |               |                |
  |                  |                   |--------------------------------------------------------------->|
  |                  |                   | <-- timelines, gaps,  |               |                |
  |                  |                   |     risk flags        |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       | analysis_     |                |
  |                  |                   |                       | results)      |                |
  |                  |                   |                       |               |                |
  |                  |                   | 8. Generate briefing  |               |                |
  |                  |                   |--------------------------------------------------------------->|
  |                  |                   | <-- briefing text     |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       |  briefings)   |                |
  |                  |                   |                       |               |                |
  |                  |                   | 9. Calculate health   |               |                |
  |                  |                   | score                 |               |                |
  |                  |                   |---------------------->| (store in     |                |
  |                  |                   |                       | health_scores)|                |
  |                  |                   |                       |               |                |
  |                  |                   | 10. Re-evaluate       |               |                |
  |                  |                   | alerts                |               |                |
  |                  |                   |---------------------->| (update       |                |
  |                  |                   |                       |  alerts)      |                |
  |                  |                   |                       |               |                |
  |                  |                   | 11. Publish event     |               |                |
  |                  |                   | via Redis pub/sub     |               |                |
  |                  |                   | "ingestion_complete"  |               |                |
  |                  |                   |                       |               |                |
  |  <-- WebSocket   | <-- event        |                       |               |                |
  |  "Ingestion      |                  |                       |               |                |
  |   complete.      |                  |                       |               |                |
  |   342 Slack msgs,|                  |                       |               |                |
  |   89 Jira tasks, |                  |                       |               |                |
  |   14 documents." |                  |                       |               |                |
  |                  |                   |                       |               |                |
  |  Dashboard       |                  |                       |               |                |
  |  auto-refreshes  |                  |                       |               |                |
```

### 4.1 File Type Detection Logic

```python
# Pseudocode for file routing
def route_file(filename: str, content_type: str) -> Parser:
    if filename.endswith('.zip'):
        # Check internal structure
        if contains_slack_export_structure(filename):
            return SlackParser()
        else:
            return extract_and_route_individually(filename)

    elif filename.endswith('.json'):
        # Could be Slack API extract or generic JSON
        if looks_like_slack_api_extract(filename):
            return SlackParser()
        else:
            return DriveProcessor()

    elif filename.endswith('.csv'):
        if looks_like_jira_export(filename):
            return JiraParser()
        else:
            return DriveProcessor()

    elif filename.endswith(('.pdf', '.docx', '.pptx', '.xlsx',
                            '.html', '.md', '.txt')):
        return DriveProcessor()

    else:
        raise UnsupportedFileTypeError(filename)
```

### 4.2 Content Hashing for Deduplication

Every parsed record receives a content hash (`SHA-256` of the normalized content). Before storing, the pipeline checks if a record with the same hash already exists. If it does, the record is skipped. This enables incremental ingestion: the COO can re-upload a Slack export that overlaps with previous data and only new messages are processed.

```
content_hash = SHA256(normalize(record_content))

if db.collection.find_one({"content_hash": content_hash}):
    skip()  # Already ingested
else:
    store(record)
    index_in_citex(record)
```

---

## 5. Request Flow -- Report Generation

The report generation flow is conversational: the COO requests a report, the AI generates a structured report specification, the frontend renders a preview, the COO edits via natural language, and finally exports to PDF.

```
 COO              Frontend           Backend              AI Adapter        MongoDB        Report Engine
  |                  |                  |                     |                |                |
  | 1. "Generate a   |                  |                     |                |                |
  |  board-ready ops |                  |                     |                |                |
  |  report for Jan" |                  |                     |                |                |
  |----------------->|                  |                     |                |                |
  |                  | 2. POST /api/v1/ |                     |                |                |
  |                  | query            |                     |                |                |
  |                  |----------------->|                     |                |                |
  |                  |                  |                     |                |                |
  |                  |                  | 3. Detect report    |                |                |
  |                  |                  | intent              |                |                |
  |                  |                  |                     |                |                |
  |                  |                  | 4. Gather data      |                |                |
  |                  |                  | from MongoDB +      |                |                |
  |                  |                  | Citex               |                |                |
  |                  |                  |------------------------------------>|                |
  |                  |                  | <-- project data,   |                |                |
  |                  |                  |     people data,    |                |                |
  |                  |                  |     metrics         |                |                |
  |                  |                  |                     |                |                |
  |                  |                  | 5. Ask AI to        |                |                |
  |                  |                  | generate report_spec|                |                |
  |                  |                  | (structured JSON)   |                |                |
  |                  |                  |-------------------->|                |                |
  |                  |                  |                     |                |                |
  |                  |                  | <-- report_spec     |                |                |
  |                  |                  |  {                  |                |                |
  |                  |                  |   "type": "board",  |                |                |
  |                  |                  |   "title": "...",   |                |                |
  |                  |                  |   "sections": [     |                |                |
  |                  |                  |     { "heading",    |                |                |
  |                  |                  |       "content",    |                |                |
  |                  |                  |       "charts": [], |                |                |
  |                  |                  |       "tables": []  |                |                |
  |                  |                  |     }, ...          |                |                |
  |                  |                  |   ],                |                |                |
  |                  |                  |   "metadata": {}    |                |                |
  |                  |                  |  }                  |                |                |
  |                  |                  |                     |                |                |
  |                  |                  | 6. Store report_spec|                |                |
  |                  |                  |------------------------------------>|                |
  |                  |                  |                     |                |                |
  |                  | <-- report_spec  |                     |                |                |
  |                  |<-----------------|                     |                |                |
  |                  |                  |                     |                |                |
  | 7. Render rich   |                  |                     |                |                |
  | preview          |                  |                     |                |                |
  | - Formatted text |                  |                     |                |                |
  | - Live ECharts   |                  |                     |                |                |
  | - Tables         |                  |                     |                |                |
  |<-----------------|                  |                     |                |                |
  |                  |                  |                     |                |                |
  | 8. "Add a section|                  |                     |                |                |
  |  on hiring and   |                  |                     |                |                |
  |  shorten the     |                  |                     |                |                |
  |  summary"        |                  |                     |                |                |
  |----------------->|                  |                     |                |                |
  |                  |----------------->|                     |                |                |
  |                  |                  | 9. Send edit        |                |                |
  |                  |                  | instruction + old   |                |                |
  |                  |                  | report_spec to AI   |                |                |
  |                  |                  |-------------------->|                |                |
  |                  |                  | <-- updated spec    |                |                |
  |                  |                  |------------------------------------>| (update)       |
  |                  | <-- updated spec |                     |                |                |
  |                  |<-----------------|                     |                |                |
  | <-- Re-rendered  |                  |                     |                |                |
  |    preview       |                  |                     |                |                |
  |                  |                  |                     |                |                |
  |  (COO iterates   |                  |                     |                |                |
  |   as needed)     |                  |                     |                |                |
  |                  |                  |                     |                |                |
  | 10. "Export to   |                  |                     |                |                |
  |  PDF"            |                  |                     |                |                |
  |----------------->|                  |                     |                |                |
  |                  | POST /api/v1/    |                     |                |                |
  |                  | reports/{id}/    |                     |                |                |
  |                  | export           |                     |                |                |
  |                  |----------------->|                     |                |                |
  |                  |                  |                     |                |  11. Render    |
  |                  |                  |                     |                |                |
  |                  |                  | 11a. Load spec      |                |                |
  |                  |                  |------------------------------------>|                |
  |                  |                  |                     |                |                |
  |                  |                  | 11b. Render HTML    |                |                |
  |                  |                  | via Jinja2 template |                |                |
  |                  |                  |---------------------------------------------->       |
  |                  |                  |                     |                |                |
  |                  |                  | 11c. Render charts  |                |                |
  |                  |                  | as SVG via pyecharts|                |                |
  |                  |                  |---------------------------------------------->       |
  |                  |                  |                     |                |                |
  |                  |                  | 11d. WeasyPrint     |                |                |
  |                  |                  | HTML + SVGs -> PDF  |                |                |
  |                  |                  |---------------------------------------------->       |
  |                  |                  |                     |                |                |
  |                  |                  | <-- PDF bytes       |                |                |
  |                  |                  |                     |                |                |
  |                  |                  | 12. Store in        |                |                |
  |                  |                  | report_history +    |                |                |
  |                  |                  | exports volume      |                |                |
  |                  |                  |------------------------------------>|                |
  |                  |                  |                     |                |                |
  |                  | <-- PDF download |                     |                |                |
  |                  |<-----------------|                     |                |                |
  | <-- PDF file     |                  |                     |                |                |
  |<-----------------|                  |                     |                |                |
```

### 5.1 Report Spec Structure (Summary)

The `report_spec` is a JSON document that fully describes the report content and layout. See [Report Generation](./07-REPORT-GENERATION.md) for the complete specification.

```json
{
  "report_id": "rpt_abc123",
  "type": "board",
  "title": "Board Operations Report — January 2026",
  "period": { "start": "2026-01-01", "end": "2026-01-31" },
  "generated_at": "2026-02-05T10:30:00Z",
  "version": 3,
  "sections": [
    {
      "id": "sec_1",
      "heading": "Executive Summary",
      "content": "Markdown text...",
      "charts": [],
      "tables": []
    },
    {
      "id": "sec_2",
      "heading": "Sprint Performance",
      "content": "Markdown text...",
      "charts": [
        {
          "chart_id": "chart_1",
          "type": "bar",
          "title": "Sprint Velocity Trend",
          "echarts_option": { /* full ECharts option object */ }
        }
      ],
      "tables": [
        {
          "table_id": "tbl_1",
          "title": "Sprint Metrics Summary",
          "headers": ["Sprint", "Planned", "Completed", "Velocity"],
          "rows": [/* ... */]
        }
      ]
    }
  ],
  "metadata": {
    "data_sources": ["slack", "jira", "drive"],
    "projects_covered": ["project-alpha", "project-beta"],
    "branding": { "logo_url": "/assets/logo.png", "company_name": "YENSI Solutions" }
  }
}
```

### 5.2 PDF Rendering Pipeline

```
report_spec (JSON)
    |
    v
Jinja2 Template Selection
    |  (board.html, project.html, team.html, etc.)
    v
Template Rendering
    |  - Sections -> HTML blocks
    |  - Tables -> HTML tables with CSS styling
    |  - Chart specs -> pyecharts SVG rendering
    |  - Metadata -> Headers, footers, page numbers
    v
Complete HTML Document
    |  - Professional CSS (typography, colors, spacing)
    |  - Embedded SVG charts
    |  - Page break markers
    v
WeasyPrint
    |  - HTML + CSS -> PDF
    |  - Headers/footers on every page
    |  - Page numbers
    |  - Table of contents (optional)
    v
PDF Output
    |  - Stored in exports volume
    |  - Record in report_history collection
    v
Served to frontend for download
```

---

## 6. AI Adapter Architecture

The AI adapter pattern is **mandatory** per `technical.md`. It abstracts the AI provider behind a common interface, allowing seamless switching between CLI-based local models (development) and Open Router API (production) via a single environment variable.

### 6.1 Class Hierarchy

```
                    +---------------------------+
                    |      AIAdapter (ABC)      |
                    |  (abstract base class)    |
                    +---------------------------+
                    | + generate()              |
                    | + analyze_people()        |
                    | + analyze_project()       |
                    | + generate_report()       |
                    | + generate_chart_spec()   |
                    | + detect_correction()     |
                    | + summarize_conversation()|
                    +---------------------------+
                           /              \
                          /                \
           +--------------------+   +-------------------------+
           |   CLIAdapter       |   |  OpenRouterAdapter      |
           |   (development)    |   |  (production)           |
           +--------------------+   +-------------------------+
           | Invokes CLI tools  |   | Calls Open Router API   |
           | as Python          |   | via httpx async client  |
           | subprocesses       |   |                         |
           | - Claude CLI       |   | - Model selection via   |
           | - Codex CLI        |   |   config                |
           | - Gemini CLI       |   | - Streaming support     |
           |                    |   | - Retry with backoff    |
           | Process:           |   | - Token counting        |
           | 1. Write prompt    |   |                         |
           |    to temp file    |   | Process:                |
           | 2. Invoke CLI via  |   | 1. Build API request    |
           |    subprocess.run  |   | 2. POST to Open Router  |
           | 3. Capture stdout  |   | 3. Parse SSE stream     |
           | 4. Parse response  |   | 4. Return structured    |
           | 5. Return struct.  |   |    response             |
           +--------------------+   +-------------------------+
```

### 6.2 Abstract Base Class

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional

class AIResponse(BaseModel):
    text: str
    chart_specs: list[dict] = []
    corrections: list[dict] = []
    sources_used: list[str] = []
    tokens_used: int = 0
    model: str = ""

class PeopleAnalysis(BaseModel):
    people: list[dict]
    role_inferences: list[dict]
    confidence_scores: dict[str, float]

class ProjectAnalysis(BaseModel):
    projects: list[dict]
    timelines: list[dict]
    gaps: list[dict]
    risks: list[dict]

class ReportSpec(BaseModel):
    report_id: str
    type: str
    title: str
    sections: list[dict]
    metadata: dict

class ChartSpec(BaseModel):
    chart_id: str
    type: str
    title: str
    echarts_option: dict

class CorrectionResult(BaseModel):
    is_correction: bool
    entity_type: Optional[str] = None  # "person", "project", "task"
    entity_id: Optional[str] = None
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None

class ConversationSummary(BaseModel):
    summary: str
    key_facts: list[str]
    open_threads: list[str]
    tokens_used: int


class AIAdapter(ABC):
    """
    Abstract base class for all AI integrations.
    Implementations MUST handle prompt assembly, error handling,
    retries, and response parsing.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: dict,       # memory + RAG chunks + structured data
        max_tokens: int = 4096,
    ) -> AIResponse:
        """General-purpose generation for NL queries."""
        ...

    @abstractmethod
    async def analyze_people(
        self,
        raw_data: dict,      # slack_messages, jira_tasks, drive_docs
        existing_people: list[dict],
    ) -> PeopleAnalysis:
        """Identify and analyze people from ingested data."""
        ...

    @abstractmethod
    async def analyze_project(
        self,
        project_data: dict,  # tasks, messages, documents for one project
        people: list[dict],
    ) -> ProjectAnalysis:
        """Deep-dive analysis of a single project."""
        ...

    @abstractmethod
    async def generate_report(
        self,
        request: str,        # COO's NL request
        data: dict,          # assembled data for the report
        existing_spec: Optional[dict] = None,  # for edits
    ) -> ReportSpec:
        """Generate or edit a report specification."""
        ...

    @abstractmethod
    async def generate_chart_spec(
        self,
        request: str,        # COO's chart request
        data: dict,          # data to visualize
    ) -> ChartSpec:
        """Generate an ECharts option spec from data and request."""
        ...

    @abstractmethod
    async def detect_correction(
        self,
        message: str,        # COO's latest message
        context: dict,       # current facts and conversation
    ) -> CorrectionResult:
        """Detect if the COO is correcting a fact."""
        ...

    @abstractmethod
    async def summarize_conversation(
        self,
        turns: list[dict],
        existing_summary: str,
        hard_facts: list[dict],
    ) -> ConversationSummary:
        """Compact conversation history into a summary."""
        ...
```

### 6.3 CLIAdapter Implementation (Development)

```python
import asyncio
import json
import tempfile
from pathlib import Path

class CLIAdapter(AIAdapter):
    """
    Development adapter that invokes AI CLI tools as subprocesses.
    Supports Claude CLI, Codex CLI, and Gemini CLI.
    """

    def __init__(self, cli_tool: str = "claude"):
        self.cli_tool = cli_tool  # "claude" | "codex" | "gemini"
        self.cli_commands = {
            "claude": ["claude", "-p"],
            "codex":  ["codex", "--quiet", "--prompt"],
            "gemini": ["gemini", "--prompt"],
        }

    async def generate(self, system_prompt, user_message, context, max_tokens=4096):
        prompt = self._assemble_prompt(system_prompt, user_message, context)

        # Write prompt to temp file for large inputs
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            cmd = self._build_command(prompt_file)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise AIAdapterError(f"CLI returned {proc.returncode}: {stderr.decode()}")

            raw_response = stdout.decode()
            return self._parse_response(raw_response)
        finally:
            Path(prompt_file).unlink(missing_ok=True)

    # ... (other methods follow the same subprocess pattern)
```

### 6.4 OpenRouterAdapter Implementation (Production)

```python
import httpx

class OpenRouterAdapter(AIAdapter):
    """
    Production adapter that calls Open Router API.
    Supports model selection, streaming, retries with exponential backoff.
    """

    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def generate(self, system_prompt, user_message, context, max_tokens=4096):
        messages = self._build_messages(system_prompt, user_message, context)

        response = await self._call_with_retry(
            messages=messages,
            max_tokens=max_tokens,
        )

        return self._parse_response(response)

    async def _call_with_retry(self, messages, max_tokens, retries=3):
        for attempt in range(retries):
            try:
                resp = await self.client.post(
                    "/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                    },
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # exponential backoff

    # ... (other methods follow the same API call pattern)
```

### 6.5 Adapter Selection

```python
# config.py
import os

def get_ai_adapter() -> AIAdapter:
    """
    Factory function. Selection driven by AI_ADAPTER environment variable.
    """
    adapter_type = os.getenv("AI_ADAPTER", "cli")

    if adapter_type == "cli":
        cli_tool = os.getenv("AI_CLI_TOOL", "claude")
        return CLIAdapter(cli_tool=cli_tool)

    elif adapter_type == "openrouter":
        api_key = os.environ["OPENROUTER_API_KEY"]  # Required
        model = os.getenv("AI_MODEL", "anthropic/claude-sonnet-4")
        return OpenRouterAdapter(api_key=api_key, model=model)

    else:
        raise ValueError(f"Unknown AI_ADAPTER: {adapter_type}. Use 'cli' or 'openrouter'.")
```

### 6.6 Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AI_ADAPTER` | `cli`, `openrouter` | `cli` | Which adapter to use |
| `AI_CLI_TOOL` | `claude`, `codex`, `gemini` | `claude` | Which CLI tool (only when `AI_ADAPTER=cli`) |
| `OPENROUTER_API_KEY` | string | (none) | Required when `AI_ADAPTER=openrouter` |
| `AI_MODEL` | model ID string | `anthropic/claude-sonnet-4` | Open Router model (only when `AI_ADAPTER=openrouter`) |

---

## 7. Data Flow Overview

This section shows the complete lifecycle of data through the system, from raw file upload to dashboard presentation.

```
+============================================================================+
|                        DATA FLOW OVERVIEW                                  |
+============================================================================+

  +-------------------+     +-------------------+     +-------------------+
  |  Slack Export ZIP  |     |  Jira CSV Export   |     | Google Drive Files|
  |  (JSON per channel |     | (tasks, sprints,  |     | (PDF, DOCX, PPTX,|
  |   per day)         |     |  comments)         |     |  XLSX, MD, TXT)  |
  +--------+----------+     +--------+----------+     +--------+----------+
           |                          |                          |
           v                          v                          v
  +--------+----------+     +--------+----------+     +--------+----------+
  |    Slack Parser    |     |    Jira Parser     |     |  Drive Processor  |
  | - Unzip           |     | - CSV parsing      |     | - File type       |
  | - Channel parsing  |     | - Column mapping   |     |   detection       |
  | - Thread linking   |     | - Sprint mapping   |     | - Metadata        |
  | - User extraction  |     | - Comment parsing  |     |   extraction      |
  | - Content hashing  |     | - Content hashing  |     | - Content hashing |
  +--------+----------+     +--------+----------+     +--------+----------+
           |                          |                          |
           +------------+-------------+                          |
                        |                                        |
                        v                                        v
           +------------+-------------+             +------------+----------+
           |      MongoDB :23002      |             |     Citex :23004      |
           |   (Structured Storage)   |             |   (Semantic Index)    |
           |                          |             |                       |
           | - slack_messages         |             | - Document ingestion  |
           | - jira_tasks             |             | - Chunking            |
           | - drive_documents        |             | - Embedding           |
           |                          |             | - Vector storage      |
           | (Normalized schemas      |             |   (Qdrant :23005)     |
           |  with content hashes,    |             | - Raw chunk storage   |
           |  timestamps, source      |             |   (MongoDB :23006)    |
           |  tracking)               |             | - File storage        |
           +------------+-------------+             |   (MinIO :23007)      |
                        |                           | - Graph relationships |
                        |                           |   (Neo4j :23008)      |
                        |                           +------------+----------+
                        |                                        |
                        +-------------------+--------------------+
                                            |
                                            v
                        +-------------------+--------------------+
                        |        AI ANALYSIS PIPELINE            |
                        |        (AI Adapter powered)            |
                        |                                        |
                        |  Stage 1: People Identification        |
                        |    - Scan Slack users, Jira assignees, |
                        |      Drive authors                     |
                        |    - Resolve cross-platform identities |
                        |    - Infer roles from context          |
                        |                                        |
                        |  Stage 2: Project Identification       |
                        |    - Map Jira projects/epics           |
                        |    - Correlate Slack channels           |
                        |    - Link Drive docs to projects       |
                        |                                        |
                        |  Stage 3: Task-Person Mapping          |
                        |    - Jira formal assignments           |
                        |    - Slack informal assignments        |
                        |    - Multi-person task handling        |
                        |                                        |
                        |  Stage 4: Timeline & Gap Detection     |
                        |    - Construct project timelines       |
                        |    - Backward plan from deadlines      |
                        |    - Detect missing prerequisite tasks |
                        |    - Estimate capacity vs. remaining   |
                        |    - Flag external dependencies        |
                        |                                        |
                        |  Stage 5: Health Score Calculation     |
                        |    - Sprint health (30%)               |
                        |    - Communication health (25%)        |
                        |    - Throughput (20%)                  |
                        |    - Documentation health (15%)        |
                        |    - Alert count (10%)                 |
                        |                                        |
                        |  Stage 6: Briefing Generation          |
                        |    - Highlights / lowlights            |
                        |    - Risk flags                        |
                        |    - Items needing attention           |
                        +-------------------+--------------------+
                                            |
                                            v
                        +-------------------+--------------------+
                        |      MongoDB :23002                    |
                        |      (Analysis Results)                |
                        |                                        |
                        | - people (directory with roles,        |
                        |   activity levels, task counts)        |
                        | - projects (summaries, timelines,      |
                        |   completion %, risks, gaps)           |
                        | - analysis_results (task-person maps,  |
                        |   gap lists, capacity estimates)       |
                        | - health_scores (composite + sub)      |
                        | - briefings (generated text)           |
                        | - alerts (triggered thresholds)        |
                        +-------------------+--------------------+
                                            |
                    +-----------+-----------+-----------+
                    |           |                       |
                    v           v                       v
          +---------+--+ +-----+-------+       +-------+--------+
          | Dashboard  | |  Chat /     |       |  Report        |
          | Widgets    | |  NL Query   |       |  Generation    |
          |            | |             |       |                |
          | - Health   | | - Q&A with  |       | - AI generates |
          |   score    | |   RAG       |       |   report_spec  |
          | - Alert    | |   context   |       | - Preview in   |
          |   banner   | | - Inline    |       |   frontend     |
          | - Briefing | |   charts    |       | - NL editing   |
          | - Project  | | - Fact      |       | - PDF export   |
          |   cards    | |   correction|       |   (WeasyPrint) |
          | - Custom   | | - Widget    |       |                |
          |   widgets  | |   commands  |       |                |
          +------------+ +-------------+       +----------------+
```

### 7.1 Data Storage Split

The system uses a deliberate split between MongoDB (structured data, application state) and Citex (semantic search, RAG):

| Store | What Goes Here | Why |
|-------|---------------|-----|
| **MongoDB** (app) | Parsed records (slack_messages, jira_tasks, drive_documents), people directory, projects, analysis results, conversations, memory, widget specs, reports, alerts, audit log | Fast structured queries, aggregation pipelines, application state management |
| **Citex** (RAG) | Document chunks with embeddings, entity graphs, raw files | Semantic similarity search, RAG retrieval for NL queries |

Both stores receive data during ingestion. The backend queries both during NL query processing: MongoDB for structured lookups (e.g., "all tasks assigned to Raj in Project Alpha") and Citex for semantic search (e.g., relevant Slack conversations about the deployment timeline).

---

## 8. Memory System Overview

The memory system maintains conversational context across sessions and ensures the AI always has the right context to answer questions accurately. See [Memory System](./04-MEMORY-SYSTEM.md) for the complete specification.

### 8.1 Three-Layer Architecture

```
+============================================================================+
|                         MEMORY LAYERS                                      |
+============================================================================+
|                                                                            |
|  LAYER 1: HARD FACTS                                                      |
|  +------------------------------------------------------------------+     |
|  | - COO corrections and explicit statements                         |     |
|  | - "Raj is the lead architect"                                     |     |
|  | - "Project Alpha deadline is March 20"                            |     |
|  | - "Ignore Slack channel #random for analysis"                     |     |
|  |                                                                   |     |
|  | Properties:                                                       |     |
|  | - NEVER compacted or summarized                                   |     |
|  | - ALWAYS included in every prompt (highest priority)              |     |
|  | - Override any data from Slack/Jira/Drive                         |     |
|  | - Stored in memory_facts collection                               |     |
|  | - Timestamped, attributed, versioned                              |     |
|  +------------------------------------------------------------------+     |
|                                                                            |
|  LAYER 2: COMPACTED SUMMARY                                               |
|  +------------------------------------------------------------------+     |
|  | - Progressive summary of all prior conversation turns             |     |
|  | - Updated every 10 turns via AI-powered compaction                |     |
|  | - Contains: key decisions, ongoing threads, established context   |     |
|  |                                                                   |     |
|  | Properties:                                                       |     |
|  | - Grows slowly (AI compaction keeps it concise)                   |     |
|  | - ~2-8K tokens typical                                            |     |
|  | - Stored in memory_summaries collection                           |     |
|  | - One per conversation stream                                     |     |
|  +------------------------------------------------------------------+     |
|                                                                            |
|  LAYER 3: RECENT TURNS                                                    |
|  +------------------------------------------------------------------+     |
|  | - Last 10 raw conversation turns (user + assistant pairs)         |     |
|  | - Provides immediate conversational context                       |     |
|  | - Sliding window: when turn 11 arrives, turn 1 is compacted      |     |
|  |   into the summary                                                |     |
|  |                                                                   |     |
|  | Properties:                                                       |     |
|  | - Fixed size (10 turns max)                                       |     |
|  | - Full fidelity (no summarization)                                |     |
|  | - Stored in conversations collection                              |     |
|  +------------------------------------------------------------------+     |
|                                                                            |
+============================================================================+
```

### 8.2 Conversation Streams

Memory is organized into **streams**. Each stream has its own Hard Facts, Compacted Summary, and Recent Turns.

```
+-- Global Stream (cross-project conversations from main dashboard)
|
+-- Project Alpha Stream
|   +-- Merges: COO conversations about Alpha
|   +-- Merges: Slack messages from #project-alpha channel
|   +-- Merges: Relevant Jira task updates
|
+-- Project Beta Stream
|   +-- Merges: COO conversations about Beta
|   +-- Merges: Slack messages from #project-beta channel
|   +-- Merges: Relevant Jira task updates
|
+-- ... (one stream per project)
```

When the COO views a project and asks a question, the conversation is routed to that project's stream. When on the main dashboard, the global stream is used. Hard Facts created in any stream are also visible in the global stream.

### 8.3 Compaction Process

```
Turns 1-10 (raw) --> [Turn 11 arrives]
    |
    v
AI summarizes turns 1-10 into compacted summary
    |
    v
Old summary + new summary --> AI merges into single summary
    |
    v
Turns 2-11 are now the "recent turns" window
Turn 1 is archived (available for audit but not in prompt)
```

---

## 9. Security Architecture

Step Zero is designed for a single user running locally. Security measures protect data privacy during AI interactions without the overhead of full enterprise security.

### 9.1 Data Locality

```
+============================================================================+
|                       SECURITY BOUNDARY                                    |
|                    (COO's machine / server)                                |
|                                                                            |
|  +----------------------------------------------------------------------+  |
|  |                    Docker Environment                                 |  |
|  |                                                                      |  |
|  |  All containers, volumes, and data                                   |  |
|  |  reside within this boundary.                                        |  |
|  |                                                                      |  |
|  |  +----------------------+  +----------------------+                  |  |
|  |  | Docker Volumes       |  | Application Data     |                 |  |
|  |  | - mongo-data         |  | - Uploaded files     |                 |  |
|  |  | - redis-data         |  | - Generated PDFs     |                 |  |
|  |  | - qdrant-data        |  | - Audit logs         |                 |  |
|  |  | - neo4j-data         |  | - Memory/facts       |                 |  |
|  |  | - minio-data         |  |                      |                 |  |
|  |  +----------------------+  +----------------------+                  |  |
|  +----------------------------------------------------------------------+  |
|                                                                            |
|  OUTBOUND CONNECTIONS (only when AI_ADAPTER=openrouter):                   |
|  +----------------------------------------------------------------------+  |
|  |  ChiefOps Backend --> Open Router API (HTTPS)                         |  |
|  |  - Only sends: assembled prompt chunks (~7-17K tokens)               |  |
|  |  - Never sends: full data dumps, raw files, or database exports      |  |
|  |  - Provider guarantee: data not used for training                    |  |
|  +----------------------------------------------------------------------+  |
|                                                                            |
|  NO outbound connections when AI_ADAPTER=cli (fully local)                 |
+============================================================================+
```

### 9.2 PII Redaction Pipeline

Before any data is sent to an LLM (via either adapter), it passes through a PII redaction filter.

```
Raw chunk from Citex / MongoDB
    |
    v
+-- PII Scanner ----------------------------------------+
| Regex-based detection for:                             |
|   - Email addresses (xxx@xxx.com -> [EMAIL_REDACTED])  |
|   - Phone numbers (+1-xxx-xxx-xxxx -> [PHONE_REDACTED])|
|   - SSN patterns (xxx-xx-xxxx -> [SSN_REDACTED])      |
|   - Credit card patterns -> [CC_REDACTED]              |
|   - Custom patterns (configurable)                     |
+-------------------------------------------------------+
    |
    v
Redacted chunk (sent to LLM)
    |
    +-- Original + redacted stored in audit_log
```

### 9.3 Chunk Audit Log

Every AI request is logged with full traceability:

```json
{
  "audit_id": "aud_xyz789",
  "timestamp": "2026-02-05T10:30:00Z",
  "request_type": "nl_query",
  "conversation_id": "conv_abc123",
  "chunks_sent": [
    {
      "chunk_id": "chunk_001",
      "source": "slack",
      "channel": "#project-alpha",
      "tokens": 342,
      "pii_redactions": 2
    },
    {
      "chunk_id": "chunk_002",
      "source": "jira",
      "task_key": "ALPHA-45",
      "tokens": 128,
      "pii_redactions": 0
    }
  ],
  "total_tokens_sent": 12450,
  "total_tokens_received": 1823,
  "model": "anthropic/claude-sonnet-4",
  "adapter": "openrouter"
}
```

The COO can query the audit log to see exactly what data was sent in each AI request: "What data did you use to answer my last question?"

### 9.4 Opt-Out Tags

During ingestion, the COO can tag specific data sources as "never send to AI":

- Tag an entire Slack channel: `#hr-confidential` -> all messages excluded from AI prompts
- Tag specific files: `salary-report.xlsx` -> excluded from Citex indexing and AI prompts
- Tag by keyword pattern: any message containing "confidential" -> excluded

Opt-out tags are stored in the ingestion metadata and enforced at the RAG retrieval layer (Citex queries filter out tagged chunks) and the prompt assembly layer (MongoDB queries filter out tagged records).

### 9.5 No Authentication (Step Zero)

Step Zero has no authentication or authorization. The system is designed for a single user running on their own machine. The Docker Compose environment is not exposed to external networks.

Security is added in phases:

| Phase | Security Feature |
|-------|-----------------|
| Step Zero | No auth. Single user. Local Docker. Data locality. PII redaction. Audit log. |
| Phase 3 | Keycloak integration. JWT tokens. Role-based access (COO, Team Lead, Viewer). |
| Phase 5 | SOC 2 compliance. Full audit trail. Encryption at rest. Key management. |

---

## 10. Scalability Path

Every architectural decision in Step Zero is designed to scale without rewrites. The system grows along five axes.

### 10.1 Data Sources: File Dumps to Live Connectors

```
STEP ZERO                              PHASE 1-2
+---------------------+                +---------------------+
| Slack Export ZIP     |  ------>       | Slack Webhook +     |
| (manual upload)     |                | Events API          |
+---------------------+                | (real-time)         |
                                       +---------------------+
+---------------------+                +---------------------+
| Jira CSV Export      |  ------>       | Jira Webhook +      |
| (manual upload)     |                | REST API            |
+---------------------+                | (real-time)         |
                                       +---------------------+
+---------------------+                +---------------------+
| Google Drive Files   |  ------>       | Google Drive Watch   |
| (manual copy)       |                | API (push notif.)   |
+---------------------+                +---------------------+

                                       PHASE 2-3
                                       +---------------------+
                                       | GitHub Webhooks      |
                                       +---------------------+
                                       | Notion API           |
                                       +---------------------+
                                       | Salesforce API       |
                                       +---------------------+
                                       | 10+ more connectors  |
                                       +---------------------+
```

**Why this works without rewrites:**

The ingestion pipeline normalizes all data into the same MongoDB schemas regardless of source. A Slack message from a ZIP export has the same schema as a Slack message from a webhook. The parsers are swapped; everything downstream (MongoDB schema, Citex indexing, AI analysis, dashboard, reports) stays identical.

```
Source Layer                    Normalization Layer         Storage Layer
(changes per phase)             (same always)               (same always)

SlackZIPParser      ─┐
                     ├──> NormalizedSlackMessage ──> MongoDB + Citex
SlackWebhookParser  ─┘

JiraCSVParser       ─┐
                     ├──> NormalizedJiraTask     ──> MongoDB + Citex
JiraAPIParser       ─┘

DriveFileProcessor  ─┐
                     ├──> NormalizedDocument     ──> MongoDB + Citex
DriveWatchProcessor ─┘
```

### 10.2 Single Tenant to Multi-Tenant

```
STEP ZERO                              PHASE 3
+---------------------+                +---------------------+
| No auth             |                | Keycloak SSO        |
| Single user         |  ------>       | JWT tokens          |
| Single tenant       |                | RBAC roles:         |
|                     |                |  - COO (full access) |
|                     |                |  - Team Lead (scoped)|
|                     |                |  - Viewer (read-only)|
+---------------------+                +---------------------+

MongoDB Schema:                        MongoDB Schema:
{ project_id, ... }                    { tenant_id, project_id, ... }
                                       (tenant_id added to all collections,
                                        all queries scoped by tenant)
```

**Preparation in Step Zero:**

- All MongoDB collections include a `tenant_id` field set to `"default"` in Step Zero. In Phase 3, this becomes the actual tenant identifier.
- All queries include `tenant_id` in their filter. This is a no-op in Step Zero but enables multi-tenancy without query rewrites.
- The API layer has a middleware slot for auth. In Step Zero it passes through. In Phase 3, it validates JWT tokens and extracts `tenant_id`.

### 10.3 Local Docker Compose to Cloud Kubernetes

```
STEP ZERO                              PHASE 3-5
+---------------------+                +---------------------+
| docker-compose.yml  |                | Kubernetes Cluster  |
| Single machine      |  ------>       |                     |
| Docker volumes      |                | Deployments:        |
|                     |                |  - frontend (2+ pods)|
|                     |                |  - backend (3+ pods) |
|                     |                | StatefulSets:        |
|                     |                |  - MongoDB (replica) |
|                     |                |  - Redis (sentinel)  |
|                     |                | Citex cluster        |
|                     |                | Ingress + TLS        |
|                     |                | PersistentVolumes    |
+---------------------+                +---------------------+
```

**Preparation in Step Zero:**

- Each service is its own Docker container with clear boundaries
- No inter-service communication via shared filesystem (only network)
- Environment-variable-driven configuration (12-factor app)
- Health check endpoints on all services
- Stateless backend (all state in MongoDB/Redis)

### 10.4 Advisory to Autonomous

```
STEP ZERO              PHASE 4                  PHASE 5
+--------------+       +-----------------+       +------------------+
| ADVISORY     |       | SEMI-AUTONOMOUS |       | FULL AUTONOMOUS  |
|              |       |                 |       |                  |
| AI analyzes  | ----> | AI suggests     | ----> | AI executes      |
| and reports  |       | actions with    |       | low-risk actions |
|              |       | approval        |       | automatically    |
| No actions   |       | workflows       |       |                  |
| taken        |       |                 |       | Approval for     |
|              |       | COO approves/   |       | high-risk only   |
|              |       | rejects         |       |                  |
+--------------+       +-----------------+       +------------------+

Examples:
Step Zero:             Phase 4:                  Phase 5:
"ALPHA-89 has no       "I recommend assigning    Auto-assigns ALPHA-89
 assignee and is on     ALPHA-89 to Raj.         to Raj (low-risk).
 the critical path"     [Approve] [Reject]"      Notifies COO after.
```

**Preparation in Step Zero:**

- The AI analysis pipeline already produces structured recommendations (gaps, risks, missing tasks)
- These recommendations have a consistent schema that can be extended with action definitions
- The action execution layer is a clean extension point (new service, same data model)

### 10.5 Data Source Growth

| Phase | Sources | Count |
|-------|---------|-------|
| Step Zero | Slack (export), Jira (CSV), Google Drive (files) | 3 |
| Phase 1 | + GitHub (export), Notion (export) | 5 |
| Phase 2 | + Slack (live), Jira (live), Google Drive (live), GitHub (live), Notion (live) | 5 (upgraded to live) |
| Phase 3 | + Salesforce, SAP, ServiceNow, Confluence | 9 |
| Phase 4 | + Linear, Asana, Monday.com, Figma, Datadog, PagerDuty | 15+ |

Each new source requires only:
1. A new parser/connector implementing the same interface
2. A normalization mapping to existing MongoDB schemas
3. Citex indexing configuration

No changes needed to: AI adapter, memory system, dashboard, report generation, widget system, alert engine, or any downstream component.

---

## Related Documents

- **Product:** [PRD](./01-PRD.md)
- **Data:** [Data Models](./03-DATA-MODELS.md)
- **Core Systems:** [Memory System](./04-MEMORY-SYSTEM.md), [Citex Integration](./05-CITEX-INTEGRATION.md), [AI Layer](./06-AI-LAYER.md)
- **Features:** [File Ingestion](./08-FILE-INGESTION.md), [People Intelligence](./09-PEOPLE-INTELLIGENCE.md), [Report Generation](./07-REPORT-GENERATION.md), [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md)
- **Execution:** [Implementation Plan](./11-IMPLEMENTATION-PLAN.md), [UI/UX Design](./12-UI-UX-DESIGN.md)
