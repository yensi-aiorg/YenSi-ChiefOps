# Product Requirements Document: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | **PRD** | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Product Overview

### 1.1 What Is ChiefOps?

**ChiefOps** is an AI-powered Chief Operations Officer agent — the COO's right hand. It is an **intelligent project advisor** that works from raw file dumps (Slack exports, Jira CSV exports, Google Drive file copies) and uses AI to piece together the real state of affairs — including things that no rigid rule-based tool can capture.

ChiefOps is part of the **YENSI AI Platform** ecosystem, built by YENSI Solutions (Hyderabad, India). It is one of 22+ products spanning enterprise, consumer, education, and robotics, all powered by a unified AI core under the philosophy **"One Platform. Infinite Possibilities."**

### 1.2 Core Value Proposition

A startup COO drowns in fragmented data across Slack, Jira, Google Drive, and other tools. They spend half their day just gathering context, cross-referencing information, and compiling reports. ChiefOps eliminates this by:

1. **Ingesting raw data dumps** — no API access, no admin credentials, no integration setup
2. **Using AI to understand context** — identifying people, roles, assignments, and project status from unstructured data
3. **Providing intelligent analysis** — gap detection, backward planning from deadlines, technical feasibility checks
4. **Delivering everything through natural language** — no forms, no buttons, just conversation
5. **Generating beautiful visualizations and reports** — on demand, exportable to PDF

### 1.3 Relationship to the Full ChiefOps Vision

The full ChiefOps vision (as defined in the repository README) describes an autonomous agent with a 5-step loop: **Observe → Analyze → Recommend → Act → Learn**.

Step Zero builds the first three stages:

| Vision Stage | Step Zero Implementation | Future Phases |
|-------------|------------------------|---------------|
| **Observe** | File dump ingestion (Slack ZIP, Jira CSV, Drive folder) | Phase 2: Live API integrations (webhooks + polling) |
| **Analyze** | People intelligence, project deep-dive, gap detection, technical feasibility | Phase 1: Add GitHub + Notion, improve AI accuracy |
| **Recommend** | NL briefings, risk flags, missing task detection, architect questions | Phase 1: Configurable alerts, refined recommendations |
| **Act** | Advisory only — no autonomous actions | Phase 4: Semi-autonomous → full autonomous with approval workflows |
| **Learn** | COO corrections feed back into the system, memory compaction | Phase 4: Continuous learning from operational patterns |

Every architectural decision in Step Zero is designed to **grow into the full vision without rewriting**. File dump parsers become live connectors. Single tenant becomes multi-tenant. Advisory becomes autonomous. The MongoDB schema, Citex integration, AI adapter pattern, dashboard widget system, and people intelligence model remain the same across all phases.

---

## 2. Target User

### 2.1 Primary Persona

**Sarah, COO at a Series A/B startup with 80 people.**

- Engineering (30), Sales (15), Customer Success (10), Ops (8), Marketing (8), Product (5), Finance (4)
- Uses Slack all day, reviews Jira weekly, glances at GitHub for release cadence, lives in Google Workspace, tries to keep Notion as source of truth
- Opens her laptop every morning not knowing what fires are burning
- **Does NOT have admin access** to most tools — she can download her own Slack conversations, export Jira as CSV, and copy files from Google Drive, but she cannot set up API tokens, OAuth apps, or webhook integrations
- Needs to report to the CEO and board regularly with operational summaries
- Wants a tool that understands her organization, not just displays data

### 2.2 Key Characteristics

| Characteristic | Detail |
|---------------|--------|
| Company size | 50-200 people |
| Funding stage | Series A/B |
| Technical depth | Non-technical — needs the system to handle technical analysis |
| Tool access | Regular user access to Slack, Jira, Google Drive (not admin) |
| Primary need | Visibility, intelligence, and reporting without manual effort |
| Interaction preference | Natural language — types or speaks (speech-to-text) |

### 2.3 What the COO Wants to Know

- "How's the engineering sprint going?"
- "Who is falling short on their deliverables?"
- "Are we on track for the March 15 deadline?"
- "What technical tasks are we missing for the iOS launch?"
- "What should I ask the architect about the database migration?"
- "Give me a complete summary of Project Alpha"
- "Generate a board-ready ops report for January"
- "Show me a person vs. tasks breakdown for this month"

---

## 3. Step Zero Scope

### 3.1 Data Sources

