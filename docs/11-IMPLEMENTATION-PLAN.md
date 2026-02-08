# Implementation Plan -- Part A: ChiefOps -- Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | **Implementation Plan** | [Implementation Plan -- Part B](./11B-IMPLEMENTATION-PLAN-CONTINUED.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Overview

ChiefOps Step Zero is built across **10 two-week sprints** (20 weeks total). Each sprint delivers a working vertical slice -- backend API, service logic, frontend UI, and tests -- that the COO can touch at the end of the sprint. There are no "backend-only" or "frontend-only" sprints. Every sprint ends with a deployable increment that adds visible capability.

### Delivery Philosophy

| Principle | Detail |
|-----------|--------|
| **Vertical slices** | Every sprint ships backend + frontend + tests for one capability |
| **Working software** | `docker compose up` at the end of every sprint yields a functional system |
| **Incremental value** | The COO can do something new after every sprint |
| **No big bang** | No sprint depends on "finishing everything first" -- each builds on the last |
| **Feature-flagged** | Incomplete features behind flags; main branch is always deployable |

### Sprint Map

| Sprint | Weeks | Focus | Key Deliverable |
|--------|-------|-------|-----------------|
| 0 | 1--2 | Foundation | Docker Compose starts all 10 containers; hello-world end-to-end |
| 1 | 3--4 | Data Ingestion | COO uploads Slack/Jira/Drive files; data lands in MongoDB + Citex |
| 2 | 5--6 | AI Layer & Memory | COO chats with the system; responses use ingested data via RAG |
| 3 | 7--8 | People Intelligence | System identifies people with roles; COO can correct |
| 4 | 9--10 | Project Intelligence | COO asks "How's Project Alpha?" and gets AI analysis |
| 5 | 11--12 | Dashboard Foundation | Dashboard renders KPIs and charts; COO creates widgets via chat |
| 6 | 13--14 | Report Generation | COO says "Generate a board report" and gets a preview + PDF |
| 7 | 15--16 | Advanced Dashboards | Gantt charts, person grids, timeline widgets, auto-refresh |
| 8 | 17--18 | Polish & Integration | End-to-end workflows, performance tuning, error handling |
| 9 | 19--20 | Hardening & Launch | Load testing, edge cases, documentation, launch prep |

Sprints 6--9 are covered in [Implementation Plan -- Part B](./11B-IMPLEMENTATION-PLAN-CONTINUED.md).

---

## 2. Repository Structure

The project is a monorepo. Backend (Python/FastAPI) and frontend (React/Vite) live side by side. Docker Compose orchestrates all services including the Citex stack.

