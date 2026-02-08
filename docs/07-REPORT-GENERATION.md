# Report Generation: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | **Report Generation** | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Overview

Reports are the COO's primary deliverable to the board, CEO, and leadership team. ChiefOps makes report generation as simple as saying "Generate a board ops report for January."

The entire report lifecycle is conversational:

1. **Triggered by NL** — the COO asks for a report in plain English
2. **Generated as a structured JSON spec** — the AI produces a `report_spec` that defines every section, chart, metric, and narrative
3. **Previewed as rich interactive content** — the frontend renders the spec into a scrollable, paginated report preview with live charts, tables, and cards
4. **Editable via conversation** — "Add a section on hiring," "Remove the Gantt chart," "Make the summary shorter" — each edit modifies the spec and the preview re-renders instantly
5. **Exportable to professional PDF** — one click converts the report to a print-ready PDF with branding, charts rendered as SVG, proper page breaks, and table of contents

There are **no forms, no formatting toolbars, no drag-and-drop builders**. The COO talks to ChiefOps, reviews the preview, adjusts through conversation, and exports when satisfied.

```
COO: "Generate a board ops summary for January"
    │
    ▼
┌─────────────────────────────────────────────────┐
│              REPORT GENERATION PIPELINE          │
│                                                  │
│  Intent Detection → Data Assembly → AI Gen →     │
│  Preview Render → NL Editing → PDF Export        │
└─────────────────────────────────────────────────┘
    │
    ▼
Professional PDF with branding, charts, and metrics
```

---

## 2. Report Types

ChiefOps supports eight report types out of the box. The AI selects the appropriate type based on the COO's request, or the COO can explicitly ask for one.

| Type | Audience | Default Sections |
|------|----------|-----------------|
| **Board Ops Summary** | Board / Investors | Exec Summary → Key Metrics Grid → Project Status Cards → Team Allocation Chart → Risk List → Recommendations |
| **Project Status** | CEO / Stakeholders | Project Overview → Timeline (Gantt) → Team & Roles → Task Breakdown Table → Blockers → Technical Readiness Checklist → Next Steps |
| **Team Performance** | COO / HR | Team Overview → Per-Person Metrics Table → Task Completion Chart → Activity Heatmap → Highlights & Concerns |
| **Risk Assessment** | Leadership | Risk Summary → Risk Matrix Chart → Per-Risk Detail Cards → Mitigation Status Table → Action Items |
| **Sprint Report** | Product / Engineering | Sprint Goals vs Actuals → Velocity Chart → Completed Items Table → Carry-Over Items → Blocker Analysis → Next Sprint Plan |
| **Resource Utilization** | COO / Finance | Capacity Overview Metrics → Allocation by Project Chart → Per-Person Utilization Table → Over/Under Utilized Flags → Recommendations |
| **Technical Due Diligence** | CTO / Architect | Readiness Score → Checklist Status → Missing Tasks → Dependency Map → Feasibility Concerns → Questions for Architect |
| **Custom** | Anyone | AI determines structure from COO's request — no predefined sections |

### Report Type Detection

The AI determines the report type from the COO's natural language. Examples:

| COO Says | Detected Type | Reasoning |
|----------|--------------|-----------|
| "Generate a board report for January" | Board Ops Summary | "board" keyword, monthly scope |
| "How's Project Alpha doing?" | Project Status | Single project focus |
| "Show me team performance for Q4" | Team Performance | "team performance" phrase |
| "What are our biggest risks right now?" | Risk Assessment | "risks" keyword |
| "Sprint 12 retro report" | Sprint Report | "sprint" keyword |
| "Who's overloaded? Who's underutilized?" | Resource Utilization | Capacity/allocation focus |
| "Is the iOS app technically ready for launch?" | Technical Due Diligence | Technical readiness focus |
| "Give me a summary of ops, hiring, and revenue" | Custom | Multiple topics, no standard type fits |

---

## 3. Report Generation Pipeline

### Step 1: Intent & Scope Detection

When the COO requests a report, the AI first classifies the request:

```
┌────────────────────────────────────────────────────────────┐
│                   INTENT & SCOPE DETECTION                 │
│                                                            │
│  Input: "Generate a board ops summary for January          │
│          focusing on Project Alpha and Beta"               │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Extracted Parameters:                               │  │
│  │                                                      │  │
│  │  report_type:  "board_ops_summary"                   │  │
│  │  time_scope:   { start: "2026-01-01",                │  │
│  │                  end: "2026-01-31" }                  │  │
│  │  audience:     "board_investors"                      │  │
│  │  projects:     ["project_alpha", "project_beta"]     │  │
│  │  people:       [] (all)                              │  │
│  │  tone:         "formal"                              │  │
│  │  detail_level: "executive"                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Intent extraction prompt (sent to AI):**

```
You are analyzing a report request from a COO. Extract the following:

1. report_type: One of [board_ops_summary, project_status, team_performance,
   risk_assessment, sprint_report, resource_utilization, technical_due_diligence,
   custom]
2. time_scope: { start, end } — infer from "January", "Q4", "last week", etc.
3. audience: Who will read this? Affects tone and detail level.
4. projects: Specific projects mentioned, or empty for all.
5. people: Specific people mentioned, or empty for all.
6. tone: formal (board/investors), professional (CEO/leadership),
   casual (internal team)
7. detail_level: executive (high-level), standard (balanced), detailed (deep-dive)
8. special_requests: Any specific sections, metrics, or focus areas mentioned.

COO's request: "{user_message}"
```

**Response format (structured output):**

```json
{
  "report_type": "board_ops_summary",
  "time_scope": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-01-31T23:59:59Z"
  },
  "audience": "board_investors",
  "projects": ["project_alpha", "project_beta"],
  "people": [],
  "tone": "formal",
  "detail_level": "executive",
  "special_requests": []
}
```

### Step 2: Data Assembly

Once the scope is known, the backend assembles all data the AI needs to generate the report.

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA ASSEMBLY                             │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   MongoDB     │    │     Citex         │    │   Memory      │  │
│  │              │    │   (Semantic)      │    │   System      │  │
│  │  - projects  │    │                  │    │              │  │
│  │  - people    │    │  - Relevant docs  │    │  - Compacted  │  │
│  │  - tasks     │    │  - Slack context  │    │    summaries  │  │
│  │  - metrics   │    │  - Meeting notes  │    │  - Key facts  │  │
│  │  - sprints   │    │  - Decisions      │    │  - COO prefs  │  │
│  └──────┬───────┘    └────────┬─────────┘    └──────┬────────┘  │
│         │                     │                      │           │
│         ▼                     ▼                      ▼           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              ASSEMBLED DATA CONTEXT                      │   │
│  │                                                          │   │
│  │  {                                                       │   │
│  │    "projects": [...],                                    │   │
│  │    "people": [...],                                      │   │
│  │    "tasks_by_status": {...},                              │   │
│  │    "metrics_snapshot": {...},                             │   │
│  │    "relevant_documents": [...],                           │   │
│  │    "memory_context": "...",                               │   │
│  │    "time_scope": {...}                                    │   │
│  │  }                                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**Data sources by report type:**

| Report Type | MongoDB Queries | Citex Searches | Memory |
|-------------|----------------|----------------|--------|
| Board Ops Summary | All active projects, all people, aggregated metrics, top risks | "board-relevant decisions," "strategic updates" | Compacted project summaries, COO's previous board notes |
| Project Status | Single project + its tasks + assigned people + sprints | "Project Alpha updates," "Alpha technical decisions" | Project-specific memory, COO corrections |
| Team Performance | All people + their tasks + completion rates + activity logs | "team performance," "individual contributions" | Per-person summaries, COO feedback |
| Risk Assessment | All risks + mitigation tasks + risk history | "risks," "blockers," "concerns" | Risk-related memory, escalation history |
| Sprint Report | Sprint tasks + velocity data + blockers | "sprint goals," "sprint blockers" | Sprint retrospective notes |
| Resource Utilization | People + task assignments + capacity data | "workload," "capacity" | COO observations on workload |
| Technical Due Diligence | Technical tasks + checklists + dependencies | "technical readiness," "architecture decisions" | Technical facts, architect Q&A |

**Data assembly implementation:**

```python
# services/report_data_assembler.py

from typing import Any
from datetime import datetime