Step Zero supports **three data sources**, all provided as file dumps by the COO:

| Source | How the COO Provides It | Format | What We Extract |
|--------|------------------------|--------|-----------------|
| **Slack** | Downloads/zips conversations from Slack client, OR uses Admin Export (if available) | ZIP of JSON files, or folder of exported conversations | Messages, channels, participants, threads, reactions, timestamps |
| **Jira** | CSV export from Jira's built-in export UI | CSV file(s) | Tasks (key, summary, status, assignee, priority, sprint, story points, dates, comments) |
| **Google Drive** | Copies a folder from Drive to a local folder | Folder of files (PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, etc.) | Full document content, parsed and indexed for semantic search |

**Not in Step Zero:** GitHub, Notion, Salesforce, SAP, or any live API integrations. These are planned for Phase 1-2.

Both Slack extraction methods are supported:
- **Admin Export ZIP** — the standard Slack workspace export format (JSON per channel per day)
- **API Extract Script** — a Python script that uses the Slack API to pull conversations (requires a Slack app token)

The COO can use whichever method is available to them.

### 3.2 Data Refresh

**On-demand.** The COO triggers a new data extract whenever they want fresh data. There is no scheduled sync, no polling, no webhooks. The COO:

1. Downloads/exports fresh data from their tools
2. Drops the files into ChiefOps
3. System processes the new data, updates analysis

### 3.3 User Model

- **Single user** — the COO is the only user
- **Single tenant** — one deployment = one company
- **No authentication in Step Zero** — skip Keycloak entirely. Auth is added in Phase 3 when multi-user support is introduced.

### 3.4 Deployment Model

- **Local Docker Compose** — everything runs on the COO's machine or a single server
- `docker compose up` and the system is running
- All data stays local (in the Docker volumes)

---

## 4. Feature Requirements

### 4.1 Feature 1: Smart File Ingestion

**Purpose:** Accept manual file drops from the COO and parse them into structured data.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| FI-01 | Drag-and-drop interface for uploading files | Must |
| FI-02 | Support Slack Admin Export ZIP format (JSON per channel per day) | Must |
| FI-03 | Support Slack API extract JSON format | Must |
| FI-04 | Support Jira CSV export format | Must |
| FI-05 | Support Google Drive folder of files (PDF, DOCX, PPTX, XLSX, HTML, MD, TXT) | Must |
| FI-06 | Auto-detect file type and route to appropriate parser | Must |
| FI-07 | Progress indicator showing ingestion status (parsing, chunking, embedding, indexing) | Must |
| FI-08 | Summary of what was ingested: "Processed 342 Slack messages, 89 Jira tasks, 14 documents" | Must |
| FI-09 | Incremental ingestion — detect already-ingested files and skip duplicates (via content hash) | Should |
| FI-10 | Error reporting for unsupported or corrupted files | Must |

**Data flow:** Files are uploaded via the frontend, stored temporarily, then processed through the ingestion pipeline (parse → normalize → store in MongoDB → index in Citex). See [File Ingestion](./08-FILE-INGESTION.md) for details.

### 4.2 Feature 2: People Intelligence Engine

**Purpose:** Use AI to identify all people in the organization, their roles, their activity levels, and their task ownership — even when data is incomplete or informal.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| PI-01 | Scan all ingested data (Slack + Jira + Drive) to build a people directory | Must |
| PI-02 | Identify roles from context (developer, architect, PM, designer, etc.) | Must |
| PI-03 | Cross-reference Slack mentions with Jira task descriptions to map people to tasks | Must |
| PI-04 | Handle informal task assignments in Slack: "Hey Raj, can you pick up PROJ-142?" | Must |
| PI-05 | Handle one task assigned to multiple people | Must |
| PI-06 | Track engagement levels: active contributors vs. passive observers | Must |
| PI-07 | Flag inactive team members: "Anil hasn't posted in #project-alpha for 5 days" | Must |
| PI-08 | COO can correct any person's role, assignment, or details via natural language | Must |
| PI-09 | Corrections cascade: changing a role re-adjusts all summaries, reports, and analysis | Must |
| PI-10 | People directory is viewable and queryable via NL | Must |

**Key challenge:** Jira tasks may not have assignees. People are assigned work informally in Slack. One Jira task can be assigned to multiple people. A rigid rule-based system does not work here. The AI must understand context, infer assignments, and build the organizational picture from unstructured data.

See [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) for the detailed design.