```
yensi-chiefops/
├── docker-compose.yml              # Production-like compose (all 10 services)
├── docker-compose.dev.yml          # Dev overrides (hot reload, debug ports)
├── .env.example                    # All required environment variables
├── .gitignore
├── Makefile                        # Convenience targets: up, down, test, lint
│
├── backend/
│   ├── Dockerfile
│   ├── Dockerfile.dev              # Dev image with watchfiles for hot reload
│   ├── requirements.txt            # Pinned production dependencies
│   ├── requirements-dev.txt        # Test + lint dependencies
│   ├── pyproject.toml              # Black, ruff, mypy configuration
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry point, lifespan, middleware
│   │   ├── config.py               # Settings via pydantic-settings (env vars)
│   │   ├── database.py             # Motor async MongoDB connection pool
│   │   ├── redis_client.py         # Redis async connection (aioredis)
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       # Main API router (mounts all sub-routers)
│   │   │       ├── health.py       # GET /health -- readiness + liveness
│   │   │       ├── projects.py     # Project CRUD + analysis endpoints
│   │   │       ├── people.py       # People directory + corrections
│   │   │       ├── ingestion.py    # File upload + ingestion status
│   │   │       ├── conversation.py # Chat / NL query + streaming
│   │   │       ├── dashboards.py   # Dashboard CRUD (main, project, custom)
│   │   │       ├── widgets.py      # Widget CRUD + data query endpoints
│   │   │       ├── reports.py      # Report generation + PDF export
│   │   │       └── websocket.py    # WebSocket endpoint for real-time updates
│   │   │
│   │   ├── models/                  # Pydantic v2 models (03-DATA-MODELS.md)
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # MongoBaseModel, shared utilities
│   │   │   ├── person.py           # Person, SourceReference, EngagementMetrics
│   │   │   ├── project.py          # Project, SprintHealth, TechnicalFeasibility
│   │   │   ├── ingestion.py        # IngestionJob, IngestionResult
│   │   │   ├── conversation.py     # ConversationTurn, MemoryStream
│   │   │   ├── dashboard.py        # Dashboard, WidgetSpec, DataQuery
│   │   │   ├── report.py           # ReportSpec, ReportSection
│   │   │   └── alert.py            # Alert model
│   │   │
│   │   ├── services/                # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── ingestion/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py  # Coordinates file detection + parsing
│   │   │   │   ├── detector.py      # File type auto-detection
│   │   │   │   ├── slack_admin.py   # Slack Admin Export ZIP parser
│   │   │   │   ├── slack_manual.py  # Slack manual export parser
│   │   │   │   ├── slack_api.py     # Slack API extract script output parser
│   │   │   │   ├── jira_csv.py      # Jira CSV parser
│   │   │   │   ├── drive.py         # Google Drive folder processor
│   │   │   │   └── hasher.py        # Content hashing for deduplication
│   │   │   │
│   │   │   ├── people/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pipeline.py      # 5-step people identification pipeline
│   │   │   │   ├── resolver.py      # Cross-source entity resolution
│   │   │   │   ├── role_detector.py # AI-powered role detection
│   │   │   │   └── corrections.py   # COO correction handler + cascading
│   │   │   │
│   │   │   ├── memory/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── manager.py       # MemoryManager -- context assembly
│   │   │   │   ├── hard_facts.py    # Hard fact extraction + storage
│   │   │   │   ├── compactor.py     # Progressive summary compaction
│   │   │   │   └── assembler.py     # Context builder for AI requests
│   │   │   │
│   │   │   ├── projects/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analyzer.py      # Project analysis engine
│   │   │   │   ├── health.py        # Sprint health + operational score
│   │   │   │   ├── gaps.py          # Gap detection + backward planning
│   │   │   │   └── feasibility.py   # Technical feasibility analysis
│   │   │   │
│   │   │   ├── reports/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── generator.py     # Report spec generation via AI
│   │   │   │   ├── editor.py        # NL report editing
│   │   │   │   └── pdf_export.py    # HTML-to-PDF via WeasyPrint
│   │   │   │
│   │   │   ├── widgets/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── query_engine.py  # DataQuery -> MongoDB aggregation
│   │   │   │   ├── spec_generator.py # NL -> WidgetSpec via AI
│   │   │   │   └── cache.py         # Redis caching for widget data
│   │   │   │
│   │   │   └── conversation/
│   │   │       ├── __init__.py
│   │   │       ├── service.py       # Conversation orchestrator
│   │   │       ├── intent.py        # NL intent detection
│   │   │       └── streaming.py     # SSE streaming handler
│   │   │
│   │   ├── ai/                       # AI adapter layer (06-AI-LAYER.md)
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py           # AIAdapter ABC, AIRequest, AIResponse
│   │   │   ├── cli_adapter.py       # CLI subprocess adapter (dev)
│   │   │   ├── openrouter_adapter.py # OpenRouter HTTP adapter (prod)
│   │   │   ├── factory.py           # Adapter factory (config-driven)
│   │   │   └── prompts/
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # Prompt template base class
│   │   │       ├── people.py        # People identification prompts
│   │   │       ├── project.py       # Project analysis prompts
│   │   │       ├── report.py        # Report generation prompts
│   │   │       ├── widget.py        # Widget spec generation prompts
│   │   │       └── conversation.py  # General conversation prompts
│   │   │
│   │   └── citex/                    # Citex RAG client (05-CITEX-INTEGRATION.md)
│   │       ├── __init__.py
│   │       ├── client.py            # Async HTTP client for Citex REST API
│   │       ├── models.py            # Citex request/response Pydantic models
│   │       └── indexer.py           # Document indexing helper
│   │
│   └── tests/
│       ├── conftest.py              # Shared fixtures (test DB, mock AI adapter)
│       ├── test_health.py
│       ├── test_ingestion/
│       ├── test_people/
│       ├── test_projects/
│       ├── test_conversation/
│       ├── test_dashboards/
│       ├── test_widgets/
│       ├── test_reports/
│       └── test_ai/
│
├── frontend/
│   ├── Dockerfile
│   ├── Dockerfile.dev               # Dev image with Vite HMR
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── index.html
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── main.tsx                 # React root + router
│   │   ├── App.tsx                  # Top-level layout (sidebar + content)
│   │   ├── vite-env.d.ts
│   │   │
│   │   ├── pages/
│   │   │   ├── MainDashboard.tsx    # Global dashboard (fixed layout)
│   │   │   ├── ProjectDashboard.tsx # Per-project static dashboard
│   │   │   ├── CustomDashboard.tsx  # Per-project NL-managed dashboard
│   │   │   ├── DataUpload.tsx       # Drag-and-drop file upload page
│   │   │   ├── PeopleDirectory.tsx  # People listing + detail view
│   │   │   ├── ProjectDetail.tsx    # Single project deep-dive
│   │   │   ├── ReportPreview.tsx    # Report preview + NL editing
│   │   │   └── NotFound.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatSidebar.tsx       # Expandable chat panel
│   │   │   │   ├── ChatInput.tsx         # Input bar with send button
│   │   │   │   ├── ChatMessage.tsx       # Single message bubble
│   │   │   │   └── StreamingResponse.tsx # Animated streaming text
│   │   │   │
│   │   │   ├── widgets/
│   │   │   │   ├── WidgetRenderer.tsx    # Dispatch to correct widget type
│   │   │   │   ├── BarChart.tsx          # ECharts bar chart
│   │   │   │   ├── LineChart.tsx         # ECharts line chart
│   │   │   │   ├── PieChart.tsx          # ECharts pie chart
│   │   │   │   ├── KpiCard.tsx           # Single KPI metric card
│   │   │   │   ├── DataTable.tsx         # Sortable data table
│   │   │   │   ├── SummaryText.tsx       # AI-generated text block
│   │   │   │   ├── GanttChart.tsx        # Timeline/Gantt via ECharts
│   │   │   │   ├── PersonGrid.tsx        # People card grid
│   │   │   │   ├── TimelineWidget.tsx    # Activity timeline
│   │   │   │   └── ActivityFeed.tsx      # Recent events feed
│   │   │   │
│   │   │   ├── reports/
│   │   │   │   ├── ReportViewer.tsx      # Rendered report preview
│   │   │   │   ├── ReportSection.tsx     # Single section renderer
│   │   │   │   └── PdfExportButton.tsx   # Export trigger
│   │   │   │
│   │   │   ├── people/
│   │   │   │   ├── PersonCard.tsx        # Person summary card
│   │   │   │   ├── PersonDetail.tsx      # Full person view
│   │   │   │   └── RoleBadge.tsx         # Role display with source indicator
│   │   │   │
│   │   │   ├── ingestion/
│   │   │   │   ├── DropZone.tsx          # Drag-and-drop upload area
│   │   │   │   ├── UploadProgress.tsx    # Per-file progress indicator
│   │   │   │   └── IngestionSummary.tsx  # Post-upload results summary
│   │   │   │
│   │   │   └── shared/
│   │   │       ├── Sidebar.tsx           # Main navigation sidebar
│   │   │       ├── TopBar.tsx            # Search bar + alerts
│   │   │       ├── HealthScore.tsx       # Health score circle
│   │   │       ├── LoadingSpinner.tsx
│   │   │       └── ErrorBoundary.tsx
│   │   │
│   │   ├── stores/                       # Zustand state management
│   │   │   ├── chatStore.ts             # Chat messages + conversation state
│   │   │   ├── dashboardStore.ts        # Dashboard + widget state
│   │   │   ├── projectStore.ts          # Project list + selected project
│   │   │   ├── peopleStore.ts           # People directory state
│   │   │   ├── ingestionStore.ts        # Upload progress state
│   │   │   └── reportStore.ts           # Report state
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChat.ts               # Chat interaction hook
│   │   │   ├── useWidgetData.ts         # Widget data fetching + caching
│   │   │   ├── useWebSocket.ts          # WebSocket connection hook
│   │   │   └── useStreamingResponse.ts  # SSE streaming hook
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                   # Axios instance + interceptors
│   │   │   ├── websocket.ts             # WebSocket client
│   │   │   └── utils.ts                 # Formatting, date helpers
│   │   │
│   │   └── types/
│   │       ├── api.ts                   # API response types
│   │       ├── models.ts               # Domain model types (mirrors backend)
│   │       └── widgets.ts              # Widget spec + data types
│   │
│   └── tests/
│       ├── setup.ts                     # Vitest + RTL setup
│       ├── components/                  # Component unit tests
│       └── e2e/                         # Playwright E2E tests
│           └── playwright.config.ts
│
└── scripts/
    ├── seed-data.py                     # Load sample Slack/Jira/Drive data
    ├── reset-db.py                      # Drop all collections (dev only)
    └── chiefops-slack-extract.py        # Slack API extract helper for COO
```

---

## 3. Docker Compose Configuration