class ReportDataAssembler:
    """Assembles all data needed for report generation."""

    def __init__(self, db, citex_client, memory_service):
        self.db = db
        self.citex = citex_client
        self.memory = memory_service

    async def assemble(
        self,
        report_type: str,
        time_scope: dict,
        projects: list[str],
        people: list[str],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Pull all data needed for the given report type."""

        context = {
            "time_scope": time_scope,
            "assembled_at": datetime.utcnow().isoformat(),
        }

        # --- MongoDB: structured data ---
        context["projects"] = await self._get_projects(
            tenant_id, projects, time_scope
        )
        context["people"] = await self._get_people(
            tenant_id, people
        )
        context["tasks_by_status"] = await self._get_tasks_grouped(
            tenant_id, projects, time_scope
        )
        context["metrics_snapshot"] = await self._get_metrics(
            tenant_id, projects, time_scope
        )

        if report_type in ("risk_assessment", "board_ops_summary"):
            context["risks"] = await self._get_risks(
                tenant_id, projects
            )

        if report_type in ("sprint_report",):
            context["sprint_data"] = await self._get_sprint_data(
                tenant_id, projects, time_scope
            )

        if report_type in ("resource_utilization", "team_performance"):
            context["utilization"] = await self._get_utilization(
                tenant_id, people, time_scope
            )

        # --- Citex: semantic search for relevant unstructured content ---
        search_queries = self._build_search_queries(report_type, projects)
        context["relevant_documents"] = []
        for query in search_queries:
            results = await self.citex.search(
                query=query,
                tenant_id=tenant_id,
                top_k=10,
                time_filter=time_scope,
            )
            context["relevant_documents"].extend(results)

        # Deduplicate by document ID
        seen = set()
        unique_docs = []
        for doc in context["relevant_documents"]:
            if doc["id"] not in seen:
                seen.add(doc["id"])
                unique_docs.append(doc)
        context["relevant_documents"] = unique_docs

        # --- Memory: compacted summaries and facts ---
        context["memory_context"] = await self.memory.get_report_context(
            tenant_id=tenant_id,
            report_type=report_type,
            projects=projects,
            time_scope=time_scope,
        )

        return context

    def _build_search_queries(
        self, report_type: str, projects: list[str]
    ) -> list[str]:
        """Build Citex search queries based on report type."""
        base_queries = {
            "board_ops_summary": [
                "strategic updates and decisions",
                "key metrics and milestones",
                "risks and blockers",
            ],
            "project_status": [
                "project updates and progress",
                "technical decisions",
                "blockers and dependencies",
            ],
            "team_performance": [
                "team contributions and activity",
                "individual performance",
                "collaboration patterns",
            ],
            "risk_assessment": [
                "risks and concerns",
                "mitigation plans",
                "escalations",
            ],
            "sprint_report": [
                "sprint goals and commitments",
                "completed work",
                "sprint blockers",
            ],
            "resource_utilization": [
                "workload and capacity",
                "resource allocation",
                "team availability",
            ],
            "technical_due_diligence": [
                "technical readiness",
                "architecture decisions",
                "technical debt and concerns",
            ],
        }
        queries = base_queries.get(report_type, ["general updates"])

        # Add project-specific queries
        for project in projects:
            queries.append(f"{project} updates and status")

        return queries

    async def _get_projects(self, tenant_id, projects, time_scope):
        query = {"tenant_id": tenant_id, "status": {"$ne": "archived"}}
        if projects:
            query["slug"] = {"$in": projects}
        return await self.db.projects.find(query).to_list(None)

    async def _get_people(self, tenant_id, people):
        query = {"tenant_id": tenant_id, "status": "active"}
        if people:
            query["slug"] = {"$in": people}
        return await self.db.people.find(query).to_list(None)

    async def _get_tasks_grouped(self, tenant_id, projects, time_scope):
        pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "updated_at": {
                    "$gte": time_scope["start"],
                    "$lte": time_scope["end"],
                },
                **({"project_id": {"$in": projects}} if projects else {}),
            }},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "tasks": {"$push": "$$ROOT"},
            }},
        ]
        results = await self.db.tasks.aggregate(pipeline).to_list(None)
        return {r["_id"]: r for r in results}

    async def _get_metrics(self, tenant_id, projects, time_scope):
        pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "recorded_at": {
                    "$gte": time_scope["start"],
                    "$lte": time_scope["end"],
                },
            }},
            {"$group": {
                "_id": "$metric_name",
                "latest_value": {"$last": "$value"},
                "previous_value": {"$first": "$value"},
                "count": {"$sum": 1},
            }},
        ]
        results = await self.db.metrics.aggregate(pipeline).to_list(None)
        return {r["_id"]: r for r in results}

    async def _get_risks(self, tenant_id, projects):
        query = {"tenant_id": tenant_id, "status": {"$ne": "resolved"}}
        if projects:
            query["project_id"] = {"$in": projects}
        return await self.db.risks.find(
            query, sort=[("severity", -1)]
        ).to_list(None)

    async def _get_sprint_data(self, tenant_id, projects, time_scope):
        query = {
            "tenant_id": tenant_id,
            "start_date": {"$lte": time_scope["end"]},
            "end_date": {"$gte": time_scope["start"]},
        }
        if projects:
            query["project_id"] = {"$in": projects}
        return await self.db.sprints.find(query).to_list(None)

    async def _get_utilization(self, tenant_id, people, time_scope):
        pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "assigned_at": {
                    "$gte": time_scope["start"],
                    "$lte": time_scope["end"],
                },
                **({"assignee_id": {"$in": people}} if people else {}),
            }},
            {"$group": {
                "_id": "$assignee_id",
                "total_tasks": {"$sum": 1},
                "completed_tasks": {
                    "$sum": {"$cond": [
                        {"$eq": ["$status", "done"]}, 1, 0
                    ]}
                },
                "total_points": {"$sum": "$story_points"},
            }},
        ]
        return await self.db.tasks.aggregate(pipeline).to_list(None)
```

### Step 3: AI Report Generation

The AI receives the assembled data context and generates a complete `report_spec` JSON.

```
┌──────────────────────────────────────────────────────────────────┐
│                     AI REPORT GENERATION                         │
│                                                                  │
│  Input:                                                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  - Report type: board_ops_summary                         │  │
│  │  - Scope parameters (time, projects, audience, tone)      │  │
│  │  - Assembled data context (projects, people, tasks, etc.) │  │
│  │  - Section template for this report type                   │  │
│  │  - Memory context (COO preferences, past reports)         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  AI generates:                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Complete report_spec JSON                                │  │
│  │  - Title, subtitle, branding                              │  │
│  │  - Ordered list of sections                               │  │
│  │  - Narrative text (executive summary, recommendations)    │  │
│  │  - Data for metrics grids, tables, cards                  │  │
│  │  - ECharts configs for all charts                         │  │
│  │  - Risk items, checklist items, action items              │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Report generation prompt:**

```
You are generating a professional operations report for a COO.

REPORT TYPE: {report_type}
AUDIENCE: {audience}
TONE: {tone}
TIME SCOPE: {time_scope.start} to {time_scope.end}
DETAIL LEVEL: {detail_level}

DATA CONTEXT:
{assembled_data_json}

MEMORY CONTEXT:
{memory_context}

Generate a complete report_spec JSON following this schema exactly.
The report must include all standard sections for a {report_type} report.
Use the actual data provided — do not fabricate numbers.
For charts, generate complete ECharts option configs.
For narrative sections, write clear, concise prose appropriate for {audience}.
For metrics, include trend indicators (up/down/flat) based on the data.

Output the report_spec as valid JSON.
```

**AI generation service:**

```python
# services/report_generator.py

import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

class ReportGenerator:
    """Generates report_spec JSON from assembled data using AI."""

    def __init__(self, ai_adapter, data_assembler):
        self.ai = ai_adapter
        self.assembler = data_assembler

    async def generate(
        self,
        intent: dict,
        tenant_id: str,
        branding: dict,
    ) -> dict[str, Any]:
        """Full pipeline: assemble data → generate spec → validate."""

        # Step 2: Assemble data
        data_context = await self.assembler.assemble(
            report_type=intent["report_type"],
            time_scope=intent["time_scope"],
            projects=intent["projects"],
            people=intent["people"],
            tenant_id=tenant_id,
        )

        # Step 3: Generate report spec via AI
        section_template = self._get_section_template(intent["report_type"])

        prompt = self._build_generation_prompt(
            intent=intent,
            data_context=data_context,
            section_template=section_template,
        )

        response = await self.ai.generate_structured(
            prompt=prompt,
            schema="report_spec",
            max_tokens=8000,
        )

        report_spec = json.loads(response)

        # Attach metadata
        report_spec["report_id"] = str(uuid4())
        report_spec["generated_at"] = datetime.now(timezone.utc).isoformat()
        report_spec["branding"] = branding
        report_spec["meta"] = {
            "report_type": intent["report_type"],
            "time_scope": intent["time_scope"],
            "audience": intent["audience"],
            "tone": intent["tone"],
            "detail_level": intent["detail_level"],
            "projects": intent["projects"],
            "people": intent["people"],
        }

        # Validate
        self._validate_spec(report_spec)

        return report_spec

    def _get_section_template(self, report_type: str) -> list[dict]:
        """Return the default section ordering for a report type."""
        templates = {
            "board_ops_summary": [
                {"type": "executive_summary", "title": "Executive Summary"},
                {"type": "metrics_grid", "title": "Key Metrics"},
                {"type": "project_cards", "title": "Project Status"},
                {"type": "chart", "title": "Team Allocation"},
                {"type": "risk_list", "title": "Risks & Concerns"},
                {"type": "recommendations", "title": "Recommendations"},
            ],
            "project_status": [
                {"type": "narrative", "title": "Project Overview"},
                {"type": "gantt", "title": "Timeline"},
                {"type": "person_grid", "title": "Team & Roles"},
                {"type": "table", "title": "Task Breakdown"},
                {"type": "risk_list", "title": "Blockers"},
                {"type": "checklist", "title": "Technical Readiness"},
                {"type": "recommendations", "title": "Next Steps"},
            ],
            "team_performance": [
                {"type": "narrative", "title": "Team Overview"},
                {"type": "table", "title": "Per-Person Metrics"},
                {"type": "chart", "title": "Task Completion"},
                {"type": "chart", "title": "Activity Heatmap"},
                {"type": "recommendations", "title": "Highlights & Concerns"},
            ],
            "risk_assessment": [
                {"type": "executive_summary", "title": "Risk Summary"},
                {"type": "chart", "title": "Risk Matrix"},
                {"type": "risk_list", "title": "Risk Details"},
                {"type": "table", "title": "Mitigation Status"},
                {"type": "recommendations", "title": "Actions"},
            ],
            "sprint_report": [
                {"type": "metrics_grid", "title": "Sprint Goals vs Actuals"},
                {"type": "chart", "title": "Velocity"},
                {"type": "table", "title": "Completed Items"},
                {"type": "table", "title": "Carry-Over"},
                {"type": "narrative", "title": "Blocker Analysis"},
                {"type": "recommendations", "title": "Next Sprint"},
            ],
            "resource_utilization": [
                {"type": "metrics_grid", "title": "Capacity Overview"},
                {"type": "chart", "title": "Allocation by Project"},
                {"type": "table", "title": "Per-Person Utilization"},
                {"type": "risk_list", "title": "Over/Under Utilized"},
                {"type": "recommendations", "title": "Recommendations"},
            ],
            "technical_due_diligence": [
                {"type": "metrics_grid", "title": "Readiness Score"},
                {"type": "checklist", "title": "Checklist Status"},
                {"type": "table", "title": "Missing Tasks"},
                {"type": "chart", "title": "Dependency Map"},
                {"type": "narrative", "title": "Feasibility Concerns"},
                {"type": "recommendations", "title": "Questions for Architect"},
            ],
        }
        return templates.get(report_type, [])

    def _build_generation_prompt(
        self, intent: dict, data_context: dict, section_template: list
    ) -> str:
        return f"""You are generating a professional operations report.

REPORT TYPE: {intent['report_type']}
AUDIENCE: {intent['audience']}
TONE: {intent['tone']}
TIME SCOPE: {intent['time_scope']['start']} to {intent['time_scope']['end']}
DETAIL LEVEL: {intent['detail_level']}

SECTION TEMPLATE (generate these sections in this order):
{json.dumps(section_template, indent=2)}

DATA CONTEXT:
{json.dumps(data_context, indent=2, default=str)}

MEMORY CONTEXT:
{data_context.get('memory_context', 'No prior context available.')}

Generate a complete report_spec JSON. Each section must include:
- "type": matching the template
- "title": section title
- "content": narrative text (for text sections)
- "data": structured data (for data-driven sections)
- "chart_spec": complete ECharts option config (for chart sections)
- "items": array of items (for list sections)

Use REAL data from the context. Do not fabricate numbers.
For charts, generate complete ECharts option objects that can be passed directly
to echarts.setOption().
"""

    def _validate_spec(self, spec: dict) -> None:
        """Validate the report spec has required fields."""
        required = ["report_id", "title", "sections"]
        for field in required:
            if field not in spec:
                raise ValueError(f"Report spec missing required field: {field}")

        for i, section in enumerate(spec["sections"]):
            if "type" not in section:
                raise ValueError(f"Section {i} missing 'type' field")
            if "title" not in section:
                raise ValueError(f"Section {i} missing 'title' field")

            valid_types = {
                "executive_summary", "metrics_grid", "chart",
                "project_cards", "table", "risk_list",
                "recommendations", "narrative", "person_grid",
                "gantt", "checklist",
            }
            if section["type"] not in valid_types:
                raise ValueError(
                    f"Section {i} has invalid type: {section['type']}"
                )
```

### Step 4: Preview Render

The frontend receives the `report_spec` and renders it into a rich, interactive preview.

```
┌──────────────────────────────────────────────────────────────────┐
│                       PREVIEW RENDER                             │
│                                                                  │
│  report_spec (JSON)                                              │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  React Report Renderer                                   │   │
│  │                                                          │   │
│  │  for section in report_spec.sections:                    │   │
│  │    switch (section.type):                                │   │
│  │      "executive_summary" → <NarrativeBlock />            │   │
│  │      "metrics_grid"      → <MetricsGrid />               │   │
│  │      "chart"             → <EChartsWrapper />             │   │
│  │      "project_cards"     → <ProjectCardGrid />            │   │
│  │      "table"             → <DataTable />                  │   │
│  │      "risk_list"         → <RiskList />                   │   │
│  │      "recommendations"   → <RecommendationsList />        │   │
│  │      "narrative"         → <NarrativeBlock />             │   │
│  │      "person_grid"       → <PersonCardGrid />             │   │
│  │      "gantt"             → <GanttChart />                 │   │
│  │      "checklist"         → <ChecklistBlock />             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Output: scrollable, paginated, interactive report preview       │
└──────────────────────────────────────────────────────────────────┘
```

**React component structure:**

```typescript
// components/report/ReportRenderer.tsx

interface ReportRendererProps {
  spec: ReportSpec;
  onSectionClick?: (sectionIndex: number) => void;
}

function ReportRenderer({ spec, onSectionClick }: ReportRendererProps) {
  return (
    <div className="report-preview">
      {/* Report Header */}
      <ReportHeader
        title={spec.title}
        subtitle={spec.subtitle}
        branding={spec.branding}
        generatedAt={spec.generated_at}
      />

      {/* Sections */}
      {spec.sections.map((section, index) => (
        <ReportSection
          key={`${section.type}-${index}`}
          section={section}
          onClick={() => onSectionClick?.(index)}
        />
      ))}

      {/* Report Footer */}
      <ReportFooter branding={spec.branding} />
    </div>
  );
}

function ReportSection({ section, onClick }: { section: Section; onClick: () => void }) {
  const Component = SECTION_COMPONENTS[section.type];
  if (!Component) return null;

  return (
    <div className="report-section" onClick={onClick}>
      <h2 className="section-title">{section.title}</h2>
      <Component section={section} />
    </div>
  );
}

const SECTION_COMPONENTS: Record<string, React.ComponentType<{ section: Section }>> = {
  executive_summary: NarrativeBlock,
  metrics_grid: MetricsGrid,
  chart: EChartsWrapper,
  project_cards: ProjectCardGrid,
  table: DataTable,
  risk_list: RiskList,
  recommendations: RecommendationsList,
  narrative: NarrativeBlock,
  person_grid: PersonCardGrid,
  gantt: GanttChart,
  checklist: ChecklistBlock,
};
```

### Step 5: COO Reviews & Adjusts via NL

The COO reviews the preview and makes adjustments through conversation. Each instruction modifies the `report_spec`.

```
┌──────────────────────────────────────────────────────────────────┐
│                     NL REPORT EDITING                            │
│                                                                  │
│  COO: "Add a section on the hiring pipeline after team alloc"   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AI Edit Processor                                       │   │
│  │                                                          │   │
│  │  Input:                                                  │   │
│  │    - Current report_spec                                 │   │
│  │    - COO's edit instruction                              │   │
│  │    - Data context (for new sections that need data)      │   │
│  │                                                          │   │
│  │  Operations:                                             │   │
│  │    - INSERT section at position                          │   │
│  │    - REMOVE section(s) by type or title                  │   │
│  │    - REWRITE section content                             │   │
│  │    - UPDATE data point                                   │   │
│  │    - REORDER sections                                    │   │
│  │    - UPDATE chart_spec                                   │   │
│  │    - UPDATE metadata (title, subtitle)                   │   │
│  │                                                          │   │
│  │  Output: modified report_spec                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  Frontend re-renders with updated spec (instant)                 │
└──────────────────────────────────────────────────────────────────┘
```

### Step 6: Export to PDF

When the COO is satisfied, they click Export or say "Export to PDF."

```
┌──────────────────────────────────────────────────────────────────┐
│                       PDF EXPORT PIPELINE                        │
│                                                                  │
│  report_spec (JSON)                                              │
│       │                                                          │
│       ├──► Jinja2 Template Engine                                │
│       │      │                                                   │
│       │      ├── base_report.html (header, footer, page nums)    │
│       │      ├── executive_summary.html                          │
│       │      ├── metrics_grid.html                               │
│       │      ├── chart_section.html (SVG placeholder)            │
│       │      ├── project_cards.html                              │
│       │      ├── data_table.html                                 │
│       │      ├── risk_list.html                                  │
│       │      ├── recommendations.html                            │
│       │      ├── person_grid.html                                │
│       │      ├── gantt_section.html                              │
│       │      └── checklist.html                                  │
│       │      │                                                   │
│       │      ▼                                                   │
│       │    Complete HTML document                                 │
│       │                                                          │
│       ├──► Chart Renderer (pyecharts)                            │
│       │      │                                                   │
│       │      ├── chart_spec → pyecharts config                   │
│       │      ├── render to SVG                                   │
│       │      └── SVGs embedded in HTML                           │
│       │                                                          │
│       ▼                                                          │
│  HTML + embedded SVG charts + print CSS                          │
│       │                                                          │
│       ▼                                                          │
│  WeasyPrint                                                      │
│       │                                                          │
│       ├── Page breaks between sections                           │
│       ├── Running header/footer                                  │
│       ├── Table of contents                                      │
│       ├── Professional typography                                │
│       │                                                          │
│       ▼                                                          │
│  Final PDF file                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Report Spec Structure (JSON)

The `report_spec` is the central data structure for the report system. It is a complete, self-contained description of a report that can be rendered in the browser or exported to PDF.

### Schema

```json
{
  "report_id": "string — UUID, unique identifier for this report",
  "title": "string — main report title",
  "subtitle": "string — optional subtitle (e.g., time period, scope)",
  "generated_at": "datetime — ISO 8601 timestamp",
  "branding": {
    "company": "string — company name displayed in header/footer",
    "logo_url": "string — URL to company logo image",
    "color_scheme": "string — preset name or hex codes for primary/secondary colors"
  },
  "meta": {
    "report_type": "string — one of the 8 report types",
    "time_scope": {
      "start": "datetime — period start",
      "end": "datetime — period end"
    },
    "audience": "string — intended audience",
    "tone": "string — formal | professional | casual",
    "detail_level": "string — executive | standard | detailed",
    "projects": ["string — project slugs included"],
    "people": ["string — people slugs included"]
  },
  "sections": [
    {
      "type": "string — one of: executive_summary | metrics_grid | chart | project_cards | table | risk_list | recommendations | narrative | person_grid | gantt | checklist",
      "title": "string — section heading",
      "content": "string — narrative/text content (for text-based sections)",
      "data": {
        "description": "object — structured data for data-driven sections (metrics, cards, etc.)"
      },
      "chart_spec": {
        "description": "object — complete ECharts option config (for chart sections)"
      },
      "items": [
        {
          "description": "array — list items (for risk_list, recommendations, checklist, etc.)"
        }
      ]
    }
  ]
}
```

### Full Example: Board Ops Summary Report

The following is a complete, realistic `report_spec` for a Board Ops Summary generated from actual project data.

```json
{
  "report_id": "rpt_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Board Operations Summary",
  "subtitle": "January 2026 — YENSI Solutions",
  "generated_at": "2026-02-01T09:30:00Z",
  "branding": {
    "company": "YENSI Solutions",
    "logo_url": "/assets/branding/yensi-logo.svg",
    "color_scheme": "yensi_default"
  },
  "meta": {
    "report_type": "board_ops_summary",
    "time_scope": {
      "start": "2026-01-01T00:00:00Z",
      "end": "2026-01-31T23:59:59Z"
    },
    "audience": "board_investors",
    "tone": "formal",
    "detail_level": "executive",
    "projects": [],
    "people": []
  },
  "sections": [
    {
      "type": "executive_summary",
      "title": "Executive Summary",
      "content": "January was a strong operational month for YENSI Solutions. Engineering velocity increased 18% over December, driven by the Project Alpha team hitting its stride after the holiday ramp-up. Project Beta successfully completed its Phase 1 milestone two days ahead of schedule, and the iOS build pipeline is now fully operational.\n\nTeam capacity remains healthy at 82% average utilization across 78 active team members. Two key hires joined (Senior Backend Engineer, Product Designer), bringing the headcount to 80.\n\nThe primary risk area is the March 15 deadline for the Project Gamma investor demo. The backend API is at 71% completion with 6 weeks remaining, and the AI integration layer has not yet started. A mitigation plan is outlined in the Risks section below.\n\nRecommendations focus on accelerating Gamma's AI integration, rebalancing two over-utilized engineers, and scheduling a mid-February architecture review with the CTO."
    },
    {
      "type": "metrics_grid",
      "title": "Key Metrics",
      "data": {
        "metrics": [
          {
            "label": "Active Projects",
            "value": 5,
            "previous_value": 5,
            "trend": "flat",
            "unit": "",
            "color": "#3B82F6"
          },
          {
            "label": "Tasks Completed",
            "value": 247,
            "previous_value": 209,
            "trend": "up",
            "trend_pct": 18.2,
            "unit": "",
            "color": "#10B981"
          },
          {
            "label": "Team Utilization",
            "value": 82,
            "previous_value": 78,
            "trend": "up",
            "trend_pct": 5.1,
            "unit": "%",
            "color": "#6366F1"
          },
          {
            "label": "Open Blockers",
            "value": 3,
            "previous_value": 7,
            "trend": "down",
            "trend_pct": -57.1,
            "unit": "",
            "color": "#EF4444"
          },
          {
            "label": "Sprint Velocity",
            "value": 64,
            "previous_value": 54,
            "trend": "up",
            "trend_pct": 18.5,
            "unit": "pts/sprint",
            "color": "#F59E0B"
          },
          {
            "label": "Headcount",
            "value": 80,
            "previous_value": 78,
            "trend": "up",
            "trend_pct": 2.6,
            "unit": "people",
            "color": "#8B5CF6"
          }
        ]
      }
    },
    {
      "type": "project_cards",
      "title": "Project Status",
      "data": {
        "projects": [
          {
            "name": "Project Alpha",
            "slug": "project-alpha",
            "status": "on_track",
            "status_label": "On Track",
            "completion_pct": 62,
            "deadline": "2026-04-30",
            "lead": "Priya Sharma",
            "team_size": 12,
            "tasks_completed": 87,
            "tasks_total": 140,
            "highlights": [
              "Core API endpoints 100% complete",
              "Frontend dashboard at 65% completion",
              "Performance benchmarks exceeded targets"
            ],
            "concerns": [
              "Third-party payment integration delayed by vendor"
            ]
          },
          {
            "name": "Project Beta",
            "slug": "project-beta",
            "status": "on_track",
            "status_label": "On Track",
            "completion_pct": 45,
            "deadline": "2026-06-15",
            "lead": "Arjun Mehta",
            "team_size": 8,
            "tasks_completed": 54,
            "tasks_total": 120,
            "highlights": [
              "Phase 1 milestone completed 2 days early",
              "iOS build pipeline fully operational",
              "User testing feedback incorporated"
            ],
            "concerns": []
          },
          {
            "name": "Project Gamma",
            "slug": "project-gamma",
            "status": "at_risk",
            "status_label": "At Risk",
            "completion_pct": 38,
            "deadline": "2026-03-15",
            "lead": "Vikram Patel",
            "team_size": 10,
            "tasks_completed": 42,
            "tasks_total": 110,
            "highlights": [
              "Backend API at 71% completion",
              "Database schema finalized"
            ],
            "concerns": [
              "AI integration layer not yet started (est. 3 weeks work)",
              "March 15 investor demo deadline is tight",
              "Need additional ML engineer capacity"
            ]
          },
          {
            "name": "Platform Infrastructure",
            "slug": "platform-infra",
            "status": "on_track",
            "status_label": "On Track",
            "completion_pct": 78,
            "deadline": "2026-03-31",
            "lead": "Deepa Krishnan",
            "team_size": 5,
            "tasks_completed": 39,
            "tasks_total": 50,
            "highlights": [
              "CI/CD pipeline migrated to GitHub Actions",
              "Monitoring stack (Prometheus + Grafana) deployed",
              "Staging environment mirrors production"
            ],
            "concerns": []
          },
          {
            "name": "Data Platform",
            "slug": "data-platform",
            "status": "on_track",
            "status_label": "On Track",
            "completion_pct": 55,
            "deadline": "2026-05-31",
            "lead": "Rahul Desai",
            "team_size": 6,
            "tasks_completed": 25,
            "tasks_total": 45,
            "highlights": [
              "ETL pipeline processing 2M records/day",
              "Data warehouse schema v2 deployed"
            ],
            "concerns": [
              "Query performance optimization needed for large datasets"
            ]
          }
        ]
      }
    },
    {
      "type": "chart",
      "title": "Team Allocation by Project",
      "chart_spec": {
        "tooltip": {
          "trigger": "item",
          "formatter": "{b}: {c} people ({d}%)"
        },
        "legend": {
          "orient": "vertical",
          "left": "right",
          "top": "center"
        },
        "series": [
          {
            "name": "Team Allocation",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["40%", "50%"],
            "avoidLabelOverlap": true,
            "itemStyle": {
              "borderRadius": 6,
              "borderColor": "#fff",
              "borderWidth": 2
            },
            "label": {
              "show": true,
              "formatter": "{b}\n{c} people"
            },
            "data": [
              { "value": 12, "name": "Project Alpha", "itemStyle": { "color": "#3B82F6" } },
              { "value": 8, "name": "Project Beta", "itemStyle": { "color": "#10B981" } },
              { "value": 10, "name": "Project Gamma", "itemStyle": { "color": "#EF4444" } },
              { "value": 5, "name": "Platform Infra", "itemStyle": { "color": "#F59E0B" } },
              { "value": 6, "name": "Data Platform", "itemStyle": { "color": "#8B5CF6" } },
              { "value": 15, "name": "Sales & Marketing", "itemStyle": { "color": "#EC4899" } },
              { "value": 10, "name": "Customer Success", "itemStyle": { "color": "#14B8A6" } },
              { "value": 8, "name": "Ops & Finance", "itemStyle": { "color": "#6B7280" } },
              { "value": 6, "name": "Unallocated", "itemStyle": { "color": "#D1D5DB" } }
            ]
          }
        ]
      }
    },
    {
      "type": "risk_list",
      "title": "Risks & Concerns",
      "items": [
        {
          "id": "risk_001",
          "title": "Project Gamma March 15 Deadline",
          "severity": "high",
          "probability": "medium",
          "impact": "high",
          "description": "The AI integration layer for Project Gamma has not started, and the investor demo is scheduled for March 15. The backend API is at 71% but the remaining 29% includes complex endpoints. Current team velocity suggests completion by March 8 at best, leaving minimal buffer for the demo prep.",
          "mitigation": "Reassign 2 engineers from Platform Infra (which is 78% complete and ahead of schedule) to Gamma starting Feb 3. Scope the demo to core features only — defer advanced AI features to post-demo sprint.",
          "owner": "Vikram Patel",
          "status": "mitigation_planned",
          "due_date": "2026-02-03"
        },
        {
          "id": "risk_002",
          "title": "Engineer Overutilization — Priya S. & Arjun M.",
          "severity": "medium",
          "probability": "high",
          "impact": "medium",
          "description": "Priya Sharma (Project Alpha lead) and Arjun Mehta (Project Beta lead) are both at 110%+ utilization for 3 consecutive weeks. Both are assigned to their project leadership roles plus cross-cutting architecture reviews. Sustained overload risks burnout and quality degradation.",
          "mitigation": "Delegate architecture review responsibilities to senior engineers on each team. Priya can delegate to Kiran (Senior BE), Arjun to Maya (Senior FE). Reduce their task load by 20% for February.",
          "owner": "COO",
          "status": "action_required",
          "due_date": "2026-02-07"
        },
        {
          "id": "risk_003",
          "title": "Third-Party Payment Integration Delay",
          "severity": "low",
          "probability": "medium",
          "impact": "low",
          "description": "The payment gateway vendor (Razorpay) has delayed their sandbox API update by 2 weeks. This affects Project Alpha's payment module but does not block other work streams. The team has implemented a mock layer and can integrate when the API is ready.",
          "mitigation": "Continue with mock layer. Payment module is on the critical path for Phase 3 (May), not the current sprint. Monitor vendor timeline weekly.",
          "owner": "Priya Sharma",
          "status": "monitoring",
          "due_date": null
        }
      ]
    },
    {
      "type": "recommendations",
      "title": "Recommendations",
      "items": [
        {
          "priority": "high",
          "action": "Reassign 2 engineers from Platform Infra to Project Gamma by Feb 3",
          "rationale": "Platform Infra is 78% complete and ahead of schedule. Gamma needs additional capacity to meet the March 15 demo deadline.",
          "owner": "COO",
          "deadline": "2026-02-03"
        },
        {
          "priority": "high",
          "action": "Schedule mid-February architecture review with CTO for Gamma's AI integration",
          "rationale": "The AI layer is the most technically uncertain component. An architecture review before implementation begins will prevent rework.",
          "owner": "Vikram Patel",
          "deadline": "2026-02-14"
        },
        {
          "priority": "medium",
          "action": "Reduce Priya and Arjun's task loads by 20% and delegate architecture reviews",
          "rationale": "Both leads are at 110%+ utilization for 3 weeks. Delegation to senior team members prevents burnout without losing quality.",
          "owner": "COO",
          "deadline": "2026-02-07"
        },
        {
          "priority": "medium",
          "action": "Scope Gamma investor demo to core features only — defer advanced AI to post-demo sprint",
          "rationale": "Attempting full feature set by March 15 is high risk. A polished demo of core features is more impactful than a rushed full demo.",
          "owner": "Vikram Patel",
          "deadline": "2026-02-10"
        },
        {
          "priority": "low",
          "action": "Begin hiring pipeline for ML Engineer to support Gamma and future AI products",
          "rationale": "Current ML capacity is stretched. A dedicated ML engineer would accelerate Gamma and support the broader AI platform roadmap.",
          "owner": "HR Lead",
          "deadline": "2026-02-28"
        }
      ]
    }
  ]
}
```

---

## 5. Section Types

Each section type maps to a specific React component in the preview and a Jinja2 template for PDF export.

### executive_summary

Narrative text block summarizing the report's key findings. Written in the COO's voice for the target audience.

| Property | Type | Description |
|----------|------|-------------|
| `content` | `string` | Multi-paragraph narrative text. Supports markdown-style formatting (bold, lists). |

**Rendering:** Full-width text block with professional typography. In PDF, this is the first page content after the cover page.

### metrics_grid

Grid of KPI cards with current values, previous values, and trend indicators.

| Property | Type | Description |
|----------|------|-------------|
| `data.metrics` | `array` | Array of metric objects |
| `data.metrics[].label` | `string` | Metric name (e.g., "Tasks Completed") |
| `data.metrics[].value` | `number` | Current value |
| `data.metrics[].previous_value` | `number` | Previous period value for comparison |
| `data.metrics[].trend` | `string` | `"up"` / `"down"` / `"flat"` |
| `data.metrics[].trend_pct` | `number` | Percentage change |
| `data.metrics[].unit` | `string` | Unit label (e.g., "%", "pts/sprint", "people") |
| `data.metrics[].color` | `string` | Hex color for the card accent |

**Rendering:** 2-3 column grid of metric cards. Each card shows the value prominently, with a trend arrow and percentage change. Green for positive trends, red for negative, gray for flat.

### chart

Any ECharts visualization. The `chart_spec` is a complete ECharts `option` object that can be passed directly to `echarts.setOption()`.

| Property | Type | Description |
|----------|------|-------------|
| `chart_spec` | `object` | Complete ECharts option config |

**Supported chart types via ECharts:**
- Bar chart (horizontal/vertical, stacked/grouped)
- Line chart (single/multi-series, area)
- Pie / Donut chart
- Scatter plot
- Heatmap
- Radar chart
- Gantt chart (via custom series)
- Treemap
- Sankey diagram

**Rendering (preview):** Interactive ECharts instance with tooltips, zoom, and legend toggling. **Rendering (PDF):** Static SVG generated server-side by pyecharts.

### project_cards

Grid of status cards for multiple projects. Each card shows key project info at a glance.

| Property | Type | Description |
|----------|------|-------------|
| `data.projects` | `array` | Array of project objects |
| `data.projects[].name` | `string` | Project name |
| `data.projects[].status` | `string` | `"on_track"` / `"at_risk"` / `"blocked"` / `"completed"` |
| `data.projects[].status_label` | `string` | Human-readable status |
| `data.projects[].completion_pct` | `number` | 0-100 completion percentage |
| `data.projects[].deadline` | `string` | ISO date |
| `data.projects[].lead` | `string` | Project lead name |
| `data.projects[].team_size` | `number` | Number of people assigned |
| `data.projects[].tasks_completed` | `number` | Completed task count |
| `data.projects[].tasks_total` | `number` | Total task count |
| `data.projects[].highlights` | `array[string]` | Positive highlights |
| `data.projects[].concerns` | `array[string]` | Concerns or issues |

**Rendering:** Card grid (2 columns in preview, 1 column in PDF). Each card has a colored status indicator (green/yellow/red), progress bar, and expandable highlights/concerns.

### table

Generic tabular data with headers and rows.

| Property | Type | Description |
|----------|------|-------------|
| `data.headers` | `array[string]` | Column header labels |
| `data.rows` | `array[array]` | Row data (array of arrays) |
| `data.column_types` | `array[string]` | Optional type hints: `"text"`, `"number"`, `"percentage"`, `"date"`, `"status"` |
| `data.sortable` | `boolean` | Whether columns are sortable in preview |
| `data.highlight_rules` | `array[object]` | Optional conditional formatting rules |

**Rendering (preview):** Interactive table with sorting, search, and pagination. **Rendering (PDF):** Static table with zebra striping and professional formatting.

### risk_list

List of risk items with severity indicators, descriptions, mitigation plans, and owners.

| Property | Type | Description |
|----------|------|-------------|
| `items` | `array` | Array of risk objects |
| `items[].id` | `string` | Unique risk identifier |
| `items[].title` | `string` | Risk title |
| `items[].severity` | `string` | `"critical"` / `"high"` / `"medium"` / `"low"` |
| `items[].probability` | `string` | `"high"` / `"medium"` / `"low"` |
| `items[].impact` | `string` | `"high"` / `"medium"` / `"low"` |
| `items[].description` | `string` | Detailed description |
| `items[].mitigation` | `string` | Mitigation plan |
| `items[].owner` | `string` | Person responsible |
| `items[].status` | `string` | `"action_required"` / `"mitigation_planned"` / `"monitoring"` / `"resolved"` |
| `items[].due_date` | `string` or `null` | ISO date for mitigation action |

**Rendering:** Vertical list of risk cards with colored severity badges. Critical/high risks are visually prominent.

### recommendations

Bullet-point action items with priority, rationale, owner, and deadline.

| Property | Type | Description |
|----------|------|-------------|
| `items` | `array` | Array of recommendation objects |
| `items[].priority` | `string` | `"high"` / `"medium"` / `"low"` |
| `items[].action` | `string` | The recommended action |
| `items[].rationale` | `string` | Why this is recommended |
| `items[].owner` | `string` | Who should take this action |
| `items[].deadline` | `string` | ISO date target |

**Rendering:** Ordered list with priority badges. High-priority items appear first with visual emphasis.

### narrative

Free-form text paragraphs. Used for analysis sections, blocker analysis, feasibility concerns, and similar prose content.

| Property | Type | Description |
|----------|------|-------------|
| `content` | `string` | Multi-paragraph text. Supports markdown formatting. |

**Rendering:** Full-width text block. Same as `executive_summary` but without the special positioning.

### person_grid

Grid of team member cards with per-person metrics.

| Property | Type | Description |
|----------|------|-------------|
| `data.people` | `array` | Array of person objects |
| `data.people[].name` | `string` | Full name |
| `data.people[].role` | `string` | Job title/role |
| `data.people[].avatar_url` | `string` or `null` | Profile image URL |
| `data.people[].projects` | `array[string]` | Assigned project names |
| `data.people[].tasks_completed` | `number` | Tasks completed in period |
| `data.people[].tasks_total` | `number` | Total tasks assigned |
| `data.people[].utilization_pct` | `number` | 0-100+ utilization percentage |
| `data.people[].status` | `string` | `"healthy"` / `"over_utilized"` / `"under_utilized"` |

**Rendering:** Card grid showing each person with their metrics. Color-coded utilization (green = healthy, yellow = approaching limit, red = over-utilized).

### gantt

Timeline / Gantt chart visualization for project or task scheduling.

| Property | Type | Description |
|----------|------|-------------|
| `chart_spec` | `object` | ECharts config for a horizontal bar/custom chart representing the Gantt |
| `data.milestones` | `array` | Optional milestone markers |
| `data.milestones[].name` | `string` | Milestone name |
| `data.milestones[].date` | `string` | ISO date |
| `data.today_marker` | `boolean` | Whether to show a "today" vertical line |

**Rendering (preview):** Interactive ECharts Gantt with zoom and tooltips. **Rendering (PDF):** Static SVG with milestone markers and today indicator.

### checklist

Checklist items with completion status. Used for technical readiness, compliance, and task tracking.

| Property | Type | Description |
|----------|------|-------------|
| `items` | `array` | Array of checklist items |
| `items[].label` | `string` | Checklist item description |
| `items[].status` | `string` | `"done"` / `"pending"` / `"missing"` / `"blocked"` |
| `items[].notes` | `string` or `null` | Optional additional notes |
| `items[].assignee` | `string` or `null` | Person responsible |

**Rendering:** Vertical checklist with colored status icons. Done = green checkmark, Pending = yellow clock, Missing = red X, Blocked = red lock. Summary line at top: "14/20 complete (70%)."

---

## 6. NL Report Editing

After the initial report is generated, the COO reviews the preview and makes adjustments entirely through conversation. Each edit instruction is processed by the AI, which modifies the `report_spec` accordingly. The frontend re-renders instantly from the updated spec.

### Edit Operations

| COO Says | Operation | What Changes |
|----------|-----------|-------------|
| "Add a section on the hiring pipeline" | `INSERT` | AI generates a new section (type determined by content) and inserts it at a logical position |
| "Add a chart showing sprint velocity over time after the metrics" | `INSERT` | AI generates a `chart` section with ECharts line chart config, inserts after metrics_grid |
| "Remove the technical details" | `REMOVE` | AI identifies which sections are "technical details" and removes them |
| "Remove the last section" | `REMOVE` | Removes the final section from the array |
| "Make the executive summary shorter" | `REWRITE` | AI rewrites the executive_summary content to be more concise |
| "Rewrite the recommendations in bullet points" | `REWRITE` | AI reformats the recommendations section |
| "Change the chart to a pie chart" | `UPDATE_CHART` | AI modifies the chart_spec to use `type: "pie"` instead of the current chart type |
| "Make the team allocation chart a bar chart instead" | `UPDATE_CHART` | AI rewrites chart_spec from pie to horizontal bar |
| "Move risks above project cards" | `REORDER` | AI swaps section positions in the sections array |
| "Put the recommendations at the end" | `REORDER` | AI moves the recommendations section to the last position |
| "The Alpha completion should say 62%" | `UPDATE_DATA` | AI finds the Project Alpha card and updates `completion_pct` to 62 |
| "Priya's team has 14 people, not 12" | `UPDATE_DATA` | AI finds Priya's project card and updates `team_size` to 14 |
| "Change the title to Q4 Operations Review" | `UPDATE_META` | AI updates `report_spec.title` |
| "This is for the CEO, not the board" | `UPDATE_META` + `REWRITE` | AI updates audience in meta and rewrites tone-sensitive sections |

### Edit Processing Pipeline

```
COO: "Move risks above project cards and make the summary shorter"
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  EDIT INTENT PARSER                                          │
│                                                              │
│  Detects TWO operations:                                     │
│  1. REORDER: move risk_list before project_cards             │
│  2. REWRITE: shorten executive_summary                       │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  SPEC MODIFIER                                               │
│                                                              │
│  Input: current report_spec + edit operations                │
│                                                              │
│  1. Find risk_list section (index 4)                         │
│  2. Find project_cards section (index 2)                     │
│  3. Move risk_list to index 2, shift project_cards to 3      │
│  4. Send executive_summary content to AI with "make shorter" │
│  5. Replace executive_summary content with shorter version   │
│                                                              │
│  Output: modified report_spec                                │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
Frontend receives updated spec → re-renders instantly
```

### Edit Prompt

```
You are editing a report based on the COO's instruction.

CURRENT REPORT SPEC:
{current_report_spec_json}

COO'S EDIT INSTRUCTION: "{edit_instruction}"

Determine the edit operations needed and apply them to the report_spec.
Return the COMPLETE modified report_spec as JSON.

Rules:
- Only modify what the COO asked for. Do not change other sections.
- For INSERT operations, generate complete section data.
- For REWRITE operations, maintain the same data but adjust the prose.
- For REORDER operations, only change the order of the sections array.
- For UPDATE_DATA operations, change only the specific data point mentioned.
- For REMOVE operations, delete the section(s) from the array.
- Preserve all section IDs, types, and data that were not mentioned.
```

### Edit Implementation

```python
# services/report_editor.py

import json
from typing import Any

class ReportEditor:
    """Processes NL edit instructions and modifies the report_spec."""

    def __init__(self, ai_adapter, data_assembler):
        self.ai = ai_adapter
        self.assembler = data_assembler

    async def apply_edit(
        self,
        current_spec: dict[str, Any],
        edit_instruction: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Apply a NL edit instruction to the report spec."""

        # Classify the edit type(s) first
        classification = await self._classify_edit(
            current_spec, edit_instruction
        )

        # For INSERT operations that need new data, fetch it
        if "INSERT" in classification["operations"]:
            additional_data = await self._fetch_data_for_insert(
                classification, tenant_id, current_spec
            )
        else:
            additional_data = None

        # Apply the edit via AI
        prompt = self._build_edit_prompt(
            current_spec=current_spec,
            edit_instruction=edit_instruction,
            classification=classification,
            additional_data=additional_data,
        )

        response = await self.ai.generate_structured(
            prompt=prompt,
            schema="report_spec",
            max_tokens=8000,
        )

        modified_spec = json.loads(response)

        # Preserve immutable fields
        modified_spec["report_id"] = current_spec["report_id"]
        modified_spec["generated_at"] = current_spec["generated_at"]
        modified_spec["branding"] = current_spec["branding"]

        # Increment version
        modified_spec["version"] = current_spec.get("version", 1) + 1

        return modified_spec

    async def _classify_edit(
        self, current_spec: dict, instruction: str
    ) -> dict:
        """Classify the edit instruction into operation types."""
        prompt = f"""Classify the following report edit instruction into
operations. The current report has these sections:
{json.dumps([
    {"index": i, "type": s["type"], "title": s["title"]}
    for i, s in enumerate(current_spec["sections"])
], indent=2)}

Edit instruction: "{instruction}"

Return JSON:
{{
  "operations": ["INSERT" | "REMOVE" | "REWRITE" | "REORDER" |
                  "UPDATE_DATA" | "UPDATE_CHART" | "UPDATE_META"],
  "target_sections": [list of section indices affected],
  "needs_new_data": true/false,
  "description": "brief description of what will change"
}}"""

        response = await self.ai.generate_structured(
            prompt=prompt, schema="edit_classification", max_tokens=500
        )
        return json.loads(response)

    async def _fetch_data_for_insert(
        self, classification: dict, tenant_id: str, current_spec: dict
    ) -> dict | None:
        """Fetch additional data if the insert needs fresh data."""
        if not classification.get("needs_new_data"):
            return None

        # Use the same data assembly pipeline with the report's scope
        meta = current_spec.get("meta", {})
        return await self.assembler.assemble(
            report_type=meta.get("report_type", "custom"),
            time_scope=meta.get("time_scope", {}),
            projects=meta.get("projects", []),
            people=meta.get("people", []),
            tenant_id=tenant_id,
        )

    def _build_edit_prompt(
        self,
        current_spec: dict,
        edit_instruction: str,
        classification: dict,
        additional_data: dict | None,
    ) -> str:
        prompt = f"""You are editing a report based on the COO's instruction.

CURRENT REPORT SPEC:
{json.dumps(current_spec, indent=2, default=str)}

COO'S EDIT INSTRUCTION: "{edit_instruction}"

CLASSIFIED OPERATIONS: {json.dumps(classification)}
"""
        if additional_data:
            prompt += f"""
ADDITIONAL DATA (for new sections):
{json.dumps(additional_data, indent=2, default=str)}
"""
        prompt += """
Return the COMPLETE modified report_spec as JSON.
Only modify what the COO asked for. Preserve everything else exactly.
"""
        return prompt
```

### Conversation Flow Example

```
COO: "Generate a board ops summary for January"

ChiefOps: "Here's your January Board Operations Summary. I've included
6 sections: Executive Summary, Key Metrics, Project Status (5 projects),
Team Allocation chart, Risks (3 items), and Recommendations (5 items).

Take a look at the preview — let me know if you'd like any changes."

[Preview renders in the report panel]

COO: "The Alpha completion should say 62%, not 58%"

ChiefOps: "Updated — Project Alpha now shows 62% completion."

[Preview re-renders with the corrected number]

COO: "Move the risks section up, right after the executive summary.
The board always wants to see risks early."

ChiefOps: "Done — Risks & Concerns is now the second section, right
after the Executive Summary."

[Preview re-renders with reordered sections]

COO: "Add a section on hiring pipeline progress"

ChiefOps: "Added a new 'Hiring Pipeline' section after Team Allocation.
It shows 3 open positions, 2 offers extended, and the recent hires
(Senior BE, Product Designer). Want me to adjust anything?"

[Preview re-renders with the new section]

COO: "Perfect. Make the exec summary a bit shorter — two paragraphs max."

ChiefOps: "Shortened the Executive Summary to two paragraphs. Kept the
key points: velocity up 18%, Beta Phase 1 complete, Gamma at-risk for
March 15, and the top recommendations."

COO: "Looks great. Export to PDF."

ChiefOps: "Your PDF is ready. [Download: Board_Ops_Summary_Jan_2026.pdf]"
```

---

## 7. PDF Generation Pipeline

### Overview

The PDF pipeline converts the `report_spec` JSON into a professional, print-ready PDF document. The process has three stages: HTML generation (Jinja2), chart rendering (pyecharts to SVG), and PDF conversion (WeasyPrint).

### Template Engine (Jinja2)

Each section type has its own Jinja2 template. A base template wraps them all with consistent branding, headers, footers, and page numbering.

**Base template:**

```html
{# templates/reports/base_report.html #}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ report.title }}</title>
  <style>
    @page {
      size: A4;
      margin: 2.5cm 2cm 3cm 2cm;

      @top-left {
        content: "{{ report.branding.company }}";
        font-size: 9pt;
        color: #6B7280;
        font-family: 'Inter', sans-serif;
      }
      @top-right {
        content: "{{ report.title }}";
        font-size: 9pt;
        color: #6B7280;
        font-family: 'Inter', sans-serif;
      }
      @bottom-center {
        content: counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #6B7280;
        font-family: 'Inter', sans-serif;
      }
      @bottom-right {
        content: "Generated {{ report.generated_at | format_date }}";
        font-size: 8pt;
        color: #9CA3AF;
        font-family: 'Inter', sans-serif;
      }
    }

    @page :first {
      @top-left { content: none; }
      @top-right { content: none; }
    }

    /* Base typography */
    body {
      font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.6;
      color: #1F2937;
    }

    h1 { font-size: 24pt; font-weight: 700; color: #111827; margin-bottom: 4pt; }
    h2 { font-size: 16pt; font-weight: 600; color: #1F2937; margin-top: 24pt;
         border-bottom: 2px solid {{ report.branding.primary_color | default('#3B82F6') }};
         padding-bottom: 6pt; page-break-after: avoid; }
    h3 { font-size: 13pt; font-weight: 600; color: #374151; }
    p  { margin-bottom: 8pt; }

    /* Prevent orphans/widows */
    p, li { orphans: 3; widows: 3; }

    /* Section breaks */
    .section { page-break-inside: avoid; margin-bottom: 20pt; }
    .section-break { page-break-before: always; }

    /* Cover page */
    .cover-page {
      text-align: center;
      padding-top: 30%;
    }
    .cover-page .logo { max-width: 200px; margin-bottom: 40pt; }
    .cover-page .title { font-size: 32pt; font-weight: 700; color: #111827; }
    .cover-page .subtitle { font-size: 16pt; color: #6B7280; margin-top: 12pt; }
    .cover-page .date { font-size: 12pt; color: #9CA3AF; margin-top: 24pt; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; margin: 12pt 0; font-size: 10pt; }
    th { background-color: #F3F4F6; font-weight: 600; text-align: left;
         padding: 8pt 10pt; border-bottom: 2px solid #D1D5DB; }
    td { padding: 6pt 10pt; border-bottom: 1px solid #E5E7EB; }
    tr:nth-child(even) td { background-color: #F9FAFB; }

    /* Metrics grid */
    .metrics-grid { display: flex; flex-wrap: wrap; gap: 12pt; }
    .metric-card { flex: 1 1 30%; border: 1px solid #E5E7EB; border-radius: 6pt;
                   padding: 14pt; min-width: 150pt; }
    .metric-value { font-size: 24pt; font-weight: 700; }
    .metric-label { font-size: 10pt; color: #6B7280; margin-top: 4pt; }
    .metric-trend { font-size: 10pt; margin-top: 4pt; }
    .trend-up { color: #10B981; }
    .trend-down { color: #EF4444; }
    .trend-flat { color: #6B7280; }

    /* Project cards */
    .project-card { border: 1px solid #E5E7EB; border-radius: 6pt;
                    padding: 14pt; margin-bottom: 12pt; page-break-inside: avoid; }
    .project-card .status-badge { display: inline-block; padding: 2pt 8pt;
                                  border-radius: 4pt; font-size: 9pt; font-weight: 600; }
    .status-on_track { background-color: #D1FAE5; color: #065F46; }
    .status-at_risk { background-color: #FEF3C7; color: #92400E; }
    .status-blocked { background-color: #FEE2E2; color: #991B1B; }

    /* Progress bar */
    .progress-bar { height: 8pt; background-color: #E5E7EB; border-radius: 4pt;
                    margin: 8pt 0; }
    .progress-fill { height: 100%; border-radius: 4pt; }

    /* Risk cards */
    .risk-card { border-left: 4pt solid; padding: 12pt 14pt; margin-bottom: 12pt;
                 page-break-inside: avoid; background-color: #FAFAFA; }
    .risk-critical { border-left-color: #991B1B; }
    .risk-high { border-left-color: #EF4444; }
    .risk-medium { border-left-color: #F59E0B; }
    .risk-low { border-left-color: #6B7280; }

    /* Severity badge */
    .severity-badge { display: inline-block; padding: 2pt 8pt; border-radius: 4pt;
                      font-size: 9pt; font-weight: 600; text-transform: uppercase; }
    .severity-critical { background-color: #FEE2E2; color: #991B1B; }
    .severity-high { background-color: #FEE2E2; color: #DC2626; }
    .severity-medium { background-color: #FEF3C7; color: #92400E; }
    .severity-low { background-color: #F3F4F6; color: #6B7280; }

    /* Recommendations */
    .recommendation { padding: 10pt 14pt; margin-bottom: 8pt; border-radius: 6pt;
                      background-color: #F0F9FF; page-break-inside: avoid; }
    .recommendation .priority { font-size: 9pt; font-weight: 600;
                                text-transform: uppercase; margin-bottom: 4pt; }
    .priority-high { color: #DC2626; }
    .priority-medium { color: #D97706; }
    .priority-low { color: #6B7280; }

    /* Checklist */
    .checklist-item { display: flex; align-items: flex-start; gap: 8pt;
                      padding: 6pt 0; }
    .checklist-icon { font-size: 14pt; line-height: 1; }
    .checklist-done .checklist-icon { color: #10B981; }
    .checklist-pending .checklist-icon { color: #F59E0B; }
    .checklist-missing .checklist-icon { color: #EF4444; }
    .checklist-blocked .checklist-icon { color: #DC2626; }

    /* Person grid */
    .person-grid { display: flex; flex-wrap: wrap; gap: 12pt; }
    .person-card { flex: 1 1 45%; border: 1px solid #E5E7EB; border-radius: 6pt;
                   padding: 12pt; page-break-inside: avoid; }

    /* Charts (embedded SVG) */
    .chart-container { text-align: center; margin: 16pt 0; page-break-inside: avoid; }
    .chart-container svg { max-width: 100%; }
  </style>
</head>
<body>

  {# Cover Page #}
  <div class="cover-page">
    {% if report.branding.logo_url %}
    <img src="{{ report.branding.logo_url }}" alt="{{ report.branding.company }}"
         class="logo">
    {% endif %}
    <div class="title">{{ report.title }}</div>
    {% if report.subtitle %}
    <div class="subtitle">{{ report.subtitle }}</div>
    {% endif %}
    <div class="date">Generated {{ report.generated_at | format_date }}</div>
  </div>

  <div class="section-break"></div>

  {# Table of Contents #}
  <h2>Table of Contents</h2>
  <ol>
    {% for section in report.sections %}
    <li>{{ section.title }}</li>
    {% endfor %}
  </ol>

  {# Sections #}
  {% for section in report.sections %}
  <div class="section-break"></div>
  {% include "reports/sections/" + section.type + ".html" %}
  {% endfor %}

</body>
</html>
```

**Section templates (examples):**

```html
{# templates/reports/sections/executive_summary.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  {{ section.content | markdown_to_html | safe }}
</div>
```

```html
{# templates/reports/sections/metrics_grid.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  <div class="metrics-grid">
    {% for metric in section.data.metrics %}
    <div class="metric-card">
      <div class="metric-value" style="color: {{ metric.color }}">
        {{ metric.value }}{{ metric.unit }}
      </div>
      <div class="metric-label">{{ metric.label }}</div>
      <div class="metric-trend trend-{{ metric.trend }}">
        {% if metric.trend == 'up' %}&#9650;{% elif metric.trend == 'down' %}&#9660;{% else %}&#9654;{% endif %}
        {% if metric.trend_pct %}{{ metric.trend_pct }}% vs last period{% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
```

```html
{# templates/reports/sections/project_cards.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  {% for project in section.data.projects %}
  <div class="project-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h3 style="margin: 0;">{{ project.name }}</h3>
      <span class="status-badge status-{{ project.status }}">{{ project.status_label }}</span>
    </div>
    <div style="font-size: 10pt; color: #6B7280; margin-top: 4pt;">
      Lead: {{ project.lead }} &middot; Team: {{ project.team_size }} &middot;
      Deadline: {{ project.deadline | format_date }}
    </div>
    <div class="progress-bar">
      <div class="progress-fill"
           style="width: {{ project.completion_pct }}%;
                  background-color: {% if project.status == 'on_track' %}#10B981{% elif project.status == 'at_risk' %}#F59E0B{% else %}#EF4444{% endif %};">
      </div>
    </div>
    <div style="font-size: 10pt;">
      {{ project.tasks_completed }}/{{ project.tasks_total }} tasks
      ({{ project.completion_pct }}%)
    </div>
    {% if project.highlights %}
    <div style="margin-top: 8pt;">
      <strong style="font-size: 10pt; color: #10B981;">Highlights:</strong>
      <ul style="font-size: 10pt; margin: 4pt 0;">
        {% for h in project.highlights %}<li>{{ h }}</li>{% endfor %}
      </ul>
    </div>
    {% endif %}
    {% if project.concerns %}
    <div style="margin-top: 4pt;">
      <strong style="font-size: 10pt; color: #EF4444;">Concerns:</strong>
      <ul style="font-size: 10pt; margin: 4pt 0;">
        {% for c in project.concerns %}<li>{{ c }}</li>{% endfor %}
      </ul>
    </div>
    {% endif %}
  </div>
  {% endfor %}
</div>
```

```html
{# templates/reports/sections/risk_list.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  {% for risk in section.items %}
  <div class="risk-card risk-{{ risk.severity }}">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h3 style="margin: 0; font-size: 12pt;">{{ risk.title }}</h3>
      <span class="severity-badge severity-{{ risk.severity }}">{{ risk.severity }}</span>
    </div>
    <p style="font-size: 10pt; margin-top: 8pt;">{{ risk.description }}</p>
    <div style="font-size: 10pt; background: #F0FDF4; padding: 8pt; border-radius: 4pt; margin-top: 8pt;">
      <strong>Mitigation:</strong> {{ risk.mitigation }}
    </div>
    <div style="font-size: 9pt; color: #6B7280; margin-top: 6pt;">
      Owner: {{ risk.owner }} &middot;
      Status: {{ risk.status | replace('_', ' ') | title }}
      {% if risk.due_date %} &middot; Due: {{ risk.due_date | format_date }}{% endif %}
    </div>
  </div>
  {% endfor %}
</div>
```

```html
{# templates/reports/sections/recommendations.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  {% for rec in section.items %}
  <div class="recommendation">
    <div class="priority priority-{{ rec.priority }}">{{ rec.priority }} priority</div>
    <div style="font-weight: 600; margin-bottom: 4pt;">{{ rec.action }}</div>
    <div style="font-size: 10pt; color: #4B5563;">{{ rec.rationale }}</div>
    <div style="font-size: 9pt; color: #6B7280; margin-top: 6pt;">
      Owner: {{ rec.owner }} &middot; Target: {{ rec.deadline | format_date }}
    </div>
  </div>
  {% endfor %}
</div>
```

```html
{# templates/reports/sections/chart.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  <div class="chart-container">
    {{ section.rendered_svg | safe }}
  </div>
</div>
```

```html
{# templates/reports/sections/checklist.html #}
<div class="section">
  <h2>{{ section.title }}</h2>
  {% set done_count = section.items | selectattr('status', 'equalto', 'done') | list | length %}
  {% set total_count = section.items | length %}
  <div style="font-size: 10pt; color: #6B7280; margin-bottom: 12pt;">
    {{ done_count }}/{{ total_count }} complete ({{ (done_count / total_count * 100) | round }}%)
  </div>
  {% for item in section.items %}
  <div class="checklist-item checklist-{{ item.status }}">
    <span class="checklist-icon">
      {% if item.status == 'done' %}&#10003;{% elif item.status == 'pending' %}&#9711;{% elif item.status == 'missing' %}&#10007;{% else %}&#128274;{% endif %}
    </span>
    <div>
      <div>{{ item.label }}</div>
      {% if item.notes %}
      <div style="font-size: 9pt; color: #6B7280;">{{ item.notes }}</div>
      {% endif %}
      {% if item.assignee %}
      <div style="font-size: 9pt; color: #9CA3AF;">Assignee: {{ item.assignee }}</div>
      {% endif %}
    </div>
  </div>
  {% endfor %}
</div>
```

### Chart Rendering for PDF

In the browser preview, charts are interactive ECharts instances. For PDF export, they must be converted to static SVG images that can be embedded in the HTML.

**Approach: pyecharts (Python ECharts) for server-side rendering**

pyecharts provides a Python API that mirrors the ECharts JavaScript API. Since the `report_spec` already contains ECharts-compatible configs in `chart_spec`, conversion is straightforward.

```python
# services/chart_renderer.py

from pyecharts.charts import Bar, Line, Pie, Scatter, HeatMap, Radar
from pyecharts import options as opts
from pyecharts.render import make_snapshot
from snapshot_pyppeteer import snapshot as pyppeteer_snapshot
import json
import tempfile
import os


class ChartRenderer:
    """Renders ECharts configs to SVG for PDF embedding."""

    def render_chart_to_svg(self, chart_spec: dict) -> str:
        """Convert an ECharts option config to SVG string.

        Args:
            chart_spec: Complete ECharts option object from report_spec.

        Returns:
            SVG string that can be embedded in HTML.
        """
        # Determine chart type from the series
        series = chart_spec.get("series", [])
        if not series:
            return self._empty_chart_svg()

        chart_type = series[0].get("type", "bar")

        # Create pyecharts chart based on type
        chart = self._create_chart(chart_type, chart_spec)

        # Render to SVG
        svg_content = chart.render_notebook()  # Returns SVG for embedding

        return svg_content

    def render_all_charts(self, report_spec: dict) -> dict:
        """Render all chart sections in a report to SVG.

        Returns a dict mapping section index to SVG string.
        """
        rendered = {}
        for i, section in enumerate(report_spec.get("sections", [])):
            if section.get("type") in ("chart", "gantt") and section.get("chart_spec"):
                svg = self.render_chart_to_svg(section["chart_spec"])
                rendered[i] = svg
        return rendered

    def _create_chart(self, chart_type: str, spec: dict):
        """Create a pyecharts chart object from an ECharts spec."""
        width = "720px"
        height = "400px"

        if chart_type == "pie":
            chart = Pie(init_opts=opts.InitOpts(
                width=width, height=height,
                renderer="svg"
            ))
            for s in spec.get("series", []):
                chart.add(
                    series_name=s.get("name", ""),
                    data_pair=[
                        (d["name"], d["value"])
                        for d in s.get("data", [])
                    ],
                    radius=s.get("radius", ["40%", "70%"]),
                    center=s.get("center", ["50%", "50%"]),
                )

        elif chart_type == "bar":
            chart = Bar(init_opts=opts.InitOpts(
                width=width, height=height,
                renderer="svg"
            ))
            x_data = spec.get("xAxis", {})
            if isinstance(x_data, list) and x_data:
                x_data = x_data[0]
            categories = x_data.get("data", []) if isinstance(x_data, dict) else []
            chart.add_xaxis(categories)
            for s in spec.get("series", []):
                chart.add_yaxis(
                    series_name=s.get("name", ""),
                    y_axis=s.get("data", []),
                )

        elif chart_type == "line":
            chart = Line(init_opts=opts.InitOpts(
                width=width, height=height,
                renderer="svg"
            ))
            x_data = spec.get("xAxis", {})
            if isinstance(x_data, list) and x_data:
                x_data = x_data[0]
            categories = x_data.get("data", []) if isinstance(x_data, dict) else []
            chart.add_xaxis(categories)
            for s in spec.get("series", []):
                chart.add_yaxis(
                    series_name=s.get("name", ""),
                    y_axis=s.get("data", []),
                    is_smooth=s.get("smooth", False),
                )

        else:
            # Fallback: render as bar chart
            chart = Bar(init_opts=opts.InitOpts(
                width=width, height=height,
                renderer="svg"
            ))

        # Apply common options
        if spec.get("title"):
            title = spec["title"]
            chart.set_global_opts(
                title_opts=opts.TitleOpts(
                    title=title.get("text", ""),
                    subtitle=title.get("subtext", ""),
                )
            )

        if spec.get("tooltip"):
            chart.set_global_opts(
                tooltip_opts=opts.TooltipOpts(
                    trigger=spec["tooltip"].get("trigger", "item")
                )
            )

        return chart

    def _empty_chart_svg(self) -> str:
        return (
            '<svg width="720" height="400" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="100%" height="100%" fill="#F9FAFB"/>'
            '<text x="360" y="200" text-anchor="middle" fill="#9CA3AF" '
            'font-family="Inter, sans-serif" font-size="14">'
            'No chart data available</text></svg>'
        )
```

**Alternative: Node.js ECharts SSR (for higher fidelity)**

If pyecharts does not produce sufficient fidelity for complex charts (Gantt, heatmaps, Sankey), a Node.js sidecar can render ECharts server-side:

```javascript
// scripts/render-chart.js
// Called from Python via subprocess

const echarts = require('echarts');
const { createCanvas } = require('canvas');
const { JSDOM } = require('jsdom');

function renderToSVG(optionJSON) {
  const option = JSON.parse(optionJSON);

  // Create a virtual DOM for SSR
  const { document } = new JSDOM('').window;
  const container = document.createElement('div');
  container.style.width = '720px';
  container.style.height = '400px';

  const chart = echarts.init(container, null, {
    renderer: 'svg',
    ssr: true,
    width: 720,
    height: 400,
  });

  chart.setOption(option);
  const svgStr = chart.renderToSVGString();
  chart.dispose();

  return svgStr;
}

// Read from stdin
let input = '';
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  const svg = renderToSVG(input);
  process.stdout.write(svg);
});
```

### WeasyPrint PDF Conversion

WeasyPrint takes the complete HTML document (with embedded SVG charts) and converts it to a professional PDF.

```python
# services/pdf_exporter.py

import weasyprint
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from pathlib import Path
import tempfile

class PDFExporter:
    """Converts a report_spec to a professional PDF."""

    def __init__(self, template_dir: str = "templates/reports"):
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )
        # Register custom filters
        self.jinja_env.filters["format_date"] = self._format_date
        self.jinja_env.filters["markdown_to_html"] = self._markdown_to_html

        self.chart_renderer = ChartRenderer()

    async def export(
        self,
        report_spec: dict,
        output_path: str | None = None,
    ) -> bytes:
        """Generate a PDF from a report_spec.

        Args:
            report_spec: Complete report spec JSON.
            output_path: Optional file path to save the PDF.

        Returns:
            PDF bytes.
        """
        # Step 1: Render all charts to SVG
        chart_svgs = self.chart_renderer.render_all_charts(report_spec)

        # Inject rendered SVGs into sections
        spec_copy = report_spec.copy()
        spec_copy["sections"] = []
        for i, section in enumerate(report_spec["sections"]):
            section_copy = section.copy()
            if i in chart_svgs:
                section_copy["rendered_svg"] = chart_svgs[i]
            spec_copy["sections"].append(section_copy)

        # Step 2: Render HTML from Jinja2 templates
        template = self.jinja_env.get_template("base_report.html")
        html_content = template.render(report=spec_copy, section=None)

        # For section includes, render each section individually
        sections_html = []
        for section in spec_copy["sections"]:
            section_template_name = f"sections/{section['type']}.html"
            try:
                section_template = self.jinja_env.get_template(
                    section_template_name
                )
                section_html = section_template.render(
                    section=section, report=spec_copy
                )
                sections_html.append(section_html)
            except Exception:
                # Fallback: render as narrative
                fallback = self.jinja_env.get_template("sections/narrative.html")
                sections_html.append(
                    fallback.render(section=section, report=spec_copy)
                )

        # Step 3: Combine into final HTML
        full_html = self._assemble_html(spec_copy, sections_html)

        # Step 4: Convert to PDF with WeasyPrint
        pdf_bytes = weasyprint.HTML(string=full_html).write_pdf()

        # Optionally save to file
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        return pdf_bytes

    def _assemble_html(self, report: dict, sections_html: list[str]) -> str:
        """Assemble the complete HTML document."""
        template = self.jinja_env.get_template("base_report.html")
        return template.render(
            report=report,
            sections_rendered=sections_html,
        )

    @staticmethod
    def _format_date(value: str) -> str:
        """Format an ISO date string to a human-readable format."""
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y")
        except (ValueError, AttributeError):
            return str(value)

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """Convert markdown-formatted text to HTML."""
        import markdown
        return markdown.markdown(text, extensions=["extra", "nl2br"])
```

**PDF export API endpoint:**

```python
# api/routes/reports.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/{report_id}/export/pdf")
async def export_report_pdf(
    report_id: str,
    db=Depends(get_db),
    pdf_exporter=Depends(get_pdf_exporter),
    current_user=Depends(get_current_user),
):
    """Export a report to PDF."""
    # Load the report spec from MongoDB
    report = await db.reports.find_one({
        "report_id": report_id,
        "tenant_id": current_user.tenant_id,
    })
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Generate PDF
    pdf_bytes = await pdf_exporter.export(report["report_spec"])

    # Record the export
    await db.reports.update_one(
        {"report_id": report_id},
        {
            "$push": {
                "exports": {
                    "format": "pdf",
                    "exported_at": datetime.utcnow(),
                    "exported_by": current_user.user_id,
                }
            }
        },
    )

    # Build filename
    safe_title = report["report_spec"]["title"].replace(" ", "_")
    filename = f"{safe_title}_{report_id[:8]}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
```

---

## 8. Report Storage & History

### MongoDB Schema: `reports` Collection

```json
{
  "_id": "ObjectId",
  "report_id": "rpt_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tenant_id": "tenant_yensi",
  "title": "Board Operations Summary",
  "report_type": "board_ops_summary",
  "report_spec": { "... complete report_spec JSON ..." },
  "generated_at": "2026-02-01T09:30:00Z",
  "last_modified": "2026-02-01T09:45:00Z",
  "status": "finalized",
  "version": 3,
  "version_history": [
    {
      "version": 1,
      "modified_at": "2026-02-01T09:30:00Z",
      "operation": "generated",
      "description": "Initial generation"
    },
    {
      "version": 2,
      "modified_at": "2026-02-01T09:35:00Z",
      "operation": "edit",
      "description": "Updated Alpha completion to 62%, moved risks above project cards"
    },
    {
      "version": 3,
      "modified_at": "2026-02-01T09:45:00Z",
      "operation": "edit",
      "description": "Added hiring pipeline section, shortened executive summary"
    }
  ],
  "exports": [
    {
      "format": "pdf",
      "exported_at": "2026-02-01T09:50:00Z",
      "exported_by": "user_sarah"
    }
  ],
  "conversation_turns": [
    {
      "role": "user",
      "content": "Generate a board ops summary for January",
      "timestamp": "2026-02-01T09:28:00Z"
    },
    {
      "role": "assistant",
      "content": "Here's your January Board Operations Summary...",
      "timestamp": "2026-02-01T09:30:00Z",
      "action": "report_generated",
      "version": 1
    },
    {
      "role": "user",
      "content": "The Alpha completion should say 62%",
      "timestamp": "2026-02-01T09:33:00Z"
    },
    {
      "role": "assistant",
      "content": "Updated — Project Alpha now shows 62% completion.",
      "timestamp": "2026-02-01T09:33:05Z",
      "action": "report_edited",
      "version": 2
    }
  ],
  "meta": {
    "time_scope": {
      "start": "2026-01-01T00:00:00Z",
      "end": "2026-01-31T23:59:59Z"
    },
    "audience": "board_investors",
    "projects": [],
    "people": []
  },
  "created_at": "2026-02-01T09:30:00Z"
}
```

### Indexes

```javascript
// MongoDB indexes for the reports collection
db.reports.createIndex({ "tenant_id": 1, "generated_at": -1 });
db.reports.createIndex({ "tenant_id": 1, "report_type": 1 });
db.reports.createIndex({ "tenant_id": 1, "report_id": 1 }, { unique: true });
db.reports.createIndex({ "tenant_id": 1, "title": "text" });
```

### Report History Operations

The COO can interact with past reports through conversation:

**Loading from history:**

```
COO: "Show me the report I generated last week"

→ System queries:
  db.reports.find({
    tenant_id: "tenant_yensi",
    generated_at: { $gte: last_week_start, $lte: last_week_end }
  }).sort({ generated_at: -1 }).limit(5)

→ If one report: loads it directly
→ If multiple: "I found 3 reports from last week:
   1. Board Ops Summary (Jan 28)
   2. Project Alpha Status (Jan 27)
   3. Sprint 12 Report (Jan 26)
   Which one would you like to see?"
```

**Updating a previous report with new data:**

```
COO: "Update last month's board report with February data"

→ System:
  1. Loads the January board report spec
  2. Clones the spec (new report_id, preserves structure)
  3. Re-runs data assembly with February time scope
  4. AI regenerates content with new data, same structure
  5. Preview renders the updated report
  6. COO can edit from there
```

**Comparing reports:**

```
COO: "Compare this month's board report with last month"

→ System:
  1. Loads both report specs
  2. AI generates a comparison analysis:
     - Metrics deltas (velocity up 12%, blockers down 3)
     - New risks vs resolved risks
     - Project status changes
     - Headcount changes
  3. Renders a special comparison view with side-by-side metrics
```

### Report Status Lifecycle

```
draft → in_review → finalized → archived
  │                     │
  └─── (COO editing) ───┘

draft:      Initial generation, COO is editing
in_review:  COO has shared for review (future: multi-user)
finalized:  COO is satisfied, exported to PDF
archived:   Old report, kept for history
```

---

## 9. Report Preview UI

The report preview is a dedicated panel in the ChiefOps UI that renders the `report_spec` as a rich, scrollable document alongside the conversation panel.

### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ChiefOps                                        [Dashboard] [Reports] │
├────────────────────────────────────────────┬────────────────────────────┤
│                                            │                            │
│          REPORT PREVIEW PANEL              │    CONVERSATION PANEL      │
│                                            │                            │
│  ┌──────────────────────────────────────┐  │  ┌──────────────────────┐  │
│  │  [YENSI Logo]                       │  │  │  ChiefOps:           │  │
│  │                                      │  │  │  Here's your Jan     │  │
│  │  Board Operations Summary            │  │  │  Board Ops Summary.  │  │
│  │  January 2026 — YENSI Solutions      │  │  │  6 sections...       │  │
│  │                                      │  │  │                      │  │
│  │  ─────────────────────────────────── │  │  │  You:                │  │
│  │                                      │  │  │  Move risks up       │  │
│  │  Executive Summary                   │  │  │                      │  │
│  │  January was a strong operational... │  │  │  ChiefOps:           │  │
│  │                                      │  │  │  Done — Risks is now │  │
│  │  ─────────────────────────────────── │  │  │  section 2.          │  │
│  │                                      │  │  │                      │  │
│  │  Key Metrics                         │  │  │                      │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐           │  │  │                      │  │
│  │  │ 247 │ │ 82% │ │  3  │           │  │  │                      │  │
│  │  │Tasks│ │Util │ │Block│           │  │  │                      │  │
│  │  │▲18% │ │▲5%  │ │▼57% │           │  │  │                      │  │
│  │  └─────┘ └─────┘ └─────┘           │  │  │                      │  │
│  │                                      │  │  │                      │  │
│  │  ─────────────────────────────────── │  │  │                      │  │
│  │                                      │  │  │                      │  │
│  │  Risks & Concerns                    │  │  │                      │  │
│  │  ┌─ HIGH ──────────────────────┐    │  │  │                      │  │
│  │  │ Gamma March 15 Deadline     │    │  │  │                      │  │
│  │  │ AI integration not started  │    │  │  │                      │  │
│  │  └─────────────────────────────┘    │  │  │                      │  │
│  │                                      │  │  │                      │  │
│  │  ... (scrollable)                    │  │  │                      │  │
│  │                                      │  │  │                      │  │
│  └──────────────────────────────────────┘  │  └──────────────────────┘  │
│                                            │                            │
│  [◀ Page 1 of 4 ▶]     [Export to PDF ↓]  │  ┌──────────────────────┐  │
│                                            │  │ Type a message...    │  │
│                                            │  └──────────────────────┘  │
├────────────────────────────────────────────┴────────────────────────────┤
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key UI Features

| Feature | Description |
|---------|-------------|
| **Split panel** | Report preview on the left (60% width), conversation on the right (40% width). Resizable divider. |
| **Scrollable preview** | The report renders as a continuous scroll with section dividers that mirror page breaks in the PDF. |
| **Page indicators** | Optional pagination mode that shows pages as they would appear in the PDF (A4 aspect ratio). |
| **Interactive charts** | ECharts instances are fully interactive — tooltips on hover, legend toggling, zoom on scroll. |
| **Section highlighting** | When the COO references a section in conversation ("Make the summary shorter"), the corresponding section highlights briefly in the preview. |
| **Export button** | Prominent button at the bottom of the preview panel. Triggers PDF generation and download. |
| **Version indicator** | Small badge showing "v3" or "3 edits" so the COO knows how many changes have been made. |
| **Instant re-render** | When the report_spec updates (from an NL edit), the preview re-renders instantly. React diffing ensures only changed sections re-render. |

### React Component Hierarchy

```
<ReportWorkspace>
  ├── <ReportPreviewPanel>
  │     ├── <ReportHeader title subtitle branding />
  │     ├── <ReportSection> (for each section in spec.sections)
  │     │     ├── <NarrativeBlock />
  │     │     ├── <MetricsGrid />
  │     │     ├── <EChartsWrapper />
  │     │     ├── <ProjectCardGrid />
  │     │     ├── <DataTable />
  │     │     ├── <RiskList />
  │     │     ├── <RecommendationsList />
  │     │     ├── <PersonCardGrid />
  │     │     ├── <GanttChart />
  │     │     └── <ChecklistBlock />
  │     ├── <ReportFooter branding />
  │     └── <ExportBar>
  │           ├── <PageIndicator />
  │           ├── <VersionBadge />
  │           └── <ExportButton />
  │
  └── <ConversationPanel>
        ├── <MessageList />
        └── <MessageInput />
```

---

## 10. Branding

Reports are branded with the COO's company identity or YENSI Solutions branding by default.

### Branding Configuration

Branding is stored at the tenant level in the project settings and applied to all reports.

```json
{
  "tenant_id": "tenant_yensi",
  "branding": {
    "company": "YENSI Solutions",
    "logo_url": "/assets/branding/yensi-logo.svg",
    "color_scheme": "yensi_default",
    "primary_color": "#3B82F6",
    "secondary_color": "#1E40AF",
    "accent_color": "#10B981",
    "font_family": "Inter"
  }
}
```

### Color Schemes

ChiefOps ships with preset color schemes. The COO can also specify custom hex values.

| Scheme | Primary | Secondary | Accent | Use Case |
|--------|---------|-----------|--------|----------|
| `yensi_default` | `#3B82F6` (blue) | `#1E40AF` (dark blue) | `#10B981` (green) | YENSI Solutions branding |
| `corporate_blue` | `#1E3A5F` (navy) | `#2C5282` (slate blue) | `#38B2AC` (teal) | Conservative corporate |
| `modern_dark` | `#111827` (charcoal) | `#374151` (dark gray) | `#6366F1` (indigo) | Modern/tech companies |
| `warm_professional` | `#92400E` (amber dark) | `#B45309` (amber) | `#D97706` (gold) | Warm professional tone |
| `minimal` | `#1F2937` (gray-800) | `#6B7280` (gray-500) | `#3B82F6` (blue) | Clean minimal look |
| `custom` | User-defined | User-defined | User-defined | Any company branding |

### Where Branding Appears

| Location | What Shows |
|----------|------------|
| **PDF cover page** | Company logo (centered), company name below logo |
| **PDF page header** | Company name (top-left), report title (top-right) |
| **PDF page footer** | Page number (center), generation date (bottom-right) |
| **Section heading underlines** | Primary color as the border-bottom on h2 elements |
| **Metric card accents** | Individual metric colors, or primary color as default |
| **Progress bars** | Status-based colors (green/yellow/red) with primary as fallback |
| **Chart colors** | Charts use the branding palette unless overridden in chart_spec |
| **Preview header** | Company logo and name in the preview panel header |

### Settings UI

Branding is one of the few settings in ChiefOps that uses a traditional form (not NL). This is because logo upload and hex color picking are inherently visual operations.

```
┌─────────────────────────────────────────────────────┐
│  Settings > Report Branding                         │
│                                                     │
│  Company Name:  [YENSI Solutions          ]         │
│                                                     │
│  Logo:          [yensi-logo.svg]  [Upload New]      │
│                 (Preview: [logo image])              │
│                                                     │
│  Color Scheme:  [▼ yensi_default]                   │
│                                                     │
│  Primary:    [#3B82F6] [■]                          │
│  Secondary:  [#1E40AF] [■]                          │
│  Accent:     [#10B981] [■]                          │
│                                                     │
│  Font:       [▼ Inter]                              │
│                                                     │
│  Preview:                                           │
│  ┌───────────────────────────────────────────┐      │
│  │ [Logo] YENSI Solutions                    │      │
│  │ ─────────────────────────────────── (blue)│      │
│  │ Sample Report Title                       │      │
│  │ ┌─────┐ ┌─────┐ ┌─────┐                 │      │
│  │ │ 42  │ │ 87% │ │  3  │                 │      │
│  │ └─────┘ └─────┘ └─────┘                 │      │
│  └───────────────────────────────────────────┘      │
│                                                     │
│  [Save]                                             │
└─────────────────────────────────────────────────────┘
```

### Logo Requirements

| Property | Requirement |
|----------|-------------|
| **Formats** | SVG (preferred), PNG, JPEG |
| **Max size** | 2 MB |
| **Recommended dimensions** | SVG: any (vector). PNG/JPEG: 400x100px (landscape) or 200x200px (square) |
| **Storage** | Uploaded to tenant's asset storage, served via static asset URL |
| **PDF embedding** | SVG embedded directly. PNG/JPEG base64-encoded into the HTML template. |

---

## Summary

The Report Generation system transforms the COO's natural language into professional, data-driven reports through a six-step pipeline:

1. **Intent Detection** classifies the report type, scope, audience, and tone
2. **Data Assembly** pulls structured data (MongoDB), semantic content (Citex), and context (Memory)
3. **AI Generation** produces a complete `report_spec` JSON with sections, charts, and narratives
4. **Preview Rendering** displays the spec as interactive, paginated content in the browser
5. **NL Editing** lets the COO refine the report through conversation — each edit modifies the spec
6. **PDF Export** renders the spec to HTML (Jinja2), converts charts to SVG (pyecharts), and produces a professional PDF (WeasyPrint)

The `report_spec` is the single source of truth. It flows unchanged between generation, preview, editing, storage, and export. No separate "preview format" or "export format" — one spec, rendered differently for each context.