### 4.3 Feature 3: Project Intelligence & Deep Dive

**Purpose:** Automatically identify distinct projects and provide per-project deep dives with timeline, people, completion status, risks, and gaps.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| PJ-01 | Identify distinct projects from Jira data (projects, epics) + Slack channels | Must |
| PJ-02 | Per-project summary: status, timeline, people, completion %, risks | Must |
| PJ-03 | Milestone and deadline visualization (timeline/Gantt-style view) | Must |
| PJ-04 | Identify who is involved in each project and what they are doing | Must |
| PJ-05 | Show who is falling short or has gone quiet | Must |
| PJ-06 | Calculate completion percentage from task data + AI assessment | Must |
| PJ-07 | COO can click on a project to get the full deep dive | Must |
| PJ-08 | COO can ask follow-up questions about any project in the chat | Must |
| PJ-09 | Intelligent estimation: task count vs. team capacity vs. timeline | Should |
| PJ-10 | Compare projects side-by-side | Should |

**Project deep dive includes:**
- Project overview (name, deadline, overall status, completion %)
- Timeline visualization with milestones and risk markers
- People involved (identified from Slack + Jira) with roles and activity levels
- Concerns and flags (inactive members, unassigned tasks, missing prerequisites)
- "What I'd ask the architect" — AI-generated technical due diligence questions
- Upcoming deadlines and backward planning analysis

### 4.4 Feature 4: Technical Feasibility Advisor

**Purpose:** Proactively identify gaps in project planning, missing tasks, and technical risks. Think forward from the current state and backward from deadlines.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| TF-01 | Backward planning from deadlines: identify what must happen by when | Must |
| TF-02 | Detect missing prerequisite tasks (e.g., "No task for iOS developer account setup") | Must |
| TF-03 | Generate technical checklist questions for the architect | Must |
| TF-04 | Estimate feasibility: remaining tasks vs. team capacity vs. time remaining | Must |
| TF-05 | Flag tasks with no owner that are on the critical path | Must |
| TF-06 | Consider lead times for external dependencies (app store review, vendor approvals, etc.) | Must |
| TF-07 | Surface these findings proactively in project deep dives and briefings | Must |
| TF-08 | Allow COO to ask: "What are we missing for the March launch?" | Must |

**Examples of what the system should flag:**
- "You want the application to go into the App Store, but I don't see a task for an iOS developer account confirmed. Apple typically takes 4-7 days for approval."
- "The deadline is 2 weeks away. Based on remaining 14 tasks and current velocity (3 tasks/week per developer), you'd need 5 developers fully allocated. Currently 3 people are actively contributing."
- "For a Salesforce integration project, have you considered: API rate limits? OAuth refresh token handling? Data migration rollback plan?"

### 4.5 Feature 5: Conversational AI Interface

**Purpose:** The primary interaction model. Everything happens through natural language — the COO types (or speaks via speech-to-text, always delivered as text) and the system responds.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| NL-01 | Search bar at the top of the dashboard for quick queries | Must |
| NL-02 | Expandable chat sidebar for deeper conversations | Must |
| NL-03 | Context-aware: when viewing a project, questions are scoped to that project | Must |
| NL-04 | Supports follow-up questions within a conversation | Must |
| NL-05 | Can generate charts and visualizations inline in the conversation | Must |
| NL-06 | Can trigger report generation from the conversation | Must |
| NL-07 | Can modify dashboard widgets from the conversation | Must |
| NL-08 | Can correct facts, roles, assignments via conversation (see PI-08) | Must |
| NL-09 | Conversation history maintained per project stream | Must |
| NL-10 | Cross-project queries on the main dashboard | Must |
| NL-11 | No forms, buttons, or dropdowns for interactions (except top-level project settings) | Must |
| NL-12 | All text-based input (speech-to-text happens externally, delivers text) | Must |

**Interaction from any page:** The COO interacts from different pages (main dashboard, project view, custom dashboard), but all conversations route into the correct project stream. See [Memory System](./04-MEMORY-SYSTEM.md).

### 4.6 Feature 6: Beautiful Visualizations