All services use sequential ports starting at **23000**. The development compose file adds hot reload and debug capabilities.

### 3.1 `docker-compose.yml`

```yaml
version: "3.9"

services:
  # ─────────────────────────────────────────────
  # ChiefOps Frontend — React 19 / Vite
  # ─────────────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "23000:5173"
    environment:
      - VITE_API_URL=http://localhost:23001
      - VITE_WS_URL=ws://localhost:23001
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # ChiefOps Backend — FastAPI / Python 3.11+
  # ─────────────────────────────────────────────
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "23001:8000"
    environment:
      - MONGO_URL=mongodb://chiefops-mongo:27017
      - MONGO_DB_NAME=chiefops
      - REDIS_URL=redis://chiefops-redis:6379/0
      - CITEX_API_URL=http://citex-api:8000
      - AI_ADAPTER=cli
      - AI_CLI_COMMAND=claude
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENROUTER_MODEL=${OPENROUTER_MODEL:-anthropic/claude-sonnet-4}
      - LOG_LEVEL=info
    volumes:
      - upload-data:/app/uploads
    depends_on:
      chiefops-mongo:
        condition: service_healthy
      chiefops-redis:
        condition: service_healthy
      citex-api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # ChiefOps MongoDB — Primary datastore
  # ─────────────────────────────────────────────
  chiefops-mongo:
    image: mongo:7
    ports:
      - "23002:27017"
    volumes:
      - chiefops-mongo-data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # ChiefOps Redis — Caching + pub/sub
  # ─────────────────────────────────────────────
  chiefops-redis:
    image: redis:7-alpine
    ports:
      - "23003:6379"
    volumes:
      - chiefops-redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # Citex API — RAG backbone
  # ─────────────────────────────────────────────
  citex-api:
    image: yensi/citex:latest
    ports:
      - "23004:8000"
    environment:
      - QDRANT_URL=http://citex-qdrant:6333
      - MONGO_URL=mongodb://citex-mongo:27017
      - MINIO_ENDPOINT=citex-minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}
      - NEO4J_URL=bolt://citex-neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD:-chiefops-neo4j}
      - REDIS_URL=redis://citex-redis:6379/0
    depends_on:
      citex-qdrant:
        condition: service_healthy
      citex-mongo:
        condition: service_healthy
      citex-minio:
        condition: service_healthy
      citex-neo4j:
        condition: service_healthy
      citex-redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # Citex Qdrant — Vector search engine
  # ─────────────────────────────────────────────
  citex-qdrant:
    image: qdrant/qdrant:v1.12.1
    ports:
      - "23005:6333"
    volumes:
      - citex-qdrant-data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # Citex MongoDB — Citex internal storage
  # ─────────────────────────────────────────────
  citex-mongo:
    image: mongo:7
    ports:
      - "23006:27017"
    volumes:
      - citex-mongo-data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # Citex MinIO — Object storage for raw files
  # ─────────────────────────────────────────────
  citex-minio:
    image: minio/minio:latest
    ports:
      - "23007:9000"
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY:-minioadmin}
    volumes:
      - citex-minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # Citex Neo4j — Graph database for entities
  # ─────────────────────────────────────────────
  citex-neo4j:
    image: neo4j:5
    ports:
      - "23008:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-chiefops-neo4j}
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - citex-neo4j-data:/data
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 30s
    networks:
      - chiefops

  # ─────────────────────────────────────────────
  # Citex Redis — Citex internal caching
  # ─────────────────────────────────────────────
  citex-redis:
    image: redis:7-alpine
    ports:
      - "23009:6379"
    volumes:
      - citex-redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chiefops

volumes:
  upload-data:
  chiefops-mongo-data:
  chiefops-redis-data:
  citex-qdrant-data:
  citex-mongo-data:
  citex-minio-data:
  citex-neo4j-data:
  citex-redis-data:

networks:
  chiefops:
    driver: bridge
```

### 3.2 `docker-compose.dev.yml` (Override for Development)

```yaml
version: "3.9"

services:
  frontend:
    build:
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend/src:/app/src       # Hot module replacement
      - ./frontend/index.html:/app/index.html

  backend:
    build:
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend/app:/app/app         # Watchfiles auto-reload
      - upload-data:/app/uploads
    environment:
      - LOG_LEVEL=debug
      - AI_ADAPTER=cli
    command: >
      watchfiles
      "uvicorn app.main:app --host 0.0.0.0 --port 8000"
      /app/app
```

### 3.3 Port Summary

| Service | Container Port | Host Port | Purpose |
|---------|---------------|-----------|---------|
| Frontend | 5173 | **23000** | React dev server / Nginx in prod |
| Backend | 8000 | **23001** | FastAPI application |
| ChiefOps MongoDB | 27017 | **23002** | Primary datastore |
| ChiefOps Redis | 6379 | **23003** | Caching + pub/sub |
| Citex API | 8000 | **23004** | RAG backbone REST API |
| Citex Qdrant | 6333 | **23005** | Vector search |
| Citex MongoDB | 27017 | **23006** | Citex internal storage |
| Citex MinIO | 9000 | **23007** | Object/file storage |
| Citex Neo4j | 7687 | **23008** | Graph database |
| Citex Redis | 6379 | **23009** | Citex internal caching |

---

## 4. Dependency Matrix

### 4.1 Backend (Python) -- `requirements.txt`

```
# Web framework
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1

# Database
motor==3.6.0
pymongo==4.10.1

# Cache + pub/sub
redis[hiredis]==5.2.1

# HTTP client (for Citex + OpenRouter)
httpx==0.28.1

# File handling
aiofiles==24.1.0
python-multipart==0.0.20
openpyxl==3.1.5

# PDF export
weasyprint==62.3
pyecharts==2.0.6

# Utilities
python-dateutil==2.9.0
orjson==3.10.13
python-dotenv==1.0.1

# Streaming
sse-starlette==2.2.1

# WebSocket
websockets==14.1
```

### 4.2 Backend (Python) -- `requirements-dev.txt`

```
-r requirements.txt

# Testing
pytest==8.3.4
pytest-asyncio==0.25.0
pytest-cov==6.0.0
httpx==0.28.1            # For TestClient

# Linting + formatting
ruff==0.8.6
black==24.10.0
mypy==1.14.1

# Hot reload
watchfiles==1.0.3
```

