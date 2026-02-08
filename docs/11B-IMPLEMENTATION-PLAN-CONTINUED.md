# Implementation Plan -- Part B: ChiefOps -- Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan -- Part A](./11-IMPLEMENTATION-PLAN.md) | **Implementation Plan -- Part B** | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

> **This is Part B of the Implementation Plan.** For project setup, repository structure, Docker Compose configuration, and Sprints 0-5, see [Part A](./11-IMPLEMENTATION-PLAN.md).

---

## Table of Contents

1. [Sprint 6: Advanced Dashboard & Widgets (Weeks 13-14)](#sprint-6-advanced-dashboard--widgets-weeks-13-14)
2. [Sprint 7: Report Generation (Weeks 15-16)](#sprint-7-report-generation-weeks-15-16)
3. [Sprint 8: Technical Advisor & Polish (Weeks 17-18)](#sprint-8-technical-advisor--polish-weeks-17-18)
4. [Sprint 9: Integration, Testing & Hardening (Weeks 19-20)](#sprint-9-integration-testing--hardening-weeks-19-20)
5. [Sprint Summary Timeline](#sprint-summary-timeline)
6. [Testing Strategy](#testing-strategy)
7. [Risk Management](#risk-management)
8. [Deployment Guide](#deployment-guide)
9. [Definition of Done -- Step Zero Complete](#definition-of-done----step-zero-complete)

---

## Sprint 6: Advanced Dashboard & Widgets (Weeks 13-14)

### Goal

Implement the remaining five widget types, NL widget editing and deletion, project-specific dashboard auto-creation, and full dashboard persistence -- enabling the COO to manage dashboards entirely through conversation.

### Backend Tasks

- **Pie chart data query handler** -- Extend `app/services/widgets/data_query_engine.py` to support aggregation pipelines that produce label/value pairs for pie and donut charts. Include `top_n` support with an "Other" rollup for categories exceeding the limit.
- **Gantt chart data query handler** -- Build a Gantt-specific aggregation in `app/services/widgets/gantt_query.py` that pulls tasks with `start_date`, `end_date`, `assignee`, `status`, and `project_id` from `jira_tasks`. Map statuses to color codes. Support milestone markers (tasks with zero duration).
- **Person grid data assembly** -- Create `app/services/widgets/person_grid_query.py` to aggregate per-person metrics: task count, completion rate, last active timestamp, role, and avatar URL. Pull from `people` and `jira_tasks` collections.
- **Timeline data assembly** -- Implement `app/services/widgets/timeline_query.py` to collect chronological events (task completions, ingestion events, alert triggers, report generations) from multiple collections with a unified `{ timestamp, event_type, title, detail }` shape.
- **Activity feed data assembly** -- Implement `app/services/widgets/activity_feed_query.py` to return a paginated, reverse-chronological stream of events sourced from `slack_messages`, `jira_tasks`, and `ingestion_jobs`. Support cursor-based pagination.
- **NL widget editing endpoint** -- Add `PATCH /api/v1/dashboards/{dashboard_id}/widgets/{widget_id}/nl-edit` in `app/routers/dashboard_router.py`. Accept `{ message: string }` and route through the AI layer to produce a modified `widget_spec`. The AI receives the current widget spec plus the edit instruction and returns the updated spec.
- **NL widget deletion** -- Add intent detection for deletion phrases ("remove that chart", "delete the pie chart") in the NL query pipeline. When detected, resolve the target widget by title or position and call `DELETE /api/v1/dashboards/{dashboard_id}/widgets/{widget_id}`.
- **Project dashboard auto-creation** -- In `app/services/dashboard_service.py`, add `ensure_project_dashboards(project_id)` that creates both the static and custom dashboard documents on first project view if they do not already exist. The static dashboard is pre-populated with the standard widget set (Gantt, person grid, task breakdown bar chart, risk panel, completion KPI).
- **Dashboard state persistence** -- Ensure all widget CRUD operations write through to MongoDB `dashboard_widgets` collection with `updated_at` timestamps. Add `GET /api/v1/dashboards/{dashboard_id}/state` endpoint that returns the full dashboard layout including widget positions and sizes.

### Frontend Tasks

- **`PieChartWidget` component** (`src/components/widgets/PieChartWidget.tsx`) -- Render ECharts pie/donut chart from `chart_spec`. Support label formatting, percentage display, legend placement, and responsive resizing.
- **`GanttWidget` component** (`src/components/widgets/GanttWidget.tsx`) -- Implement ECharts custom series with `renderItem` callback for Gantt bars. Each bar represents a task with a horizontal span from `start_date` to `end_date`, color-coded by status. Milestone markers rendered as diamonds. Category axis shows assignees or task names. Tooltip shows full task detail on hover. Horizontal scrolling for timelines exceeding the viewport.
- **`PersonGridWidget` component** (`src/components/widgets/PersonGridWidget.tsx`) -- CSS Grid of avatar cards. Each card shows: avatar (initials fallback), name, role badge, task count, completion percentage ring, last active indicator (green/yellow/red). Cards are clickable to navigate to person detail.
- **`TimelineWidget` component** (`src/components/widgets/TimelineWidget.tsx`) -- Vertical timeline with alternating left/right event cards. Each card has a timestamp, event icon (color-coded by type), title, and expandable detail. Supports infinite scroll for long timelines.
- **`ActivityFeedWidget` component** (`src/components/widgets/ActivityFeedWidget.tsx`) -- Scrollable card stream with real-time append via WebSocket. Each entry shows: source icon (Slack/Jira/Drive), timestamp, actor, action summary. Cursor-based "load more" at the bottom.
- **NL widget edit integration** -- Extend the chat sidebar to detect AI responses that include a `widget_update` action. When the AI modifies a widget, the frontend receives the new spec via WebSocket and re-renders the widget in place without a full dashboard reload.
- **Widget deletion UX** -- When the AI confirms deletion, animate the widget out (fade + collapse) and remove it from the Zustand dashboard store.
- **Dashboard Zustand store enhancements** (`src/stores/dashboardStore.ts`) -- Add actions: `updateWidget`, `removeWidget`, `setDashboardLayout`. Persist optimistic updates and reconcile with server responses.
- **Project dashboard auto-navigation** -- When the user navigates to `/projects/:projectId`, the frontend calls `GET /api/v1/dashboards?project_id={id}` and renders the static dashboard. A tab or button switches to the custom dashboard at `/projects/:projectId/custom`.

### Key Deliverables

At the end of Sprint 6, the COO can:
- View all 10 widget types rendered on dashboards (bar, line, pie, Gantt, table, kpi_card, summary_text, person_grid, timeline, activity_feed)
- Say "Make that chart show only engineering" and the widget updates in place
- Say "Remove the Gantt chart" and the widget disappears
- Navigate to any project and see an auto-created static dashboard with standard widgets
- Switch to the custom dashboard tab and build a personalized view through conversation

### Definition of Done

- [ ] All 10 widget types render correctly with sample data
- [ ] Gantt chart supports horizontal scrolling and milestone markers
- [ ] Person grid cards display correct metrics from people + tasks collections
- [ ] NL widget edit round-trip completes in under 5 seconds
- [ ] Widget deletion removes the widget from both the UI and MongoDB
- [ ] Project dashboards are auto-created on first navigation
- [ ] Dashboard state persists across browser refreshes
- [ ] All new widget components have Vitest unit tests with mocked ECharts
- [ ] Backend data query handlers have pytest tests with fixture data

---

## Sprint 7: Report Generation (Weeks 15-16)

### Goal

Implement the full report generation pipeline -- from NL trigger through AI-generated report specs, interactive preview, NL editing, and professional PDF export with embedded charts.

### Backend Tasks

- **Report spec Pydantic model** -- Define `ReportSpec` in `app/models/report.py` with fields: `report_id`, `report_type` (enum of 8 types), `title`, `time_scope`, `audience`, `projects`, `sections` (list of `ReportSection`), `metadata`, `created_at`, `updated_at`. Each `ReportSection` has: `section_id`, `section_type` (narrative, metrics_grid, chart, table, card_list, checklist), `title`, `content` (type-specific payload), `order`.
- **Report template definitions** -- Create `app/services/reports/templates/` directory with template configs for each of the 8 report types: `board_ops_summary`, `project_status`, `team_performance`, `risk_assessment`, `sprint_report`, `resource_utilization`, `technical_due_diligence`, `custom`. Each template defines default sections, expected data queries, and tone/audience hints.
- **NL report intent detection** -- Extend the intent classifier in `app/services/ai/intent_detector.py` to recognize report generation requests. Extract parameters: `report_type`, `time_scope`, `projects`, `audience`, `specific_sections_requested`.
- **AI report spec generation** -- Implement `app/services/reports/report_generator.py` with `generate_report_spec(intent, data_context)`. Sends the template structure, available data summary, and COO request to the AI adapter. The AI returns a complete `ReportSpec` JSON with all sections populated -- narratives written, metrics computed, chart specs generated.
- **Report data assembly** -- Create `app/services/reports/data_assembler.py` that gathers all data needed for a report: project summaries from `projects`, task metrics from `jira_tasks`, people data from `people`, communication insights from `slack_messages`, health scores from `health_scores`. Passes this data context to the AI for report generation.
- **NL report editing** -- Implement `app/services/reports/report_editor.py` with `edit_report(report_id, edit_instruction)`. Loads the current `ReportSpec`, sends it to the AI with the edit instruction ("Add a section on hiring", "Remove the Gantt chart", "Make the summary shorter"), and receives an updated spec. Supports section CRUD: add, remove, reorder, modify content.
- **Report API endpoints** -- Add to `app/routers/report_router.py`:
  - `POST /api/v1/reports/generate` -- trigger report generation from NL
  - `GET /api/v1/reports/{report_id}` -- fetch report spec
  - `PATCH /api/v1/reports/{report_id}/edit` -- NL edit
  - `POST /api/v1/reports/{report_id}/export/pdf` -- trigger PDF export
  - `GET /api/v1/reports` -- list reports with pagination
  - `DELETE /api/v1/reports/{report_id}` -- delete report
- **PDF export pipeline** -- Implement `app/services/reports/pdf_exporter.py`:
  1. Load the `ReportSpec` from MongoDB
  2. Render each chart section to SVG using `pyecharts` (server-side ECharts renderer) -- mirrors the same chart specs used by `echarts-for-react` on the frontend
  3. Feed the report spec + rendered SVGs into Jinja2 HTML templates (`app/templates/reports/`)
  4. Convert HTML to PDF via WeasyPrint with CSS for: page breaks, headers/footers, page numbers, table of contents, YENSI branding
  5. Store the PDF in the `exports` Docker volume and return a download URL
- **Jinja2 report templates** -- Create `app/templates/reports/base.html` (shared layout with branding, header, footer, page numbers) and per-report-type templates that extend the base. Section templates: `narrative.html`, `metrics_grid.html`, `chart.html`, `table.html`, `card_list.html`, `checklist.html`.
- **Report history storage** -- Store completed reports in the `report_history` MongoDB collection with: `report_id`, `report_spec` (snapshot), `pdf_path`, `generated_at`, `generated_by` (always "coo" in Step Zero).

### Frontend Tasks

- **Report preview page** (`src/pages/ReportPreviewPage.tsx`) -- Full-page report viewer. Renders the `ReportSpec` into a paginated, scrollable document with:
  - Title page with report type, date range, and YENSI branding
  - Table of contents with clickable section links
  - Each section rendered by type: narrative as formatted text, metrics as card grids, charts as live ECharts instances, tables with sorting/filtering, checklists with status indicators
  - Page break indicators showing where PDF pages will split
- **Report section components** -- Create `src/components/reports/` directory:
  - `NarrativeSection.tsx` -- Markdown-rendered text blocks
  - `MetricsGridSection.tsx` -- KPI cards in a responsive grid
  - `ChartSection.tsx` -- ECharts chart with the same spec used for widgets
  - `TableSection.tsx` -- Sortable data table
  - `CardListSection.tsx` -- Vertical list of detail cards (risks, action items)
  - `ChecklistSection.tsx` -- Checklist items with status badges
- **NL report editing UI** -- The chat sidebar recognizes report context. When the COO is viewing a report preview, NL commands like "Add a section on hiring" are routed to the report edit endpoint. The preview re-renders after each edit with a smooth transition animation.
- **PDF download button** -- "Export to PDF" button on the report preview page. Triggers `POST /api/v1/reports/{id}/export/pdf`, shows a progress spinner, and initiates browser download when ready.
- **Report list page** (`src/pages/ReportsPage.tsx`) -- Table of previously generated reports with columns: title, type, date, project scope. Row click opens the report preview. Actions: re-export PDF, delete.
- **Report generation flow** -- When the AI determines a report should be generated (from a chat message), the frontend receives a `report_generated` action via WebSocket containing the `report_id`. The UI displays a toast notification with a "View Report" link that navigates to the preview page.

### Key Deliverables

At the end of Sprint 7, the COO can:
- Say "Generate a board ops summary for January" and see a professional report preview in seconds
- Scroll through the report with live charts, formatted metrics, and narrative sections
- Say "Add a section on hiring" and the report updates with a new section
- Say "Remove the Gantt chart" and the chart section disappears from the report
- Click "Export to PDF" and download a print-ready document with YENSI branding, page numbers, embedded charts, and table of contents
- View and manage all previously generated reports

### Definition of Done

- [ ] All 8 report types generate correctly from NL triggers
- [ ] Report preview renders all 6 section types (narrative, metrics, chart, table, cards, checklist)
- [ ] NL report editing supports add, remove, and modify operations
- [ ] PDF export produces a correctly formatted document with embedded SVG charts
- [ ] PDF includes page numbers, headers, footers, and YENSI branding
- [ ] Report history persists in MongoDB and is browsable in the UI
- [ ] Report generation completes in under 15 seconds
- [ ] PDF export completes in under 10 seconds
- [ ] Backend report services have pytest tests with mock AI adapter
- [ ] Frontend report components have Vitest tests with sample report specs

---

## Sprint 8: Technical Advisor & Polish (Weeks 17-18)

### Goal

Implement the deep technical feasibility advisor, configurable alert system, morning briefing generation, and data privacy safeguards (PII redaction, chunk audit logging, data source indicators).

### Backend Tasks

- **Technical feasibility advisor** -- Implement `app/services/advisor/technical_advisor.py` with three core capabilities:
  - **Backward planning**: Given a project deadline, the AI identifies what must happen by when. Compares required timeline against current task velocity and flags gaps. Uses tasks from `jira_tasks`, milestone data from `projects`, and team capacity from `people`.
  - **Missing task detection**: AI analyzes the project plan against common technical checklists (app store submission, CI/CD setup, database migration, security audit, load testing, documentation). Flags tasks that should exist but are not in Jira.
  - **Architect question generation**: Given a project context, generates "What questions should I ask the architect?" -- technical due diligence questions covering architecture, scalability, security, data migration, third-party dependencies, and deployment.
- **Backward planning engine** -- Create `app/services/advisor/backward_planner.py`. Accepts `project_id` and `deadline`. Loads all tasks and milestones. Sends to AI with prompt: "Given this deadline and these remaining tasks, build a backward timeline. For each task, calculate the latest start date assuming average velocity. Flag any task whose latest start date is in the past." Returns a structured `BackwardPlan` with `{ task_id, latest_start, latest_finish, is_at_risk, risk_reason }` for each task.
- **Configurable alerts engine** -- Implement `app/services/alerts/alert_engine.py`:
  - NL threshold parsing: "Alert me if sprint completion drops below 70%" -- AI extracts `{ metric: "sprint_completion", operator: "lt", threshold: 70 }` and stores as an `Alert` document in MongoDB.
  - Alert evaluation: On each data ingestion completion, run all active alert rules against current metrics. Create `AlertTriggered` documents for any breaches.
  - Alert types: `sprint_metric`, `communication_pattern`, `timeline_risk`, `capacity_utilization`.
  - API endpoints in `app/routers/alert_router.py`: `POST /api/v1/alerts` (create from NL), `GET /api/v1/alerts` (list), `GET /api/v1/alerts/triggered` (active triggers), `PATCH /api/v1/alerts/{id}` (update/dismiss).
- **Morning briefing generator** -- Implement `app/services/briefing/briefing_generator.py`. Triggered after data ingestion or on-demand. Assembles: health score delta, new alerts, project status changes, people activity changes, risk flag changes. Sends to AI for narrative generation. Stores in `briefings` collection. Endpoint: `GET /api/v1/briefings/latest`.
- **PII redaction filter** -- Implement `app/services/privacy/pii_redactor.py`. Scans text for: email addresses (regex), phone numbers (regex), government IDs (SSN, Aadhaar patterns), credit card numbers (Luhn check). Replaces with `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`, etc. Applied as a middleware layer before any text is sent to the AI adapter. Configurable via `PII_REDACTION_ENABLED=true` environment variable.
- **Chunk audit logging** -- Implement `app/services/privacy/chunk_audit.py`. For every AI request, log to `audit_log` collection: `{ request_id, timestamp, chunks_sent: [{ source, chunk_id, preview }], token_count, model, purpose }`. Endpoint: `GET /api/v1/audit/chunks?request_id={id}` for the COO to inspect what was sent.
- **Data source indicator** -- Extend AI response model to include `sources_used: [{ source_type: "slack"|"jira"|"drive", item_count: int, date_range: str }]`. The AI service populates this from the chunks assembled during context building.

### Frontend Tasks

- **Technical advisor panel** (`src/components/advisor/TechnicalAdvisorPanel.tsx`) -- Dedicated section within the project static dashboard. Displays: backward planning timeline (visual bar chart showing task latest-start dates vs. today), missing task cards (each with severity and recommendation), and architect questions (expandable accordion).
- **Alert banner component** (`src/components/alerts/AlertBanner.tsx`) -- Persistent banner at the top of the main dashboard below the nav bar. Shows count of active alerts with severity color coding (red for critical, amber for warning). Expandable to show individual alert details. Dismiss button per alert.
- **Alert management** -- NL alert creation flows through the chat. When the COO says "Alert me if...", the AI creates the alert and confirms in the chat. Active alerts are visible in the alert banner and in a dedicated alerts section on the main dashboard.
- **Briefing panel update** -- Enhance the existing briefing panel on the main dashboard to display the AI-generated morning briefing. Show delta indicators (up/down arrows with values) for key metrics compared to the previous briefing.
- **Data source badges** (`src/components/chat/SourceBadge.tsx`) -- Small badges below each AI response in the chat showing which data sources were consulted: Slack icon with message count, Jira icon with task count, Drive icon with document count. Clicking a badge expands to show the specific items referenced.
- **Chunk audit viewer** (`src/components/privacy/ChunkAuditViewer.tsx`) -- Accessible from a "What data was used?" link on each AI response. Opens a modal showing the chunks that were sent to the AI for that specific request, with source, preview text, and token count.

### Key Deliverables

At the end of Sprint 8, the COO can:
- Ask "What are we missing for the March launch?" and get a structured backward planning analysis with specific gap flags
- Ask "What should I ask the architect about the database migration?" and receive tailored technical due diligence questions
- Say "Alert me if sprint completion drops below 70%" and the alert is configured
- See alert banners fire when thresholds are breached after new data ingestion
- View a morning briefing that summarizes what changed since the last data extract
- Trust that PII (emails, phone numbers, IDs) is redacted before reaching the AI
- Click "What data was used?" on any AI response and see exactly which chunks were sent

### Definition of Done

- [ ] Backward planning returns a structured timeline with at-risk flags for a sample project
- [ ] Missing task detection identifies at least 3 common missing prerequisites for a sample project
- [ ] Architect question generation produces relevant technical questions for a given project context
- [ ] Alert creation from NL stores the alert rule in MongoDB
- [ ] Alert evaluation fires alerts when thresholds are breached
- [ ] Alert banner displays active alerts with correct severity levels
- [ ] Morning briefing generates and displays on the main dashboard
- [ ] PII redaction masks emails, phone numbers, and ID patterns before AI calls
- [ ] Chunk audit log records every AI request with chunk details
- [ ] Data source badges appear on all AI responses
- [ ] All new services have pytest tests
- [ ] PII redaction has dedicated tests with known PII patterns

---

## Sprint 9: Integration, Testing & Hardening (Weeks 19-20)

### Goal

Perform end-to-end integration testing of the full workflow, optimize performance, harden error handling, build the settings and onboarding pages, polish the UI, and prepare a demo-ready system.

### Backend Tasks

- **End-to-end integration tests** -- Create `tests/integration/test_full_workflow.py` that exercises the complete pipeline: upload Slack ZIP + Jira CSV + Drive folder, wait for ingestion to complete, verify dashboard populates, ask NL questions and validate response structure, generate a report, export to PDF, verify PDF contains charts. Uses `pytest-asyncio` with a real MongoDB instance (Docker test container).
- **Performance optimization**:
  - Ingestion pipeline: Add batch processing for Slack messages (process 100 messages per AI call instead of individually). Parallelize Citex indexing calls with `asyncio.gather`.
  - Query response time: Add Redis caching for frequently accessed aggregations (project summaries, people metrics). Cache key includes data hash so cache invalidates on new ingestion. Target: NL query response under 5 seconds.
  - Dashboard load: Pre-compute widget data on ingestion completion and store in Redis. Dashboard API returns cached data, falling back to live query if cache miss.
- **Error handling hardening**:
  - Graceful degradation: If Citex is unavailable, serve cached data and display a warning banner. If AI adapter fails, return a "service temporarily unavailable" message rather than a stack trace.
  - Retry logic: Implement exponential backoff retry in `app/services/ingestion/retry.py` for Citex API calls (max 3 retries, 1s/2s/4s delays). AI adapter calls get 2 retries with 2s/4s delays.
  - File upload validation: Enforce max file size (500MB per file, 2GB total per upload batch). Validate file types before processing. Return clear error messages for unsupported formats.
- **Settings page API** -- Add `app/routers/settings_router.py`:
  - `GET /api/v1/settings` -- current settings (AI model, PII redaction toggle, alert defaults)
  - `PATCH /api/v1/settings` -- update settings
  - AI model selection: Store preferred model in settings. The AI adapter reads this at request time.
  - Data management: `POST /api/v1/settings/data/export` (export all data as JSON), `DELETE /api/v1/settings/data` (clear all data for fresh start)
- **Onboarding data** -- Create `app/fixtures/` directory with sample data: a small Slack export ZIP (3 channels, 50 messages), a Jira CSV (25 tasks across 2 projects), and 3 sample Drive documents (a project plan DOCX, a requirements PDF, a sprint notes MD). These are bundled with the Docker image for the first-run onboarding flow.
- **Demo preparation** -- Create `scripts/demo_setup.py` that loads the sample data through the ingestion pipeline so a fresh `docker compose up` can immediately show a populated dashboard for demos.

### Frontend Tasks

- **Settings page** (`src/pages/SettingsPage.tsx`) -- Simple form-based page (the one exception to the NL-only rule):
  - AI model selector: dropdown of available models (read from backend config)
  - PII redaction toggle
  - Data management: "Export All Data" button (downloads JSON), "Clear All Data" button (with confirmation dialog)
  - About section: version, build date, links to documentation
- **Onboarding flow** (`src/components/onboarding/OnboardingWizard.tsx`) -- First-run wizard triggered when no data exists. Three steps:
  1. Welcome screen with ChiefOps overview
  2. "Try with sample data" button (loads fixtures) or "Upload your own data" button (opens file upload)
  3. Confirmation and redirect to main dashboard
  - The wizard state is tracked via a `has_completed_onboarding` flag in settings
- **Final UI polish**:
  - Responsive design: Ensure all pages work at 1024px, 1280px, 1440px, and 1920px widths. Dashboard widgets reflow from 3 columns to 2 to 1 based on viewport.
  - Loading states: Skeleton loaders for all dashboard widgets, report preview sections, and chat responses. Use Tailwind `animate-pulse` on placeholder shapes.
  - Empty states: Custom illustrations and helpful messages for: no projects ("Upload data to get started"), no widgets ("Ask ChiefOps to add a chart"), no reports ("Generate your first report"), no alerts ("Set up alerts via conversation").
  - Error states: Error boundary components with "Something went wrong" messages and "Retry" buttons. Network error toast notifications.
  - Transitions: Page transitions (fade), widget add/remove animations (slide + fade), chat message appearance (slide up).
- **E2E test suite** -- Create `tests/e2e/` directory with Playwright tests:
  - `onboarding.spec.ts` -- First-run wizard with sample data
  - `file-upload.spec.ts` -- Upload Slack ZIP, Jira CSV, Drive folder
  - `dashboard.spec.ts` -- Verify main dashboard loads with widgets
  - `nl-query.spec.ts` -- Type a question, verify response appears
  - `report-generation.spec.ts` -- Generate report, verify preview, export PDF
  - `widget-management.spec.ts` -- Add, edit, delete widgets via NL
- **Documentation** -- `README.md` at the repo root: getting started (prerequisites, `docker compose up`, first login), architecture overview diagram, development setup for contributors.

### Key Deliverables

At the end of Sprint 9, the COO can:
- Run `docker compose up -d` and have a fully functional ChiefOps within 2 minutes
- Experience a guided onboarding that loads sample data and shows a populated dashboard immediately
- Upload their own data and see the full pipeline: ingestion, analysis, dashboard, reports, PDF export
- Trust that errors are handled gracefully without system crashes
- Adjust settings (AI model, PII redaction) from a settings page
- The system is demo-ready with sample data and a scripted walkthrough for stakeholders

### Definition of Done

- [ ] Full workflow E2E test passes: upload, ingest, dashboard, NL query, report, PDF
- [ ] NL query response time is under 5 seconds for cached queries
- [ ] Dashboard loads in under 3 seconds
- [ ] Report generation completes in under 15 seconds
- [ ] PDF export completes in under 10 seconds
- [ ] Graceful degradation works when Citex is temporarily unavailable
- [ ] Retry logic handles transient failures for Citex and AI adapter calls
- [ ] Settings page allows AI model selection and data management
- [ ] Onboarding wizard loads sample data successfully
- [ ] All pages are responsive at 1024px, 1280px, 1440px, and 1920px
- [ ] Empty states display for all major sections when no data is present
- [ ] Loading skeletons appear for all async content
- [ ] Playwright E2E suite has 6+ test files covering critical paths
- [ ] All tests pass in CI

---

## Sprint Summary Timeline

| Sprint | Name | Weeks | Duration | Primary Deliverables |
|--------|------|-------|----------|---------------------|
| **0** | Foundation | 1-2 | 2 weeks | Repo scaffolding, Docker Compose (all 10 containers), FastAPI skeleton, React shell, MongoDB connection, health checks |
| **1** | Data Ingestion | 3-4 | 2 weeks | Slack ZIP parser, Jira CSV parser, Drive file parser, upload UI, ingestion pipeline, Citex indexing |
| **2** | AI & Memory Core | 5-6 | 2 weeks | AI adapter (CLI + OpenRouter), memory system (facts, summaries, recent turns), NL query pipeline, chat UI |
| **3** | People Intelligence | 7-8 | 2 weeks | People identification from Slack + Jira + Drive, role inference, cross-source entity resolution, people directory UI, COO corrections |
| **4** | Project Analysis | 9-10 | 2 weeks | Project identification, per-project deep dive, completion estimation, risk detection, project dashboard (static) |
| **5** | Dashboard Foundation | 11-12 | 2 weeks | Main dashboard, health score, briefing panel, 5 widget types (bar, line, table, kpi_card, summary_text), NL widget creation |
| **6** | Advanced Dashboard | 13-14 | 2 weeks | 5 more widget types (pie, Gantt, person_grid, timeline, activity_feed), NL widget editing/deletion, project dashboard auto-creation |
| **7** | Report Generation | 15-16 | 2 weeks | 8 report templates, NL-triggered generation, interactive preview, NL editing, PDF export with charts |
| **8** | Technical Advisor | 17-18 | 2 weeks | Backward planning, missing task detection, architect questions, configurable alerts, morning briefings, PII redaction, chunk audit |
| **9** | Hardening & Demo | 19-20 | 2 weeks | E2E integration tests, performance optimization, error handling, settings, onboarding, UI polish, demo preparation |

**Total: 10 sprints across 20 weeks (5 months)**

---

## Testing Strategy

### Backend Testing

**Framework:** pytest, pytest-asyncio, pytest-cov

**Unit tests** (`tests/unit/`) -- Test individual service functions in isolation. Mock all external dependencies (MongoDB, Redis, Citex, AI adapter).

| Test Area | Example Tests | Mock Strategy |
|-----------|--------------|---------------|
| Slack parser | Parse sample ZIP, validate message extraction | Fixture ZIP file |
| Jira parser | Parse sample CSV, validate task mapping | Fixture CSV file |
| Drive parser | Parse DOCX/PDF/XLSX, validate text extraction | Fixture files |
| Memory manager | Fact extraction, summary compaction, turn management | Mock AI adapter returns predefined JSON |
| People intelligence | Entity resolution, role inference, cross-source merge | Mock AI adapter + fixture MongoDB data |
| Widget data engine | Aggregation pipelines produce correct chart data | Fixture MongoDB data |
| Report generator | Spec generation from NL, section CRUD | Mock AI adapter |
| PDF exporter | HTML template rendering, WeasyPrint invocation | Mock report spec |
| PII redactor | Email, phone, ID pattern detection and masking | Known PII strings |
| Alert engine | Threshold parsing, breach detection | Fixture metrics data |

**Integration tests** (`tests/integration/`) -- Test API endpoints with a real MongoDB instance (via Docker test container). Verify request/response contracts, error handling, and data persistence.

| Test Area | Scope |
|-----------|-------|
| Ingestion API | Upload file, verify parsing, check MongoDB documents |
| Query API | Send NL query, verify response structure with mock AI |
| Dashboard API | CRUD widgets, verify persistence |
| Report API | Generate, edit, export lifecycle |
| Alert API | Create, trigger, dismiss alerts |
| Settings API | Read and update configuration |

**Mock AI adapter** (`tests/fixtures/mock_ai_adapter.py`) -- A test-only `AIAdapter` implementation that returns predefined JSON responses for deterministic testing. Maps prompt patterns to fixture responses:

```python
class MockAIAdapter(AIAdapter):
    """Deterministic AI adapter for testing."""

    RESPONSE_MAP = {
        "intent_detection": '{"intent": "query", "project_id": "proj_alpha"}',
        "people_identification": '{"people": [{"name": "Alice", "role": "engineer"}]}',
        "report_generation": '{"report_type": "board_ops_summary", "sections": [...]}',
        "widget_creation": '{"widget_type": "bar_chart", "title": "Tasks by Person"}',
    }

    async def generate(self, system_prompt, user_prompt, **kwargs):
        for key, response in self.RESPONSE_MAP.items():
            if key in system_prompt.lower():
                return AIResponse(content=response, model="mock", adapter="mock")
        return AIResponse(content='{"result": "ok"}', model="mock", adapter="mock")
```

### Frontend Testing

**Framework:** Vitest (unit/component), React Testing Library (component interaction), Playwright (E2E)

**Unit tests** (`frontend/src/__tests__/`) -- Test utility functions, Zustand store logic, and data transformation helpers.

**Component tests** (`frontend/src/components/__tests__/`) -- Render components with mock props and verify:
- Correct DOM structure
- User interaction handling (clicks, form input)
- Zustand store updates
- API call triggers (mock Axios)

| Component | Test Coverage |
|-----------|--------------|
| Chat sidebar | Message rendering, input handling, WebSocket mock |
| Widget components | Each widget type renders with sample chart specs |
| Report preview | Section rendering for all 6 section types |
| Dashboard grid | Widget layout, responsive reflow |
| File upload | Drag-and-drop, progress indicator, error states |
| Alert banner | Alert display, severity colors, dismiss |

**E2E tests** (`frontend/tests/e2e/`) -- Playwright browser tests against the full running stack (Docker Compose). Test critical user journeys:

| Test File | Journey |
|-----------|---------|
| `onboarding.spec.ts` | First run, load sample data, verify dashboard |
| `file-upload.spec.ts` | Upload each file type, verify ingestion completes |
| `dashboard.spec.ts` | Main dashboard loads, project dashboard loads, widgets render |
| `nl-query.spec.ts` | Ask question, verify AI response in chat |
| `report-generation.spec.ts` | Generate report via NL, preview, edit, export PDF |
| `widget-management.spec.ts` | Create widget via NL, edit, delete |

### Coverage Targets

| Layer | Target | Tool |
|-------|--------|------|
| Backend unit tests | 80% line coverage | pytest-cov |
| Backend integration tests | All API endpoints covered | pytest + httpx |
| Frontend unit/component tests | 70% line coverage | Vitest + c8 |
| E2E tests | 6 critical paths | Playwright |

### CI Pipeline

```
lint (ruff + eslint)
    |
type-check (mypy + tsc --noEmit)
    |
unit tests (pytest + vitest, parallel)
    |
integration tests (pytest with Docker MongoDB)
    |
E2E tests (Playwright against Docker Compose stack)
    |
coverage report (fail if below thresholds)
```

### Test Data & Fixtures

All test fixtures live in `tests/fixtures/`:

| Fixture | Contents |
|---------|----------|
| `sample_slack_export.zip` | 3 channels, 50 messages, 8 users, threads and reactions |
| `sample_jira_export.csv` | 25 tasks across 2 projects, mixed statuses, assignees, story points |
| `sample_drive_docs/` | 3 files: project plan (DOCX), requirements (PDF), sprint notes (MD) |
| `mock_ai_responses/` | JSON files with predefined AI responses for each operation type |
| `sample_report_specs/` | Complete report spec JSON files for each of the 8 report types |
| `sample_widget_specs/` | Widget spec JSON files for each of the 10 widget types |

---

## Risk Management

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **AI response quality/accuracy** -- AI may produce incorrect project assessments, miss people, or generate inaccurate metrics | Medium | High | Use structured JSON output schemas to constrain responses. Validate AI output against known data. Allow COO corrections that override AI conclusions. Mock adapter for testing ensures predictable behavior. |
| 2 | **Citex integration complexity** -- Citex is an external system with its own API, data model, and failure modes | Medium | High | Implement fallback to direct MongoDB queries when Citex is unavailable. Cache Citex results in Redis. Comprehensive retry logic with exponential backoff. Integration tests against a running Citex instance. |
| 3 | **PDF generation with embedded charts** -- WeasyPrint + pyecharts SVG rendering may produce layout issues, missing fonts, or broken charts | Medium | Medium | Use server-side pyecharts to render SVGs independently and embed as `<img>` tags in the HTML template. Test with all 10 chart types. Pin WeasyPrint and pyecharts versions. Maintain a library of test PDFs for regression. |
| 4 | **Large file upload handling** -- Slack exports and Drive folders can be hundreds of megabytes. Browser uploads may timeout or consume excessive memory | Medium | Medium | Stream uploads using chunked transfer encoding. Process files in a background task (not in the request handler). Enforce per-file (500MB) and per-batch (2GB) limits. Show progress indicators during upload and processing. |
| 5 | **CLI subprocess reliability** -- Dev-mode AI via subprocess (`claude`, `codex`, `gemini` CLI tools) may hang, crash, or produce unexpected output | Medium | Low | Set subprocess timeout (60 seconds). Parse stdout/stderr separately. Validate JSON output before processing. Fall back to a mock response if the CLI fails. This only affects development -- production uses the OpenRouter HTTP adapter. |
| 6 | **Memory system performance at scale** -- As conversation history grows, context assembly may become slow or exceed token limits | Low | Medium | Progressive summarization compacts old turns. Hard facts are stored separately and loaded selectively. Token budget system caps context at 7-17K tokens. Redis cache for frequently accessed memory contexts. |
| 7 | **ECharts Gantt rendering complexity** -- Gantt charts use the custom series `renderItem` API which is complex and has limited documentation | Medium | Medium | Build the Gantt component early (Sprint 6) to identify issues. Use a reference implementation from ECharts examples. Create a comprehensive test fixture with edge cases (zero-duration milestones, overlapping tasks, long timelines). Fall back to a simplified bar chart timeline if custom rendering proves unreliable. |
| 8 | **Cross-source entity resolution accuracy** -- Matching people across Slack, Jira, and Drive data where names, emails, and usernames differ | High | Medium | Use the AI for fuzzy matching (not just exact match). Present low-confidence matches to the COO for confirmation. Store COO corrections as hard facts that override future resolution. Build a name alias dictionary that grows with corrections. |
| 9 | **Docker Compose startup reliability** -- 10 containers with health checks and dependency chains may fail to start cleanly | Low | Medium | Use `depends_on` with `condition: service_healthy` for strict ordering. Set generous health check intervals and retries. Provide a `scripts/health_check.sh` that verifies all services are running. Document common startup failures in the README. |
| 10 | **Token cost in production** -- OpenRouter API calls with large context windows can become expensive at scale | Low | High | Token tracking per request (logged in audit). Budget alerts when monthly spend approaches limits. Optimize context assembly to send only relevant chunks. Cache AI responses for repeated queries (same data + same question = same answer). |

---

## Deployment Guide

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | Latest stable |
| Docker Compose | v2.20+ | Latest stable |
| Disk space | 10 GB | 20 GB (for data volumes) |
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| AI CLI tools (dev only) | One of: `claude`, `codex`, or `gemini` CLI installed | Claude CLI |
| OpenRouter API key (prod only) | Required for production AI | -- |

### Environment Variables

Create a `.env` file in the project root (a `.env.example` is provided):

```bash
# .env.example -- ChiefOps Step Zero Configuration

# ── AI Configuration ──────────────────────────────────
AI_ADAPTER=cli                          # cli | openrouter
AI_MODEL=claude-sonnet-4-20250514     # Model ID for CLI or OpenRouter
OPENROUTER_API_KEY=                     # Required only when AI_ADAPTER=openrouter

# ── Database ──────────────────────────────────────────
MONGO_URI=mongodb://chiefops-mongo:27017
REDIS_URL=redis://chiefops-redis:6379

# ── Citex RAG System ─────────────────────────────────
CITEX_API_URL=http://citex-api:8000

# ── Privacy ───────────────────────────────────────────
PII_REDACTION_ENABLED=true              # Redact emails, phones, IDs before AI calls

# ── Application ───────────────────────────────────────
LOG_LEVEL=INFO                          # DEBUG | INFO | WARNING | ERROR
UPLOAD_MAX_FILE_SIZE_MB=500             # Max single file size
UPLOAD_MAX_BATCH_SIZE_MB=2048           # Max total upload batch size

# ── Frontend ──────────────────────────────────────────
VITE_API_URL=http://localhost:23001     # Backend URL for the browser
```

### Startup

```bash
# Clone the repository
git clone https://github.com/yensi-solutions/chiefops.git
cd chiefops

# Copy and configure environment
cp .env.example .env
# Edit .env to set AI_ADAPTER and OPENROUTER_API_KEY if using production AI

# Start all services (10 containers)
docker compose up -d

# Verify all services are healthy
docker compose ps

# View logs (optional)
docker compose logs -f chiefops-backend
```

The system is accessible at `http://localhost:23000` once all containers are healthy. First startup takes 2-5 minutes as Docker builds the frontend and backend images and pulls the database images.

### Port Reference

| Port | Service | Purpose |
|------|---------|---------|
| 23000 | Frontend | React SPA -- open this in a browser |
| 23001 | Backend | FastAPI -- API docs at `/docs` |
| 23002 | MongoDB | Application database |
| 23003 | Redis | Cache and pub/sub |
| 23004 | Citex API | RAG gateway |
| 23005 | Citex Qdrant | Vector database |
| 23006 | Citex MongoDB | Document store |
| 23007 | Citex MinIO | Object storage |
| 23008 | Citex Neo4j | Graph database |
| 23009 | Citex Redis | Citex cache |

### Data Volume Management

All persistent data is stored in Docker named volumes:

```bash
# List volumes
docker volume ls | grep chiefops

# Volumes:
#   chiefops_mongo-data       -- Application database
#   chiefops_redis-data       -- Cache data
#   chiefops_qdrant-data      -- Vector embeddings
#   chiefops_citex-mongo-data -- Citex document store
#   chiefops_minio-data       -- Uploaded files
#   chiefops_neo4j-data       -- Graph data
#   chiefops_citex-redis-data -- Citex cache
#   chiefops_uploads          -- Uploaded files (pre-processing)
#   chiefops_exports          -- Generated PDFs
```

### Backup and Restore

```bash
# Backup MongoDB data
docker compose exec chiefops-mongo mongodump \
  --archive=/data/db/backup.archive \
  --gzip

# Copy backup to host
docker compose cp chiefops-mongo:/data/db/backup.archive ./backups/

# Restore from backup
docker compose cp ./backups/backup.archive chiefops-mongo:/data/db/backup.archive
docker compose exec chiefops-mongo mongorestore \
  --archive=/data/db/backup.archive \
  --gzip \
  --drop
```

### Upgrading ChiefOps

```bash
# Pull latest code
git pull origin main

# Rebuild and restart (preserves data volumes)
docker compose down
docker compose build --no-cache
docker compose up -d

# Verify health
docker compose ps
```

Data volumes persist across `docker compose down` / `docker compose up` cycles. Only `docker compose down -v` removes volumes (destructive).

### Stopping and Cleanup

```bash
# Stop all services (preserves data)
docker compose down

# Stop and remove all data (DESTRUCTIVE)
docker compose down -v
```

---

## Definition of Done -- Step Zero Complete

The following seven acceptance criteria (from [PRD Section 10](./01-PRD.md#10-success-criteria-for-step-zero)) define "done" for Step Zero. Each criterion is expanded into verifiable tests.

### Criterion 1: Data Ingestion to Dashboard in Under 5 Minutes

> COO uploads Slack ZIP + Jira CSV + Drive folder, and within 5 minutes sees a populated dashboard with project summaries, people directory, and health score.

**Acceptance Tests:**
- [ ] Upload a Slack ZIP (50 messages, 3 channels) and verify ingestion completes with a summary notification
- [ ] Upload a Jira CSV (25 tasks, 2 projects) and verify tasks appear in MongoDB `jira_tasks` collection
- [ ] Upload a Drive folder (3 documents) and verify documents are indexed in Citex
- [ ] After all three uploads, the main dashboard displays: health score (non-zero), project overview cards (2 projects), and team activity summary
- [ ] The people directory contains at least 5 identified people with roles
- [ ] Total time from first upload to populated dashboard is under 5 minutes

### Criterion 2: Accurate Cross-Source Query

> COO asks "How's Project Alpha doing?" and gets an accurate, comprehensive answer drawing from all three data sources.

**Acceptance Tests:**
- [ ] NL query returns a response that references Slack messages, Jira tasks, and Drive documents related to Project Alpha
- [ ] Response includes: project completion percentage, active people, recent activity, and identified risks
- [ ] Response is generated in under 5 seconds
- [ ] Data source badges on the response show all three sources were consulted

### Criterion 3: COO Corrections Cascade

> COO says "Raj is the lead architect, not a junior dev" and the system updates all summaries, reports, and analysis accordingly.

**Acceptance Tests:**
- [ ] COO correction is stored as a hard fact in the `memory_facts` collection
- [ ] Subsequent queries about Raj reflect the corrected role
- [ ] The people directory shows Raj as "Lead Architect"
- [ ] Any report generated after the correction shows Raj with the correct role
- [ ] The correction persists across browser refreshes and server restarts

### Criterion 4: Professional PDF Report in Under 2 Minutes

> COO says "Generate a board report for January" and gets a professional PDF in under 2 minutes.

**Acceptance Tests:**
- [ ] NL command triggers report generation with the correct type (board_ops_summary) and time scope (January)
- [ ] Report preview renders with all expected sections: executive summary, key metrics, project status, team allocation, risks, recommendations
- [ ] Preview includes at least 2 live charts
- [ ] PDF export produces a valid PDF file with: YENSI branding, page numbers, embedded charts (as SVG), table of contents
- [ ] Total time from NL command to PDF download is under 2 minutes

### Criterion 5: NL Widget Management

> COO says "Add a person vs. tasks chart to my Alpha dashboard" and the widget appears and persists.

**Acceptance Tests:**
- [ ] NL command creates a bar chart widget showing people on the x-axis and task counts on the y-axis, scoped to Project Alpha
- [ ] The widget appears on the Project Alpha custom dashboard within 5 seconds
- [ ] The widget persists after a browser refresh
- [ ] The widget updates with new data after a subsequent ingestion
- [ ] The COO can modify the widget ("Make it a pie chart") and delete it ("Remove that chart") via NL

### Criterion 6: Proactive Technical Flags

> The system proactively flags: "You want to launch on March 20 but I don't see a task for App Store developer account setup."

**Acceptance Tests:**
- [ ] Given a project with a deadline and tasks, the technical advisor identifies at least one missing prerequisite
- [ ] The flag appears in the project static dashboard's technical readiness section
- [ ] The flag includes: the missing task description, why it matters, and a suggested timeline
- [ ] The COO can ask "What are we missing for the March launch?" and get a structured response

### Criterion 7: Visual Quality

> The system looks visually stunning -- an instant seller for YENSI Solutions.

**Acceptance Tests:**
- [ ] All pages use consistent typography, spacing, and color palette from the Tailwind design system
- [ ] Dashboard widgets have smooth loading transitions (skeleton loaders, fade-in)
- [ ] Charts are interactive: hover tooltips, zoom, and responsive resizing
- [ ] The main dashboard, project dashboard, and report preview render without layout breaks at 1280px and 1920px widths
- [ ] Empty states have custom messaging and visual treatment (not blank screens)
- [ ] PDF reports have professional formatting that would be suitable for a board presentation

---

## Related Documents

- **Project Setup & Sprints 0-5:** [Implementation Plan -- Part A](./11-IMPLEMENTATION-PLAN.md)
- **System Design:** [Architecture](./02-ARCHITECTURE.md), [Data Models](./03-DATA-MODELS.md)
- **Core Systems:** [Memory System](./04-MEMORY-SYSTEM.md), [Citex Integration](./05-CITEX-INTEGRATION.md), [AI Layer](./06-AI-LAYER.md)
- **Features:** [File Ingestion](./08-FILE-INGESTION.md), [People Intelligence](./09-PEOPLE-INTELLIGENCE.md), [Report Generation](./07-REPORT-GENERATION.md), [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md), [Widget Types](./10B-WIDGET-TYPES-AND-COMPONENTS.md)
- **Design:** [UI/UX Design](./12-UI-UX-DESIGN.md)
- **Requirements:** [PRD](./01-PRD.md)