**Purpose:** The dashboard and all visual outputs must be visually stunning — this is a sales tool as much as a utility. ChiefOps should be an **instant seller** for YENSI Solutions.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| VZ-01 | Gantt charts for project timelines and milestones | Must |
| VZ-02 | Bar charts (standard and stacked) for comparisons | Must |
| VZ-03 | Line charts for trends over time | Must |
| VZ-04 | Pie charts for distribution breakdowns | Must |
| VZ-05 | KPI metric cards with trend indicators | Must |
| VZ-06 | Project health/status cards | Must |
| VZ-07 | Team member activity visualization | Must |
| VZ-08 | Heat maps for activity density | Should |
| VZ-09 | All charts interactive in the UI (hover, zoom, drill-down) | Must |
| VZ-10 | Charts rendered as static images for PDF export | Must |
| VZ-11 | On-demand chart generation via NL: "Show me a person vs. tasks chart" | Must |
| VZ-12 | Clean, modern design with professional typography and color schemes | Must |

**Charting library:** Apache ECharts (via echarts-for-react) — handles Gantt natively, supports all chart types, excellent interactivity, theme-able.

### 4.7 Feature 7: Dynamic Dashboard Widgets

**Purpose:** Allow the COO to customize their dashboard by adding/removing/modifying widgets through natural language.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| DW-01 | COO can say "Add a person vs. tasks chart to my dashboard" and it appears | Must |
| DW-02 | COO can say "Remove that chart" or "Change it to a pie chart" | Must |
| DW-03 | Widgets persist per project across sessions | Must |
| DW-04 | Widgets update when new data is ingested | Must |
| DW-05 | Widget types: bar, line, pie, Gantt, table, KPI card, summary text, person grid, timeline, activity feed | Must |
| DW-06 | No drag-and-drop, no resize handles — AI manages widget placement | Must |
| DW-07 | Widget specifications stored as JSON in MongoDB | Must |
| DW-08 | Each widget has a data query specification that can be re-executed on fresh data | Must |

**Dashboard structure — three levels:**

| Level | Name | Scope | Content | Editable? |
|-------|------|-------|---------|-----------|
| 1 | **Main Dashboard** | Global (all projects) | Health score, alerts, briefing, activity feed, team overview | System-generated, not customizable in v1 |
| 2 | **Project Dashboard (Static)** | Per project | Timeline/Gantt, people, completion %, risks, milestones, architect questions | Auto-generated from analysis. Same layout every project. Regenerates on data update. |
| 3 | **Project Dashboard (Custom)** | Per project | COO-created widgets via NL | Fully NL-editable |

See [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) for the detailed design.

### 4.8 Feature 8: AI Briefings

**Purpose:** Auto-generated operational briefings that summarize the state of the organization.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| BR-01 | Briefing generated automatically after each data extract | Must |
| BR-02 | Briefing displayed on the main dashboard | Must |
| BR-03 | Briefing covers: highlights, lowlights, risks, items needing attention | Must |
| BR-04 | Per-project mini-briefings on project dashboards | Must |
| BR-05 | COO can ask "What happened since last extract?" for a delta briefing | Should |
| BR-06 | Briefing delivery: dashboard only in Step Zero | Must |
| BR-07 | Email and Slack briefing delivery deferred to Phase 3 | N/A |

### 4.9 Feature 9: Operational Health Score

**Purpose:** A single composite metric (0-100) that tells the COO how the organization is doing at a glance.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| HS-01 | Composite score displayed prominently on the main dashboard | Must |
| HS-02 | Sub-scores visible with trend indicators | Must |
| HS-03 | AI explains why the score changed: "Score dropped 8 pts because..." | Must |
| HS-04 | Configurable weights for sub-scores (via NL or settings) | Should |

**Default sub-score composition:**

| Sub-Score | Source | Weight | What It Measures |
|-----------|--------|--------|-----------------|
| Sprint Health | Jira | 30% | Completion rate, blocked tickets ratio, velocity trend |
| Communication Health | Slack | 25% | Response patterns, cross-team collaboration, unanswered threads |
| Documentation Health | Google Drive | 15% | Document freshness, knowledge base coverage, sharing activity |
| Throughput | Jira | 20% | Completed vs. created ratio, cycle time trend |
| Alert Count | All sources | 10% | Number of active threshold breaches |

### 4.10 Feature 10: Configurable Alerts

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| AL-01 | COO defines alert thresholds via NL: "Alert me if sprint completion drops below 70%" | Must |
| AL-02 | Alerts displayed in a banner on the dashboard | Must |
| AL-03 | Alerts re-evaluated on each data extract | Must |
| AL-04 | Alert types: sprint metrics, communication patterns, timeline risks, capacity | Must |

### 4.11 Feature 11: Report Generation