### 4.3 Frontend (npm) -- `package.json` Dependencies

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.1",
    "zustand": "^5.0.3",
    "axios": "^1.7.9",
    "echarts": "^5.5.1",
    "echarts-for-react": "^3.0.2",
    "clsx": "^2.1.1",
    "date-fns": "^4.1.0",
    "react-dropzone": "^14.3.5",
    "react-hot-toast": "^2.4.1",
    "lucide-react": "^0.469.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.2",
    "@types/react-dom": "^19.0.2",
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.7",
    "typescript": "^5.7.3",
    "tailwindcss": "^3.4.17",
    "postcss": "^8.4.49",
    "autoprefixer": "^10.4.20",
    "vitest": "^2.1.8",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/user-event": "^14.5.2",
    "@playwright/test": "^1.49.1",
    "eslint": "^9.17.0",
    "eslint-plugin-react-hooks": "^5.1.0",
    "@typescript-eslint/eslint-plugin": "^8.19.1",
    "@typescript-eslint/parser": "^8.19.1",
    "prettier": "^3.4.2",
    "prettier-plugin-tailwindcss": "^0.6.9"
  }
}
```

---

## 5. Sprint 0: Foundation (Weeks 1--2)

### Goal

Stand up the full Docker Compose environment with all 10 containers starting successfully, a "hello world" FastAPI backend, and a React frontend placeholder -- proving the entire stack works end-to-end.

### Backend Tasks

- **`app/main.py`** -- FastAPI application with lifespan context manager for startup/shutdown. Register CORS middleware (allow all origins in dev). Mount the v1 router.
- **`app/config.py`** -- `Settings` class using `pydantic-settings` reading from environment variables: `MONGO_URL`, `MONGO_DB_NAME`, `REDIS_URL`, `CITEX_API_URL`, `AI_ADAPTER`, `AI_CLI_COMMAND`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `LOG_LEVEL`.
- **`app/database.py`** -- Motor async client initialization. Connection pool created at startup, closed at shutdown. Export `get_database()` dependency.
- **`app/redis_client.py`** -- Async Redis client initialization. Ping on startup to verify connectivity.
- **`app/api/v1/router.py`** -- Main router that includes all sub-routers under `/api/v1`. Initially only health is active.
- **`app/api/v1/health.py`** -- `GET /api/v1/health` returns `{"status": "ok", "mongo": true, "redis": true, "citex": true}` after pinging each dependency.
- **`app/models/base.py`** -- `MongoBaseModel` with `created_at`, `updated_at` fields and `model_config` for MongoDB compatibility.
- **`app/citex/client.py`** -- Minimal Citex client with a `ping()` method that hits the Citex health endpoint.
- **`Dockerfile`** -- Multi-stage build: Python 3.11-slim base, install requirements, copy app, run uvicorn.
- **`Dockerfile.dev`** -- Single-stage with watchfiles for hot reload.
- **`requirements.txt`** and **`requirements-dev.txt`** -- As defined in Section 4.
- **`pyproject.toml`** -- Ruff, Black, and mypy configuration. Strict mypy mode enabled.

### Frontend Tasks

- **`src/main.tsx`** -- React root with `BrowserRouter` and `App` component.
- **`src/App.tsx`** -- Top-level layout: sidebar placeholder + main content area. Renders `<Outlet />` from React Router.
- **`src/pages/MainDashboard.tsx`** -- Placeholder page displaying "ChiefOps" header text and a health status indicator that fetches `GET /api/v1/health`.
- **`src/components/shared/Sidebar.tsx`** -- Navigation sidebar with placeholder links for Dashboard, Data Upload, People, Projects.
- **`src/components/shared/TopBar.tsx`** -- Top bar with search input placeholder and alert badge placeholder.
- **`src/lib/api.ts`** -- Axios instance configured with `VITE_API_URL` base URL and JSON content type.
- **`vite.config.ts`** -- React plugin, proxy `/api` to backend in dev mode, strict TypeScript.
- **`tailwind.config.ts`** -- Custom color palette for ChiefOps brand, extended spacing.
- **`tsconfig.json`** -- `strict: true`, path aliases (`@/` mapping to `src/`).
- **`Dockerfile`** / **`Dockerfile.dev`** -- Node 20 base, install deps, Vite dev server with HMR.

### CI Setup

- **Linting** -- Ruff + Black for Python, ESLint + Prettier for TypeScript
- **Type checking** -- mypy (strict) for backend, `tsc --noEmit` for frontend
- **GitHub Actions workflow** (or Makefile targets): `make lint`, `make typecheck`, `make test`

### Key Deliverables

- `docker compose up` starts all 10 containers without errors
- `http://localhost:23000` shows the React app with "ChiefOps" header and sidebar
- `http://localhost:23001/api/v1/health` returns `{"status": "ok", "mongo": true, "redis": true, "citex": true}`
- `http://localhost:23001/docs` shows the FastAPI OpenAPI documentation page
- The frontend fetches the health endpoint and displays green status indicators

### Definition of Done

- [ ] All 10 Docker containers start and pass their health checks
- [ ] Backend health endpoint verifies connectivity to MongoDB, Redis, and Citex
- [ ] Frontend renders in the browser with sidebar navigation and health status
- [ ] `make lint` and `make typecheck` pass with zero errors
- [ ] Pydantic v2 base model is defined and importable
- [ ] `.env.example` documents every required environment variable
- [ ] README with setup instructions is present in the repo root

---

## 6. Sprint 1: Data Ingestion (Weeks 3--4)

### Goal

Enable the COO to upload Slack exports, Jira CSV files, and Google Drive folders through a drag-and-drop interface, with real-time progress feedback, automatic file type detection, and data landing in both MongoDB and Citex.

### Backend Tasks

- **`app/api/v1/ingestion.py`** -- Endpoints:
  - `POST /api/v1/ingest/upload` -- Multipart file upload (single or multiple files). Returns `ingestion_job_id`.
  - `GET /api/v1/ingest/jobs` -- List all ingestion jobs with status.
  - `GET /api/v1/ingest/jobs/{job_id}` -- Single job detail with per-file status.
  - `DELETE /api/v1/ingest/jobs/{job_id}` -- Cancel a running job or delete a completed one.
- **`app/api/v1/websocket.py`** -- WebSocket endpoint at `/ws/ingestion/{job_id}` for real-time progress updates during file processing.
- **`app/models/ingestion.py`** -- Pydantic models: `IngestionJob` (id, status, files, started_at, completed_at, error_count), `IngestionFileResult` (filename, file_type, status, records_processed, records_skipped, error_message, content_hash).
- **`app/services/ingestion/orchestrator.py`** -- Main ingestion coordinator. Receives uploaded files, calls the detector, dispatches to the correct parser, tracks progress, emits WebSocket events.
- **`app/services/ingestion/detector.py`** -- Auto-detection logic from [08-FILE-INGESTION.md](./08-FILE-INGESTION.md): ZIP inspection for `users.json` + `channels.json` (Slack Admin), `_metadata.json` (API extract), CSV header sniffing for Jira columns, file extension checking for Drive documents.
- **`app/services/ingestion/slack_admin.py`** -- Parser for Slack Admin Export ZIPs. Extracts users, channels, and messages. Writes to `slack_messages`, `slack_channels`, and initial `people` records in MongoDB. Sends message content to Citex for indexing.
- **`app/services/ingestion/slack_manual.py`** -- Parser for manually exported Slack conversations (text or JSON format). Normalizes to the same internal representation as admin exports.
- **`app/services/ingestion/slack_api.py`** -- Parser for output from the `chiefops-slack-extract.py` script. Reads the `_metadata.json` marker file and processes JSON files matching admin export structure.
- **`app/services/ingestion/jira_csv.py`** -- Jira CSV parser. Detects column headers (`Issue key`, `Summary`, `Status`, `Assignee`, `Reporter`, `Priority`, `Created`, `Updated`, `Description`). Handles both "All fields" and "Current fields" export variants. Writes to `jira_issues` collection.
- **`app/services/ingestion/drive.py`** -- Google Drive folder processor. Iterates files, detects types by extension, sends to Citex for full-text indexing. Stores file metadata in `drive_files` collection.
- **`app/services/ingestion/hasher.py`** -- SHA-256 content hashing for deduplication. Before processing any file, check if the hash already exists in the `ingestion_hashes` collection. Skip if duplicate.
- **`app/citex/indexer.py`** -- Helper that sends parsed documents to the Citex REST API for indexing. Handles chunking large documents into Citex-compatible payloads. Associates each document with a `project_id`.

### Frontend Tasks

- **`src/pages/DataUpload.tsx`** -- Full-page upload interface with drag-and-drop zone, file list, and ingestion history.
- **`src/components/ingestion/DropZone.tsx`** -- Drag-and-drop area using `react-dropzone`. Accepts ZIP, CSV, PDF, DOCX, PPTX, XLSX, TXT, MD, HTML, JSON files. Visual feedback on drag-over.
- **`src/components/ingestion/UploadProgress.tsx`** -- Per-file progress bar. Connects to the WebSocket endpoint for real-time updates. Shows: filename, detected type (Slack Admin Export, Jira CSV, etc.), progress percentage, records processed count.
- **`src/components/ingestion/IngestionSummary.tsx`** -- Post-upload summary card. Shows total files processed, records ingested, duplicates skipped, errors encountered.
- **`src/stores/ingestionStore.ts`** -- Zustand store: `jobs`, `activeJobId`, `uploadFile()`, `connectWebSocket()`, `addJobUpdate()`.
- **`src/hooks/useWebSocket.ts`** -- Generic WebSocket connection hook with auto-reconnect.
- Sidebar link to "Data Upload" page becomes active.

### Key Deliverables

- COO drags a Slack Admin Export ZIP onto the upload area and sees real-time progress as messages are parsed
- COO uploads a Jira CSV and sees tasks appear in the system
- COO uploads a folder of Drive documents (PDF, DOCX) and the system indexes them in Citex
- Duplicate files are automatically detected and skipped
- After upload completes, the COO sees a summary: "Processed 3 files: 12,847 Slack messages, 342 Jira tasks, 28 documents indexed"

### Definition of Done

- [ ] File upload API accepts multipart form data and returns a job ID
- [ ] Slack Admin Export ZIP is fully parsed: users, channels, messages stored in MongoDB, message content indexed in Citex
- [ ] Slack manual export (text format) is parsed and stored
- [ ] Jira CSV with standard columns is parsed into `jira_issues` collection
- [ ] Google Drive documents (PDF, DOCX at minimum) are sent to Citex for indexing
- [ ] Content hashing prevents re-processing of identical files
- [ ] WebSocket delivers real-time progress updates to the frontend
- [ ] Frontend displays drag-and-drop upload area, per-file progress, and completion summary
- [ ] Error handling: corrupt files, unsupported formats, and partial failures are reported (not crashed on)
- [ ] At least 3 pytest test cases per parser (happy path, malformed input, empty input)

---

## 7. Sprint 2: AI Layer & Memory (Weeks 5--6)

### Goal

Wire up the AI adapter layer and three-layer memory system so the COO can chat with ChiefOps and receive intelligent, context-aware responses that reference ingested data through Citex RAG.

### Backend Tasks

- **`app/ai/adapter.py`** -- Abstract base class `AIAdapter` with `generate()` and `generate_structured()` methods as defined in [06-AI-LAYER.md](./06-AI-LAYER.md). Define `AIRequest` and `AIResponse` Pydantic models.
- **`app/ai/cli_adapter.py`** -- CLI subprocess adapter. Spawns Claude CLI (or Codex CLI, Gemini CLI based on config) as a subprocess. Pipes system prompt + user prompt via stdin, reads response from stdout. Handles timeouts, process errors, and stderr logging. Parses JSON when `response_schema` is provided.
- **`app/ai/openrouter_adapter.py`** -- OpenRouter HTTP adapter (placeholder implementation). Uses `httpx` to call the OpenRouter API. Reads `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` from config.
- **`app/ai/factory.py`** -- Factory function `get_adapter()` that reads `AI_ADAPTER` config and returns the correct adapter instance. Supports `"cli"` and `"openrouter"`.
- **`app/ai/prompts/base.py`** -- `PromptTemplate` base class with `render()` method accepting context variables.
- **`app/ai/prompts/conversation.py`** -- General conversation prompt templates. Includes the system prompt that establishes ChiefOps's persona as a COO's operations advisor.
- **`app/services/memory/manager.py`** -- `MemoryManager` class. Coordinates the three memory layers (hard facts, compacted summaries, recent turns) as described in [04-MEMORY-SYSTEM.md](./04-MEMORY-SYSTEM.md).
- **`app/services/memory/hard_facts.py`** -- Hard fact extraction. After each conversation turn, uses the AI adapter to detect if the user stated a hard fact (correction, deadline, role assignment). Stores in the `hard_facts` collection. Hard facts are never compacted or removed.
- **`app/services/memory/compactor.py`** -- Progressive summary compaction. When the conversation turn count exceeds the compaction threshold (default: 20 turns), the oldest turns beyond the recent window (10 turns) are summarized by the AI and merged into the running summary. The raw turns are then archived.
- **`app/services/memory/assembler.py`** -- Context assembler. For every AI request, builds the context payload: hard facts (always included) + compacted summary + last 10 raw turns + Citex RAG chunks relevant to the query.
- **`app/services/conversation/service.py`** -- Conversation orchestrator. Receives user input, assembles context via `MemoryManager`, queries Citex for relevant chunks, calls the AI adapter with full context, streams the response, stores the turn in MongoDB.
- **`app/services/conversation/intent.py`** -- Intent detection stub. Classifies user input as: `query` (asking for information), `correction` (correcting a fact), `command` (add widget, generate report), or `chat` (general conversation). Sprint 2 implements `query` and `chat`; `correction` and `command` are handled in later sprints.
- **`app/services/conversation/streaming.py`** -- SSE (Server-Sent Events) streaming handler. Wraps AI adapter output into an SSE stream that the frontend can consume incrementally.
- **`app/api/v1/conversation.py`** -- Endpoints:
  - `POST /api/v1/conversation/message` -- Send a message. Returns streaming SSE response.
  - `GET /api/v1/conversation/history` -- Retrieve conversation history (paginated).
  - `DELETE /api/v1/conversation/history` -- Clear conversation history (keeps hard facts).