**Purpose:** The COO generates professional reports through natural language, previews them in the UI, and exports to PDF.

**Requirements:**

| ID | Requirement | Priority |
|----|-------------|----------|
| RG-01 | Reports triggered via NL: "Generate a board-ready ops report for January" | Must |
| RG-02 | AI determines report type, scope, and data needed from the request | Must |
| RG-03 | 7+ pre-built report templates (Board, Project, Team, Risk, Sprint, Resource, Technical, Custom) | Must |
| RG-04 | Report displayed as rich preview in the UI (formatted text, live charts, tables) | Must |
| RG-05 | COO edits reports via NL: "Add a section on hiring", "Shorten the summary" | Must |
| RG-06 | Export to PDF with professional layout, branding, embedded charts | Must |
| RG-07 | Reports stored with history — COO can revisit, compare, re-export | Must |
| RG-08 | COO can clone a previous report and update with new data | Should |
| RG-09 | Report includes charts rendered as static images in PDF | Must |
| RG-10 | Page numbers, headers, footers, and branding in PDF output | Must |

See [Report Generation](./07-REPORT-GENERATION.md) for the complete design including report spec structure, templates, and PDF pipeline.

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target |
|--------|--------|
| Data ingestion (100 Slack messages) | < 30 seconds |
| Data ingestion (200-page PDF) | < 2 minutes |
| NL query response time | < 5 seconds |
| Dashboard load time | < 3 seconds |
| Report generation | < 15 seconds |
| PDF export | < 10 seconds |

### 5.2 Data Privacy & Security

| Requirement | Detail |
|-------------|--------|
| Data locality | All data stays on the COO's machine (Docker volumes). Nothing synced to any cloud except LLM API calls. |
| LLM data handling | Only relevant chunks (~7-17K tokens) sent per request, not full dumps. Claude API and Open Router both offer no-training guarantees. |
| PII redaction | Filter layer scans for and masks email addresses, phone numbers, IDs before sending to LLM |
| Chunk audit log | Log which chunks were sent in each request, visible to COO |
| Data scope indicator | UI shows what data sources were used for each AI response |
| Opt-out tags | COO can tag channels/files as "never send to AI" during ingestion |

### 5.3 Reliability

| Requirement | Detail |
|-------------|--------|
| Graceful degradation | If Citex is unavailable, system shows cached data and alerts the user |
| Ingestion recovery | Failed ingestion jobs can be retried without re-uploading files |
| Data integrity | Content hashing prevents duplicate ingestion |

---

## 6. Technology Stack

As mandated by `technical.md`:

### 6.1 Backend

| Category | Technology | Notes |
|----------|------------|-------|
| Language | Python 3.11+ | |
| Framework | FastAPI | Latest, async throughout |
| Database | MongoDB | via Motor async driver |
| Validation | Pydantic v2 | |
| Testing | pytest, pytest-asyncio, pytest-cov | |
| API Documentation | OpenAPI/Swagger | Auto-generated |
| PDF Generation | WeasyPrint | HTML/CSS → PDF |
| Template Engine | Jinja2 | For report HTML templates |

### 6.2 Frontend

| Category | Technology | Notes |
|----------|------------|-------|
| Framework | React 19 | Latest stable |
| Build Tool | Vite | Latest |
| State Management | Zustand | |
| HTTP Client | Axios | with interceptors |
| Styling | Tailwind CSS | |
| Charting | Apache ECharts (echarts-for-react) | Gantt, bar, line, pie, heatmap |
| Type Safety | TypeScript | strict mode |
| Testing | Vitest, React Testing Library, Playwright | E2E |

### 6.3 AI Integration

| Environment | Technology | Notes |
|-------------|------------|-------|
| Development/Testing | Claude CLI, Codex CLI, Gemini CLI | Invoked as Python subprocesses |
| Production | Open Router | Multi-model access |
| RAG | Citex | External plug-and-play RAG system |
| **Adapter Pattern** | **Mandatory** | Abstract interface, concrete implementations per provider, config-driven selection |

### 6.4 Infrastructure

| Category | Technology | Notes |
|----------|------------|-------|
| Containerization | Docker & Docker Compose | |
| Development | Hot Module Reloading | via volume mounts |
| Ports | Sequential starting at 23000 | Never use default ports |

### 6.5 Port Allocation