- **`app/models/conversation.py`** -- Pydantic models: `ConversationTurn` (role, content, timestamp, turn_number), `MemoryStream` (project_id, hard_facts, summary, recent_turns), `HardFact` (fact_text, source, created_at, category).

### Frontend Tasks

- **`src/components/chat/ChatSidebar.tsx`** -- Expandable chat sidebar panel. Toggles open/closed. Positioned on the right side of the screen. Shows conversation history and input field.
- **`src/components/chat/ChatInput.tsx`** -- Text input with send button. Supports Enter to send, Shift+Enter for newline.
- **`src/components/chat/ChatMessage.tsx`** -- Message bubble component. User messages right-aligned (blue), AI responses left-aligned (gray). Supports markdown rendering.
- **`src/components/chat/StreamingResponse.tsx`** -- Renders the AI response as it streams in, character by character, with a blinking cursor animation.
- **`src/hooks/useChat.ts`** -- Hook that manages sending messages and consuming SSE streams. Handles connection errors and retries.
- **`src/hooks/useStreamingResponse.ts`** -- Hook for consuming SSE (EventSource) streams from the conversation endpoint.
- **`src/stores/chatStore.ts`** -- Zustand store: `messages`, `isStreaming`, `sendMessage()`, `clearHistory()`.
- Chat sidebar is accessible from every page via a toggle button in the top bar.

### Key Deliverables

- COO types "What projects do we have?" and receives an AI-generated response based on ingested data
- Responses reference specific Slack messages or Jira tasks via Citex RAG (e.g., "Based on Slack conversations in #project-alpha, the team discussed...")
- Conversation history persists across page reloads
- Hard facts from COO corrections are extracted and stored permanently
- AI responses stream in real-time (not waiting for the full response)

### Definition of Done

- [ ] CLI adapter successfully spawns a subprocess and returns AI responses
- [ ] OpenRouter adapter placeholder is implemented (returns mock response if no API key)
- [ ] `AI_ADAPTER` env var switches between `cli` and `openrouter` without code changes
- [ ] Memory manager assembles context with hard facts + summary + recent turns
- [ ] Citex RAG chunks are included in the AI context for relevant queries
- [ ] Conversation turns are persisted in MongoDB
- [ ] Hard fact extraction identifies COO corrections and stores them
- [ ] Compaction trigger fires after 20 turns and compresses old turns into a summary
- [ ] SSE streaming works end-to-end: backend streams, frontend renders incrementally
- [ ] Chat sidebar is accessible from all pages
- [ ] At least 5 pytest test cases for the conversation flow (with a mock AI adapter)

---

## 8. Sprint 3: People Intelligence (Weeks 7--8)

### Goal

Build the people identification pipeline that extracts, resolves, and enriches person records from ingested Slack, Jira, and Drive data, with AI-powered role detection and COO correction capabilities.

### Backend Tasks

- **`app/services/people/pipeline.py`** -- The 5-step people identification pipeline from [09-PEOPLE-INTELLIGENCE.md](./09-PEOPLE-INTELLIGENCE.md):
  1. **Build Initial Directory** -- Extract raw person records from each data source (Slack `users.json`, Jira CSV assignee/reporter columns, Drive file metadata).
  2. **Cross-Source Entity Resolution** -- Match identities across sources using fuzzy name matching, email matching, and Slack user ID correlation.
  3. **AI-Powered Role Detection** -- Send person activity data (messages sent, channels active in, tasks assigned, task types) to the AI adapter for role inference.
  4. **Activity Level Calculation** -- Compute `activity_level` (very_active, active, moderate, quiet, inactive) from message frequency, task completion rate, and recency of last activity.
  5. **Persist to MongoDB** -- Write unified `Person` documents to the `people` collection with all resolved fields.
- **`app/services/people/resolver.py`** -- Cross-source entity resolution. Uses fuzzy string matching (Levenshtein distance) on display names, exact matching on email addresses, and Slack user ID to Jira username correlation. Produces a merged person record with `source_ids` pointing back to each original identity.
- **`app/services/people/role_detector.py`** -- AI-powered role detection. Builds a prompt containing the person's activity data (channels, message samples, task types, task descriptions) and asks the AI to infer their role, department, and seniority level. Uses structured output (JSON schema) to get consistent role labels.
- **`app/services/people/corrections.py`** -- COO correction handler. When the COO says "Raj is the lead architect," the intent detector classifies it as a `correction`, extracts the person name and new role, updates the `people` collection with `role_source: "coo_corrected"`, stores it as a hard fact in the memory system, and triggers a re-analysis cascade for any summaries or analysis that referenced this person.
- **`app/api/v1/people.py`** -- Endpoints:
  - `GET /api/v1/people` -- List all people (with pagination, filtering by activity_level, department, project).
  - `GET /api/v1/people/{person_id}` -- Single person detail with full activity breakdown.
  - `PATCH /api/v1/people/{person_id}` -- Manual COO correction (role, department, name).
  - `POST /api/v1/people/reprocess` -- Trigger re-running the people pipeline on existing data.
- **`app/models/person.py`** -- Finalize the `Person`, `SourceReference`, and `EngagementMetrics` Pydantic models as defined in [03-DATA-MODELS.md](./03-DATA-MODELS.md).
- **`app/ai/prompts/people.py`** -- Prompt templates for role detection, entity resolution disambiguation (when fuzzy matching finds multiple candidates), and correction interpretation.
- Update **`app/services/conversation/intent.py`** -- Add `correction` intent classification. Detect statements like "X is the Y" or "Actually, X handles Y" and route to the correction handler.

### Frontend Tasks

- **`src/pages/PeopleDirectory.tsx`** -- Full page showing all identified people in a card grid or table view. Supports filtering by activity level and department. Search bar for name lookup.
- **`src/components/people/PersonCard.tsx`** -- Card showing: name, role, department, activity level indicator (color-coded dot), task counts, avatar (or initials fallback).
- **`src/components/people/PersonDetail.tsx`** -- Expanded detail view: full activity breakdown, source references (which Slack user, which Jira account), project involvement, engagement metrics, role source indicator (AI-identified vs. COO-corrected).
- **`src/components/people/RoleBadge.tsx`** -- Small badge showing the role with a visual indicator of source: brain icon for AI-identified, checkmark icon for COO-corrected.
- **`src/stores/peopleStore.ts`** -- Zustand store: `people`, `selectedPerson`, `filters`, `fetchPeople()`, `fetchPersonDetail()`.
- Sidebar "People" link becomes active and navigates to the directory.