| Service | Port |
|---------|------|
| Frontend | 23000 |
| Backend (FastAPI) | 23001 |
| MongoDB | 23002 |
| Redis | 23003 |
| Citex API | 23004 |
| Citex Qdrant | 23005 |
| Citex MongoDB | 23006 |
| Citex MinIO | 23007 |
| Citex Neo4j | 23008 |
| Citex Redis | 23009 |

---

## 7. Target Metrics

From the original ChiefOps vision, adjusted for Step Zero:

| Metric | Target | How Measured |
|--------|--------|-------------|
| Time to first insight | < 5 minutes from file upload | Stopwatch from upload to first meaningful dashboard |
| COO daily time saved | 2+ hours | Self-reported vs. manual process |
| Report generation time | < 2 minutes (including review and export) | Vs. hours manually |
| Query accuracy | 85%+ relevant responses | Judged by COO satisfaction |
| Adoption barrier | Zero — no API keys, no admin access, no setup beyond Docker | Binary: can the COO start using it in under 10 minutes? |

---

## 8. Out of Scope (Step Zero)

| Feature | When |
|---------|------|
| Live API integrations (Slack, Jira, Google Drive webhooks/polling) | Phase 2 |
| GitHub and Notion data sources | Phase 1 |
| Multi-user access (team leads, viewers) | Phase 3 |
| Keycloak authentication / RBAC | Phase 3 |
| Autonomous actions (execute workflows, reassign tasks) | Phase 4 |
| Cloud deployment (K8s, cloud VMs) | Phase 3 |
| Email/Slack briefing delivery | Phase 3 |
| Voice input (speech-to-text integration) | Future |
| Workflow automation engine | Phase 4 |
| SOC 2 / GDPR compliance | Phase 5 |
| On-premise enterprise deployment | Phase 5 |
| SAP, Oracle, ServiceNow, Salesforce integrations | Phase 3+ |

---

## 9. Phasing Roadmap

| Phase | Name | Key Deliverables |
|-------|------|-----------------|
| **Step Zero** | Extract & Analyze | File ingestion, people intelligence, project deep-dive, technical advisor, NL interface, dashboard + widgets, report generation, memory system. Local Docker Compose. |
| **Phase 1** | Polish & Expand Data | Add GitHub + Notion extracts. Configurable health score. Alert threshold config UI. Improved NL query accuracy. |
| **Phase 2** | Live Integrations | Replace extract scripts with live connectors (webhooks + polling). Real-time activity feed. Automated scheduled briefings. |
| **Phase 3** | Multi-user & Cloud | Keycloak auth. Team lead views with filtered data. Cloud deployment. Email/Slack briefing delivery. |
| **Phase 4** | Semi-Autonomous Actions | Agent can suggest and execute low-risk actions with approval. Workflow automation engine. Continuous learning. |
| **Phase 5** | Enterprise Readiness | SOC 2 and GDPR compliance. Audit logging and traceability. On-premise and hybrid deployment. Enterprise tool connectors. |

---

## 10. Success Criteria for Step Zero

1. COO uploads Slack ZIP + Jira CSV + Drive folder, and within 5 minutes sees a populated dashboard with project summaries, people directory, and health score
2. COO asks "How's Project Alpha doing?" and gets an accurate, comprehensive answer drawing from all three data sources
3. COO says "Raj is the lead architect, not a junior dev" and the system updates all summaries, reports, and analysis accordingly
4. COO says "Generate a board report for January" and gets a professional PDF in under 2 minutes
5. COO says "Add a person vs. tasks chart to my Alpha dashboard" and the widget appears and persists
6. The system proactively flags: "You want to launch on March 20 but I don't see a task for App Store developer account setup"
7. The system looks visually stunning — an instant seller for YENSI Solutions

---

## Related Documents

- **System Design:** [Architecture](./02-ARCHITECTURE.md), [Data Models](./03-DATA-MODELS.md)
- **Core Systems:** [Memory System](./04-MEMORY-SYSTEM.md), [Citex Integration](./05-CITEX-INTEGRATION.md), [AI Layer](./06-AI-LAYER.md)
- **Features:** [File Ingestion](./08-FILE-INGESTION.md), [People Intelligence](./09-PEOPLE-INTELLIGENCE.md), [Report Generation](./07-REPORT-GENERATION.md), [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md)
- **Execution:** [Implementation Plan](./11-IMPLEMENTATION-PLAN.md), [UI/UX Design](./12-UI-UX-DESIGN.md)