### Key Deliverables

- After Slack and Jira data is ingested, the People page shows all identified people with AI-detected roles
- People from different sources (e.g., "Raj Kumar" in Slack and "raj.kumar" in Jira) are merged into a single person record
- The COO can say "Raj is the lead architect" in the chat, and the People page updates to show "Lead Architect" with a "COO-corrected" badge
- Each person card shows activity level, tasks assigned/completed, and department

### Definition of Done

- [ ] People pipeline runs automatically after ingestion completes
- [ ] Cross-source entity resolution merges Slack + Jira + Drive identities into unified person records
- [ ] AI role detection assigns roles to at least 80% of identified people
- [ ] COO can correct roles via chat ("Raj is the lead architect") and the correction persists as a hard fact
- [ ] COO can correct roles via the PATCH endpoint
- [ ] People directory page renders all people with filtering and search
- [ ] Person detail view shows source references and engagement metrics
- [ ] `role_source` field correctly distinguishes AI-identified from COO-corrected
- [ ] Correction cascading updates any existing summaries referencing the corrected person
- [ ] At least 5 pytest test cases: pipeline happy path, entity resolution with ambiguity, role detection with mock AI, correction handling, activity level calculation

---

## 9. Sprint 4: Project Intelligence (Weeks 9--10)

### Goal

Build the project analysis engine that synthesizes ingested data into project status, sprint health, gap detection, backward planning, and technical feasibility assessments.

### Backend Tasks

- **`app/services/projects/analyzer.py`** -- Project analysis orchestrator. Given a `project_id`, gathers all related data (Jira tasks, Slack messages, Drive documents, people assignments) and runs the analysis sub-services. Produces a comprehensive `ProjectAnalysis` result.
- **`app/services/projects/health.py`** -- Sprint health calculation:
  - **Completion rate** -- Tasks completed / total tasks in current sprint
  - **Velocity trend** -- Points completed per sprint over last 3 sprints (from Jira data)
  - **Blocker count** -- Tasks with "Blocked" status or blockers mentioned in Slack
  - **Operational health score** -- Composite 0--100 score combining completion rate, velocity trend, team engagement, and blocker severity. Weights configurable.
- **`app/services/projects/gaps.py`** -- Gap detection and backward planning:
  - **Missing tasks** -- AI analyzes project requirements (from Drive docs + Slack discussions) against Jira tasks to identify work not yet captured in tickets
  - **Missing prerequisites** -- For each task, AI checks if dependent tasks exist and are scheduled before it
  - **Backward planning** -- Given a deadline, work backward from deliverables to identify the critical path and flag tasks that must start by specific dates
  - **Capacity analysis** -- Compare required work against available team capacity based on people assignments and activity levels
- **`app/services/projects/feasibility.py`** -- Technical feasibility analysis:
  - **Readiness checklist** -- AI generates a list of technical prerequisites (infrastructure, APIs, libraries, skills) based on project requirements
  - **Risk identification** -- Flag areas where requirements are vague, dependencies are external, or team lacks expertise
  - **Questions for the architect** -- AI generates targeted technical questions the COO should ask the engineering lead
- **`app/api/v1/projects.py`** -- Endpoints:
  - `GET /api/v1/projects` -- List all projects with summary health scores.
  - `GET /api/v1/projects/{project_id}` -- Full project detail with analysis.
  - `POST /api/v1/projects` -- Create a project manually (name, description, deadline).
  - `PATCH /api/v1/projects/{project_id}` -- Update project metadata.
  - `GET /api/v1/projects/{project_id}/analysis` -- Full analysis result (health, gaps, feasibility).
  - `POST /api/v1/projects/{project_id}/analyze` -- Trigger a fresh analysis run.
- **`app/models/project.py`** -- Finalize `Project`, `SprintHealth`, `GapAnalysis`, `TechnicalFeasibility`, `OperationalHealthScore` models.
- **`app/ai/prompts/project.py`** -- Prompt templates for: project status assessment, gap detection, backward planning, technical feasibility, and architect question generation.
- Update **`app/services/conversation/intent.py`** -- Route project-related queries ("How's Project Alpha?", "Are we on track for the deadline?") to the project analysis service.

### Frontend Tasks

- **`src/pages/ProjectDetail.tsx`** -- Single project deep-dive page. Layout:
  - Header: project name, status badge, health score circle, deadline countdown
  - Sprint Health section: completion bar, velocity trend line chart, blocker list
  - Gap Analysis section: missing tasks list, missing prerequisites, backward planning timeline
  - Technical Feasibility section: readiness checklist, risk flags, architect questions
  - People section: team members involved (using PersonCard components)
- **`src/stores/projectStore.ts`** -- Zustand store: `projects`, `selectedProject`, `analysis`, `fetchProjects()`, `fetchProjectDetail()`, `triggerAnalysis()`.
- **`src/components/shared/HealthScore.tsx`** -- Circular health score indicator (0--100) with color gradient (red < 40, yellow 40--70, green > 70) and directional trend arrow.
- Sidebar "Projects" link becomes active. Project list page shows cards for each project with health scores.

### Key Deliverables

- COO navigates to a project page and sees a comprehensive analysis: health score, sprint progress, identified gaps, and feasibility assessment
- COO asks "How's Project Alpha?" in the chat and receives an AI-generated summary referencing specific data points
- COO asks "Are we on track for the March 15 deadline?" and gets backward planning analysis with flag for at-risk tasks
- COO asks "What should I ask the architect about the database migration?" and gets targeted technical questions

### Definition of Done

- [ ] Projects are auto-created from ingested data (grouped by Jira project key and Slack channel patterns)
- [ ] Health score computation produces a 0--100 score with breakdown
- [ ] Gap detection identifies at least missing tasks and missing prerequisites from sample data
- [ ] Backward planning computes a critical path from a given deadline
- [ ] Technical feasibility generates readiness checklist and architect questions
- [ ] Project detail page renders all analysis sections
- [ ] Chat queries about projects return analysis-backed responses
- [ ] Health score component renders with correct color coding and trend arrow
- [ ] At least 5 pytest test cases: health calculation, gap detection with mock AI, backward planning with deadline, feasibility analysis, project query via conversation

---

## 10. Sprint 5: Dashboard Foundation (Weeks 11--12)

### Goal

Implement the dashboard and widget system -- the Main Dashboard with fixed KPI layout, the data query engine that transforms `DataQuery` specs into MongoDB aggregation pipelines, and NL-driven widget creation through the chat interface.

### Backend Tasks

- **`app/api/v1/dashboards.py`** -- Endpoints:
  - `GET /api/v1/dashboards` -- List all dashboards (main + project dashboards).
  - `GET /api/v1/dashboards/{dashboard_id}` -- Single dashboard with all widget specs.
  - `POST /api/v1/dashboards` -- Create a custom dashboard (scoped to a project).
  - `PATCH /api/v1/dashboards/{dashboard_id}` -- Update dashboard metadata or layout.
  - `DELETE /api/v1/dashboards/{dashboard_id}` -- Delete a custom dashboard (main and static project dashboards cannot be deleted).
- **`app/api/v1/widgets.py`** -- Endpoints:
  - `GET /api/v1/widgets/{widget_id}` -- Get widget spec.
  - `GET /api/v1/widgets/{widget_id}/data` -- Execute the widget's `DataQuery` and return results.
  - `POST /api/v1/dashboards/{dashboard_id}/widgets` -- Add a widget to a dashboard (from a WidgetSpec).
  - `PATCH /api/v1/widgets/{widget_id}` -- Update a widget (title, position, data query).
  - `DELETE /api/v1/widgets/{widget_id}` -- Remove a widget from its dashboard.
  - `POST /api/v1/widgets/generate` -- NL-to-widget: receive natural language description, return a generated WidgetSpec.
- **`app/services/widgets/query_engine.py`** -- Data query engine. Translates a `DataQuery` JSON spec (collection, match filters, group-by, sort, limit) into a MongoDB aggregation pipeline. Executes the pipeline via Motor and returns structured results. Supports these query types:
  - `count` -- Count documents matching a filter
  - `group_count` -- Group by a field and count per group
  - `time_series` -- Group by date bucket (day/week/month) with aggregation
  - `top_n` -- Sort by a field and take top N results
  - `aggregate` -- Custom aggregation with sum/avg/min/max
- **`app/services/widgets/spec_generator.py`** -- NL-to-WidgetSpec generator. Takes a natural language request ("Show me tasks per person"), queries the AI adapter with the available data schema, and produces a `WidgetSpec` JSON including: widget type, title, data query, display config (colors, labels, axes). Uses structured output for reliable JSON generation.
- **`app/services/widgets/cache.py`** -- Redis caching layer. Caches widget query results with a configurable TTL (default: 5 minutes). Cache key is a hash of the DataQuery spec. Invalidation on data ingestion or explicit refresh.
- **`app/models/dashboard.py`** -- Finalize `Dashboard`, `WidgetSpec`, `DataQuery`, `WidgetPosition` (row, col, width, height on the 12-column grid) models as defined in [03-DATA-MODELS.md](./03-DATA-MODELS.md) and [10-DASHBOARD-AND-WIDGETS.md](./10-DASHBOARD-AND-WIDGETS.md).
- **`app/ai/prompts/widget.py`** -- Prompt templates for NL-to-WidgetSpec generation. Includes the full schema of available collections and fields so the AI can compose valid DataQuery specs.
- Update **`app/services/conversation/intent.py`** -- Add `command` intent for widget creation ("Show me tasks per person", "Add a chart of sprint velocity"). Route to the widget spec generator.

### Frontend Tasks

- **`src/pages/MainDashboard.tsx`** -- Full implementation of the Main Dashboard from [10-DASHBOARD-AND-WIDGETS.md](./10-DASHBOARD-AND-WIDGETS.md). Fixed layout with:
  - Top bar: Health score (HealthScore component), quick search, alert count
  - AI briefing text panel (fetched from a briefing widget)
  - Project overview cards (one per project, showing name, health score, status)
  - Team activity summary (summary text widget)
- **`src/pages/CustomDashboard.tsx`** -- Dynamic dashboard page. Reads widget specs from the API and renders them in a 12-column CSS Grid layout. Supports the COO adding widgets via chat.
- **`src/components/widgets/WidgetRenderer.tsx`** -- Dispatch component. Reads the `widget_type` from the WidgetSpec and lazy-loads the correct widget component (BarChart, LineChart, KpiCard, DataTable, SummaryText).
- **`src/components/widgets/BarChart.tsx`** -- ECharts bar chart. Receives data from the widget data endpoint. Configurable axes, colors, and labels from the WidgetSpec.
- **`src/components/widgets/LineChart.tsx`** -- ECharts line chart with time-series support.
- **`src/components/widgets/KpiCard.tsx`** -- Single KPI metric card: large number, label, optional trend indicator (up/down arrow with percentage change).
- **`src/components/widgets/DataTable.tsx`** -- Sortable, paginated data table. Column definitions from WidgetSpec.
- **`src/components/widgets/SummaryText.tsx`** -- AI-generated text block with markdown rendering.
- **`src/hooks/useWidgetData.ts`** -- Hook that fetches widget data from `/api/v1/widgets/{id}/data`, handles loading/error states, and supports manual refresh.
- **`src/stores/dashboardStore.ts`** -- Zustand store: `dashboards`, `activeDashboard`, `widgets`, `fetchDashboard()`, `addWidget()`, `removeWidget()`, `updateWidgetPosition()`.
- 12-column CSS Grid layout defined in Tailwind config or dedicated CSS module.

### Key Deliverables

- Main Dashboard shows health score, project overview cards, and AI briefing text
- COO says "Show me tasks per person" in the chat, and a bar chart widget appears on the custom dashboard
- COO says "Add a KPI showing total open tasks" and a KPI card appears
- Widgets load data from MongoDB aggregation queries and display charts/tables
- Widget data is cached in Redis (subsequent loads are fast)

### Definition of Done

- [ ] Main Dashboard renders with health score, project cards, and briefing text
- [ ] Custom Dashboard renders widgets in a 12-column grid layout
- [ ] Data query engine translates DataQuery specs into MongoDB aggregation pipelines and returns correct results
- [ ] 5 widget types render correctly: BarChart, LineChart, KpiCard, DataTable, SummaryText
- [ ] NL-to-widget generation: a natural language request produces a valid WidgetSpec that renders a working widget
- [ ] Widget data endpoint returns cached results from Redis on subsequent calls
- [ ] Cache invalidation works on data ingestion
- [ ] Widget creation via chat: user types a request, widget appears on the custom dashboard
- [ ] Widget CRUD operations work: create, read, update position, delete
- [ ] At least 5 pytest test cases: query engine (group_count, time_series, top_n), widget spec generation with mock AI, cache hit/miss, dashboard CRUD

---

Continued in [Implementation Plan -- Part B](./11B-IMPLEMENTATION-PLAN-CONTINUED.md) -- Sprints 6--9, testing strategy, risk management, and deployment guide.
