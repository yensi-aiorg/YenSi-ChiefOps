# Widget Types & Components: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

**Companion document to [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md).** This document covers the implementation details: every widget type with its ECharts configuration, the backend data query engine that translates widget specs into MongoDB aggregation pipelines, the React component architecture, and the Zustand state management layer.

**Tech stack:** React 19, TypeScript (strict), Tailwind CSS, Zustand, Apache ECharts via `echarts-for-react`. Backend: Python 3.11+, FastAPI, MongoDB (Motor async), Redis for caching.

---

## 1. Widget Types Reference

Every widget is a JSON document in the `dashboard_widgets` MongoDB collection. The `widget_type` field determines which React component renders it. The `data_query` field tells the backend what data to fetch. The `chart_spec` field contains the ECharts option object (for chart types) or structured display data (for non-chart types).

See [Data Models, Section 11](./03-DATA-MODELS.md) for the full `DashboardWidget` Pydantic model and the `WidgetType` enum.

---

### 1.1 `bar_chart` — Bar Chart

**Description:** Standard and stacked bar charts for categorical comparisons. Supports vertical (default) and horizontal orientation. Stacking is activated when `data_query.split_by` is provided.

**Required `data_query` fields:**
- `source` — collection to query (e.g., `"tasks"`, `"people"`)
- `group_by` — categorical field for the x-axis (e.g., `"assignees"`, `"project_id"`)
- `metric` — aggregation to compute (e.g., `"count"`, `"sum:story_points"`)
- `split_by` (optional) — secondary grouping for stacked series (e.g., `"status"`)
- `filters` (optional) — key-value filter pairs (e.g., `{"project_id": "proj_abc"}`)

**ECharts option template:**

```json
{
  "tooltip": { "trigger": "axis", "axisPointer": { "type": "shadow" } },
  "legend": { "top": "2%" },
  "grid": { "left": "3%", "right": "4%", "bottom": "3%", "containLabel": true },
  "xAxis": { "type": "category", "data": ["Alice", "Bob", "Carol", "Dave"] },
  "yAxis": { "type": "value", "name": "Tasks" },
  "series": [
    { "name": "To Do", "type": "bar", "stack": "total", "data": [3, 5, 2, 7] },
    { "name": "In Progress", "type": "bar", "stack": "total", "data": [2, 1, 4, 1] },
    { "name": "Done", "type": "bar", "stack": "total", "data": [8, 6, 5, 3] }
  ]
}
```

**Example use cases:**
- Tasks per assignee stacked by status
- Story points completed per sprint
- Messages per channel (top 10)

---

### 1.2 `line_chart` — Line Chart

**Description:** Trends over time. Used for velocity tracking, burndown charts, activity trends, and any metric that has a temporal x-axis. Supports multiple series for comparisons.

**Required `data_query` fields:**
- `source` — collection to query
- `group_by` — typically a date field bucketed by day/week/sprint (e.g., `"created_date"`)
- `metric` — aggregation (e.g., `"count"`, `"sum:story_points"`)
- `time_range` — `{ "start": "2025-01-01", "end": "2025-03-31", "field": "created_date" }`
- `split_by` (optional) — for multi-line comparisons (e.g., by project)

**ECharts option template:**

```json
{
  "tooltip": { "trigger": "axis" },
  "legend": { "top": "2%" },
  "grid": { "left": "3%", "right": "4%", "bottom": "3%", "containLabel": true },
  "xAxis": { "type": "category", "data": ["Sprint 1", "Sprint 2", "Sprint 3", "Sprint 4", "Sprint 5"] },
  "yAxis": { "type": "value", "name": "Story Points" },
  "series": [
    {
      "name": "Completed",
      "type": "line",
      "smooth": true,
      "data": [21, 34, 28, 42, 38],
      "areaStyle": { "opacity": 0.1 }
    },
    {
      "name": "Committed",
      "type": "line",
      "smooth": true,
      "data": [30, 35, 35, 40, 45],
      "lineStyle": { "type": "dashed" }
    }
  ]
}
```

**Example use cases:**
- Sprint velocity over time (committed vs. completed)
- Burndown chart for current sprint
- Daily Slack message volume trend
- Team activity level over weeks

---

### 1.3 `pie_chart` — Pie / Donut Chart

**Description:** Distribution breakdowns. Renders as a donut by default (inner radius set). Best for showing proportional composition of a categorical field.

**Required `data_query` fields:**
- `source` — collection to query
- `group_by` — categorical field for slices (e.g., `"status"`, `"role"`)
- `metric` — aggregation (typically `"count"`)
- `filters` (optional)

**ECharts option template:**

```json
{
  "tooltip": { "trigger": "item", "formatter": "{b}: {c} ({d}%)" },
  "legend": { "orient": "vertical", "right": "5%", "top": "center" },
  "series": [
    {
      "type": "pie",
      "radius": ["40%", "70%"],
      "center": ["40%", "50%"],
      "avoidLabelOverlap": true,
      "itemStyle": { "borderRadius": 6, "borderColor": "#fff", "borderWidth": 2 },
      "label": { "show": true, "formatter": "{b}\n{d}%" },
      "data": [
        { "value": 12, "name": "To Do" },
        { "value": 8, "name": "In Progress" },
        { "value": 23, "name": "Done" },
        { "value": 3, "name": "Blocked" }
      ]
    }
  ]
}
```

**Example use cases:**
- Tasks by status for a project
- People by role distribution
- Messages by channel type (public/private/DM)

---

### 1.4 `gantt` — Gantt / Timeline Chart

**Description:** Project timelines, milestones, and task schedules. Implemented using ECharts custom series with `renderItem`. Each bar represents a task or milestone with start/end dates. Color-coded by status.

**Required `data_query` fields:**
- `source` — typically `"tasks"` or `"projects"`
- `filters` — at minimum `{"project_id": "..."}` to scope
- `metric` — `"timeline"` (special mode: returns start/end/status per item)
- `time_range` (optional) — to bound the visible window

**ECharts option template:**

```json
{
  "tooltip": { "formatter": "{b}: {c0} to {c1}" },
  "grid": { "left": "15%", "right": "5%", "top": "5%", "bottom": "10%" },
  "xAxis": {
    "type": "time",
    "min": "2025-01-01",
    "max": "2025-06-30",
    "axisLabel": { "formatter": "{MMM} {d}" }
  },
  "yAxis": {
    "type": "category",
    "data": ["Auth Module", "API Gateway", "Dashboard UI", "Testing", "Launch"],
    "inverse": true
  },
  "series": [
    {
      "type": "custom",
      "renderItem": "FUNCTION_REF:ganttBarRenderer",
      "encode": { "x": [1, 2], "y": 0 },
      "data": [
        ["Auth Module", "2025-01-15", "2025-02-28", "done"],
        ["API Gateway", "2025-02-01", "2025-03-15", "in_progress"],
        ["Dashboard UI", "2025-03-01", "2025-04-30", "in_progress"],
        ["Testing", "2025-04-15", "2025-05-31", "todo"],
        ["Launch", "2025-06-01", "2025-06-15", "todo"]
      ]
    }
  ]
}
```

> **Note:** The `renderItem` function reference (`FUNCTION_REF:ganttBarRenderer`) is resolved client-side by the `GanttWidget` component, which injects the actual JavaScript render function. The chart_spec stores a string key, not executable code.

**Example use cases:**
- Project timeline with task phases
- Sprint milestones and deadlines
- Cross-project timeline comparison

---

### 1.5 `table` — Data Table

**Description:** Tabular data with headers, typed rows, and client-side sorting. Not an ECharts widget — rendered as a custom React table component with Tailwind styling. Supports pagination for large datasets.

**Required `data_query` fields:**
- `source` — collection to query
- `group_by` (optional) — if aggregating
- `metric` — `"table"` (special mode: returns raw or aggregated rows)
- `filters` (optional)

**`chart_spec` structure (not ECharts — custom format):**

```json
{
  "columns": [
    { "key": "name", "label": "Name", "sortable": true },
    { "key": "role", "label": "Role", "sortable": true },
    { "key": "tasks_assigned", "label": "Assigned", "sortable": true, "align": "right" },
    { "key": "tasks_completed", "label": "Completed", "sortable": true, "align": "right" },
    { "key": "activity_level", "label": "Activity", "sortable": true }
  ],
  "rows": [
    { "name": "Alice Chen", "role": "Engineer", "tasks_assigned": 12, "tasks_completed": 8, "activity_level": "very_active" },
    { "name": "Bob Kim", "role": "Designer", "tasks_assigned": 7, "tasks_completed": 5, "activity_level": "active" }
  ],
  "page_size": 10,
  "total_rows": 24
}
```

**Example use cases:**
- Team roster with task metrics
- Sprint backlog with status and assignees
- Overdue tasks list

---

### 1.6 `kpi_card` — KPI Card

**Description:** Single headline metric with optional trend indicator, comparison value, and sparkline. Designed for the top of dashboards — glanceable, color-coded by health.

**Required `data_query` fields:**
- `source` — collection to query
- `metric` — the calculation (e.g., `"count"`, `"avg:story_points"`, `"health_score"`)
- `filters` (optional)
- `time_range` (optional) — for trend comparison

**`chart_spec` structure (custom format, not full ECharts):**

```json
{
  "value": 73,
  "unit": "%",
  "label": "Sprint Completion",
  "trend": {
    "direction": "up",
    "delta": 8,
    "delta_label": "vs last sprint"
  },
  "color": "success",
  "sparkline_data": [45, 52, 60, 58, 65, 73]
}
```

The `color` field maps to theme tokens: `"success"` (green), `"warning"` (amber), `"danger"` (red), `"neutral"` (gray), `"info"` (blue).

**Example use cases:**
- Project health score
- Sprint completion percentage
- Active team members count
- Open blockers count (danger-colored when > 0)

---

### 1.7 `summary_text` — AI Summary Block

**Description:** AI-generated text summary rendered as a styled card. Used for briefings, risk assessments, and contextual analysis. The content is generated by the AI layer and stored as markdown in the chart_spec.

**Required `data_query` fields:**
- `source` — `"ai_generated"` (special source indicating the content comes from AI processing)
- `metric` — `"summary"` (indicates text generation, not numeric aggregation)
- `filters` — context for the AI (e.g., `{"project_id": "...", "summary_type": "daily_briefing"}`)

**`chart_spec` structure:**

```json
{
  "content": "## Project Alpha — Daily Briefing\n\n**Velocity** is trending up at 34 points/sprint, a 12% improvement over the 3-sprint average.\n\n**Risk:** The Auth Module has 2 open blockers assigned to Bob, who has been marked as `quiet` activity for 3 days.\n\n**Action needed:** Follow up with Bob on AUTH-142 and AUTH-155.",
  "generated_at": "2025-03-15T09:00:00Z",
  "model": "claude-sonnet",
  "confidence": 0.92
}
```

**Example use cases:**
- Daily project briefing
- Weekly team summary
- Risk assessment narrative
- Post-ingestion delta report

---

### 1.8 `person_grid` — Team Member Cards

**Description:** Grid of team member cards showing avatar, name, role, and key metrics. Each card is clickable to open the person detail view. Not an ECharts widget.

**Required `data_query` fields:**
- `source` — `"people"`
- `metric` — `"person_cards"` (returns person records with metrics)
- `filters` (optional) — e.g., `{"project_id": "..."}` to scope to a project team

**`chart_spec` structure:**

```json
{
  "people": [
    {
      "person_id": "p_abc123",
      "name": "Alice Chen",
      "role": "Senior Engineer",
      "avatar_url": "https://slack-avatars.example.com/alice.jpg",
      "activity_level": "very_active",
      "tasks_assigned": 12,
      "tasks_completed": 8,
      "last_active": "2025-03-15T14:22:00Z"
    },
    {
      "person_id": "p_def456",
      "name": "Bob Kim",
      "role": "Product Designer",
      "avatar_url": null,
      "activity_level": "quiet",
      "tasks_assigned": 7,
      "tasks_completed": 5,
      "last_active": "2025-03-12T10:15:00Z"
    }
  ],
  "layout": "grid",
  "columns": 3
}
```

**Example use cases:**
- Project team overview
- People flagged as `quiet` or `inactive`
- Top contributors grid

---

### 1.9 `timeline` — Event Timeline

**Description:** Chronological vertical timeline of events. Each node shows a timestamp, description, and category badge. Not an ECharts widget — custom React component.

**Required `data_query` fields:**
- `source` — `"messages"`, `"tasks"`, or `"multi"` (merged from multiple collections)
- `metric` — `"timeline_events"` (returns ordered event list)
- `filters` — scope filters (project, person, date range)
- `time_range` — bounding window

**`chart_spec` structure:**

```json
{
  "events": [
    {
      "timestamp": "2025-03-15T14:30:00Z",
      "type": "task_completed",
      "title": "AUTH-142 marked Done",
      "description": "Alice completed the OAuth integration task",
      "person_id": "p_abc123",
      "badge_color": "success"
    },
    {
      "timestamp": "2025-03-15T11:00:00Z",
      "type": "blocker_raised",
      "title": "API-089 blocked by AUTH-155",
      "description": "Dave flagged a dependency blocker on the Gateway API",
      "person_id": "p_ghi789",
      "badge_color": "danger"
    },
    {
      "timestamp": "2025-03-15T09:15:00Z",
      "type": "message_notable",
      "title": "Sprint planning discussion",
      "description": "Carol raised scope concerns in #project-alpha",
      "person_id": "p_jkl012",
      "badge_color": "warning"
    }
  ],
  "max_events": 50
}
```

**Example use cases:**
- Project activity timeline for the past week
- Person-scoped event history
- Risk event timeline (blockers, missed deadlines)

---

### 1.10 `activity_feed` — Activity Feed

**Description:** Scrollable, real-time-updated list of recent events across the organization or scoped to a project. Similar to timeline but optimized for a compact, live-updating sidebar or card. Receives WebSocket updates for new events.

**Required `data_query` fields:**
- `source` — `"multi"` (aggregates from tasks, messages, ingestion_jobs)
- `metric` — `"activity_stream"` (returns most recent events, ordered desc)
- `filters` (optional) — project scope, person scope
- `time_range` (optional) — defaults to last 24 hours

**`chart_spec` structure:**

```json
{
  "items": [
    {
      "id": "evt_001",
      "timestamp": "2025-03-15T14:32:00Z",
      "actor": { "person_id": "p_abc123", "name": "Alice", "avatar_url": "..." },
      "action": "completed",
      "target": "AUTH-142: OAuth Integration",
      "project": "Project Alpha",
      "icon": "check_circle"
    },
    {
      "id": "evt_002",
      "timestamp": "2025-03-15T14:28:00Z",
      "actor": { "person_id": "p_def456", "name": "Bob", "avatar_url": null },
      "action": "commented on",
      "target": "#project-alpha",
      "project": "Project Alpha",
      "icon": "chat_bubble"
    }
  ],
  "has_more": true,
  "next_cursor": "evt_003"
}
```

**Example use cases:**
- Main dashboard "Recent Activity" card
- Project-scoped activity stream
- Real-time ingestion event feed

---

## 2. Data Query Engine

The Data Query Engine is a backend service that translates `DataQuery` JSON specs (stored in each widget document) into MongoDB aggregation pipelines, executes them, and returns structured data that can be directly mapped into ECharts option objects or custom component props.

### 2.1 Architecture Overview

```
Widget Spec (MongoDB)                 Frontend
    │                                     ▲
    │ data_query                          │ chart_spec (populated)
    ▼                                     │
┌─────────────────────────────────────────────────────────┐
│                   Data Query Engine                       │
│                                                           │
│  1. Parse DataQuery JSON                                  │
│  2. Build MongoDB aggregation pipeline                    │
│  3. Execute pipeline via Motor                            │
│  4. Transform results → structured output                 │
│  5. Map to ECharts data arrays (for chart types)          │
│  6. Cache result in Redis (keyed by query hash)           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Supported Operations

| Operation | `DataQuery` Field | Description |
|-----------|------------------|-------------|
| Source selection | `source` | Target collection: `tasks`, `people`, `messages`, `projects` |
| Grouping | `group_by` | Field to `$group` by. Supports dot-notation (e.g., `"assignees"`) |
| Metric calculation | `metric` | `"count"`, `"sum:<field>"`, `"avg:<field>"`, `"min:<field>"`, `"max:<field>"` |
| Secondary split | `split_by` | Creates sub-groups within each group (for stacked/multi-series charts) |
| Filtering | `filters` | Key-value pairs translated to `$match` stages |
| Date range | `time_range` | `{start, end, field}` translated to `$match` with `$gte`/`$lte` on the date field |
| Special modes | `metric` values | `"timeline"`, `"table"`, `"person_cards"`, `"activity_stream"`, `"summary"` trigger specialized pipelines |

### 2.3 Concrete Example: End-to-End

**COO request:** "Show me tasks per assignee grouped by status for Project Alpha."

**Step 1 — DataQuery spec (stored in widget document):**

```json
{
  "source": "tasks",
  "group_by": "assignees",
  "metric": "count",
  "split_by": "status",
  "filters": { "project_id": "proj_alpha_001" }
}
```

**Step 2 — Generated MongoDB aggregation pipeline:**

```python
pipeline = [
    # Stage 1: Filter to project
    {"$match": {"project_id": "proj_alpha_001"}},

    # Stage 2: Unwind array fields used in group_by
    {"$unwind": "$assignees"},

    # Stage 3: Resolve person names via lookup
    {"$lookup": {
        "from": "people",
        "localField": "assignees",
        "foreignField": "person_id",
        "as": "_person"
    }},
    {"$unwind": "$_person"},

    # Stage 4: Group by assignee + status, count
    {"$group": {
        "_id": {
            "group": "$_person.name",
            "split": "$status"
        },
        "value": {"$sum": 1}
    }},

    # Stage 5: Reshape for output
    {"$project": {
        "_id": 0,
        "group": "$_id.group",
        "split": "$_id.split",
        "value": 1
    }},

    # Stage 6: Sort for consistent output
    {"$sort": {"group": 1, "split": 1}}
]
```

**Step 3 — Raw pipeline output:**

```json
[
  { "group": "Alice Chen", "split": "Done", "value": 8 },
  { "group": "Alice Chen", "split": "In Progress", "value": 2 },
  { "group": "Alice Chen", "split": "To Do", "value": 3 },
  { "group": "Bob Kim", "split": "Done", "value": 5 },
  { "group": "Bob Kim", "split": "In Progress", "value": 1 },
  { "group": "Bob Kim", "split": "To Do", "value": 4 }
]
```

**Step 4 — Transformed to ECharts data mapping:**

```json
{
  "categories": ["Alice Chen", "Bob Kim"],
  "series": [
    { "name": "Done", "data": [8, 5] },
    { "name": "In Progress", "data": [2, 1] },
    { "name": "To Do", "data": [3, 4] }
  ]
}
```

This structured output is merged into the ECharts option template from Section 1.1.

### 2.4 Python Service Implementation

```python
from typing import Any, Optional
from datetime import datetime
import hashlib
import json

from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.models.widgets import DataQuery, WidgetType


class DataQueryEngine:
    """
    Translates DataQuery specs into MongoDB aggregation pipelines,
    executes them, and returns structured data for widget rendering.
    """

    # Fields that are arrays and need $unwind before grouping
    ARRAY_FIELDS = {"assignees", "labels", "projects", "mentions", "topics"}

    # Lookup mappings for resolving IDs to display names
    LOOKUPS = {
        "assignees": {"from": "people", "local": "assignees", "foreign": "person_id", "field": "name"},
        "project_id": {"from": "projects", "local": "project_id", "foreign": "project_id", "field": "name"},
        "author": {"from": "people", "local": "author", "foreign": "person_id", "field": "name"},
    }

    def __init__(self, db: AsyncIOMotorDatabase, redis: Redis):
        self.db = db
        self.redis = redis
        self.cache_ttl = 300  # 5 minutes default; invalidated on re-ingestion

    async def execute(self, data_query: DataQuery, widget_type: WidgetType) -> dict[str, Any]:
        """
        Main entry point. Executes a data query and returns structured
        results ready for chart_spec population.
        """
        cache_key = self._cache_key(data_query)
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Route to specialized handlers for non-standard metrics
        if data_query.metric in ("timeline", "table", "person_cards", "activity_stream", "summary"):
            result = await self._execute_special(data_query, widget_type)
        else:
            result = await self._execute_aggregation(data_query)

        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(result, default=str))
        return result

    async def _execute_aggregation(self, query: DataQuery) -> dict[str, Any]:
        """Builds and runs a standard group-by aggregation pipeline."""
        pipeline = self._build_pipeline(query)
        collection = self.db[query.source]
        cursor = collection.aggregate(pipeline)
        raw_results = await cursor.to_list(length=None)
        return self._transform_results(raw_results, has_split=query.split_by is not None)

    def _build_pipeline(self, query: DataQuery) -> list[dict]:
        """Constructs the MongoDB aggregation pipeline from a DataQuery."""
        stages: list[dict] = []

        # $match: filters
        match_stage = {}
        if query.filters:
            match_stage.update(query.filters)
        if query.time_range:
            field = query.time_range.get("field", "created_date")
            match_stage[field] = {}
            if "start" in query.time_range:
                match_stage[field]["$gte"] = query.time_range["start"]
            if "end" in query.time_range:
                match_stage[field]["$lte"] = query.time_range["end"]
        if match_stage:
            stages.append({"$match": match_stage})

        # $unwind: array fields
        if query.group_by and query.group_by in self.ARRAY_FIELDS:
            stages.append({"$unwind": f"${query.group_by}"})

        # $lookup: resolve IDs to names
        if query.group_by and query.group_by in self.LOOKUPS:
            lookup_cfg = self.LOOKUPS[query.group_by]
            stages.append({"$lookup": {
                "from": lookup_cfg["from"],
                "localField": lookup_cfg["local"],
                "foreignField": lookup_cfg["foreign"],
                "as": "_resolved"
            }})
            stages.append({"$unwind": {"path": "$_resolved", "preserveNullAndEmptyArrays": True}})

        # $group: build group key and metric accumulator
        group_id = self._build_group_id(query)
        metric_acc = self._build_metric_accumulator(query.metric)
        stages.append({"$group": {"_id": group_id, "value": metric_acc}})

        # $project: flatten output
        project = {"_id": 0, "value": 1, "group": "$_id.group"}
        if query.split_by:
            project["split"] = "$_id.split"
        stages.append({"$project": project})

        stages.append({"$sort": {"group": 1}})
        return stages

    def _build_group_id(self, query: DataQuery) -> dict:
        """Constructs the $group _id expression."""
        group_field = query.group_by or "_all"
        if query.group_by and query.group_by in self.LOOKUPS:
            group_expr = f"$_resolved.{self.LOOKUPS[query.group_by]['field']}"
        else:
            group_expr = f"${group_field}" if group_field != "_all" else None

        group_id: dict = {"group": group_expr}
        if query.split_by:
            group_id["split"] = f"${query.split_by}"
        return group_id

    @staticmethod
    def _build_metric_accumulator(metric: str) -> dict:
        """Parses metric string into a MongoDB accumulator."""
        if metric == "count":
            return {"$sum": 1}
        elif ":" in metric:
            op, field = metric.split(":", 1)
            mongo_op = {"sum": "$sum", "avg": "$avg", "min": "$min", "max": "$max"}[op]
            return {mongo_op: f"${field}"}
        return {"$sum": 1}

    @staticmethod
    def _transform_results(raw: list[dict], has_split: bool) -> dict[str, Any]:
        """Transforms pipeline output into ECharts-ready structure."""
        if not has_split:
            return {
                "categories": [r["group"] for r in raw],
                "values": [r["value"] for r in raw],
            }

        # Pivot split results into multi-series format
        categories: list[str] = []
        series_map: dict[str, dict[str, float]] = {}
        for r in raw:
            if r["group"] not in categories:
                categories.append(r["group"])
            split_name = r.get("split", "default")
            if split_name not in series_map:
                series_map[split_name] = {}
            series_map[split_name][r["group"]] = r["value"]

        series = []
        for name, values in series_map.items():
            series.append({
                "name": name,
                "data": [values.get(c, 0) for c in categories],
            })

        return {"categories": categories, "series": series}

    async def _execute_special(self, query: DataQuery, widget_type: WidgetType) -> dict[str, Any]:
        """Routes special metric types to dedicated handlers."""
        handlers = {
            "timeline": self._query_timeline,
            "table": self._query_table,
            "person_cards": self._query_person_cards,
            "activity_stream": self._query_activity_stream,
        }
        handler = handlers.get(query.metric)
        if handler:
            return await handler(query)
        return {}

    async def _query_timeline(self, query: DataQuery) -> dict[str, Any]:
        """Fetches tasks with start/end dates for Gantt rendering."""
        match = query.filters.copy() if query.filters else {}
        cursor = self.db[query.source].find(match).sort("created_date", 1)
        docs = await cursor.to_list(length=200)
        return {
            "items": [
                {
                    "name": d.get("summary", ""),
                    "start": d.get("created_date"),
                    "end": d.get("due_date") or d.get("updated_date"),
                    "status": d.get("status", ""),
                }
                for d in docs
            ]
        }

    async def _query_table(self, query: DataQuery) -> dict[str, Any]:
        """Fetches raw documents for table rendering."""
        match = query.filters.copy() if query.filters else {}
        cursor = self.db[query.source].find(match, {"_id": 0}).limit(100)
        return {"rows": await cursor.to_list(length=100)}

    async def _query_person_cards(self, query: DataQuery) -> dict[str, Any]:
        """Fetches people with metrics for person_grid rendering."""
        match = query.filters.copy() if query.filters else {}
        cursor = self.db["people"].find(match, {"_id": 0}).sort("activity_level", -1)
        return {"people": await cursor.to_list(length=50)}

    async def _query_activity_stream(self, query: DataQuery) -> dict[str, Any]:
        """Aggregates recent events from multiple collections."""
        # Simplified: queries tasks and messages, merges, sorts by timestamp
        match = query.filters.copy() if query.filters else {}
        tasks = await self.db["tasks"].find(match).sort("updated_date", -1).to_list(25)
        messages = await self.db["messages"].find(match).sort("timestamp", -1).to_list(25)
        events = []
        for t in tasks:
            events.append({"timestamp": t["updated_date"], "type": "task", "title": t.get("summary", "")})
        for m in messages:
            events.append({"timestamp": m["timestamp"], "type": "message", "title": m.get("text", "")[:100]})
        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return {"items": events[:30]}

    def _cache_key(self, query: DataQuery) -> str:
        """Generates a deterministic cache key from the query spec."""
        payload = json.dumps(query.model_dump(), sort_keys=True, default=str)
        return f"widget_data:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"

    async def invalidate_cache(self) -> int:
        """Called after data re-ingestion. Clears all widget data caches."""
        keys = []
        async for key in self.redis.scan_iter(match="widget_data:*"):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)
        return len(keys)
```

### 2.5 Caching Strategy

| Aspect | Behavior |
|--------|----------|
| Cache backend | Redis (port 23003) |
| Cache key | SHA-256 hash of serialized `DataQuery` JSON |
| Default TTL | 300 seconds (5 minutes) |
| Invalidation trigger | After any data ingestion completes, `invalidate_cache()` is called to clear all `widget_data:*` keys |
| Scope | Per-query — two widgets with identical data_queries share the same cache entry |
| Bypass | The frontend can pass `?refresh=true` to force a cache miss |

---

## 3. React Component Architecture

### 3.1 Component Tree

```
App
└── DashboardPage                    ← route: /dashboard/:type/:id?
    ├── DashboardHeader              ← title, search bar, breadcrumbs
    ├── WidgetGrid                   ← CSS Grid container (12-col layout)
    │   ├── WidgetRenderer           ← maps widget_type → component
    │   │   ├── BarChartWidget       ← echarts-for-react
    │   │   ├── LineChartWidget      ← echarts-for-react
    │   │   ├── PieChartWidget       ← echarts-for-react
    │   │   ├── GanttWidget          ← echarts-for-react (custom series)
    │   │   ├── TableWidget          ← custom table
    │   │   ├── KpiCardWidget        ← custom card
    │   │   ├── SummaryTextWidget    ← markdown renderer
    │   │   ├── PersonGridWidget     ← person card grid
    │   │   ├── TimelineWidget       ← vertical timeline
    │   │   └── ActivityFeedWidget   ← scrollable feed
    │   └── ... (repeated per widget)
    └── WidgetErrorBoundary          ← catches per-widget render errors
```

### 3.2 TypeScript Interfaces

These interfaces are the contract between the API response and the React rendering layer. They mirror the Pydantic models from [Data Models, Section 11](./03-DATA-MODELS.md).

```typescript
// src/types/widgets.ts

export type WidgetType =
  | "bar_chart"
  | "line_chart"
  | "pie_chart"
  | "gantt"
  | "table"
  | "kpi_card"
  | "summary_text"
  | "person_grid"
  | "timeline"
  | "activity_feed";

export type WidgetCreator = "coo_conversation" | "system_default";

export interface DataQuery {
  source: string;
  group_by?: string;
  metric: string;
  split_by?: string;
  filters?: Record<string, unknown>;
  time_range?: {
    start?: string;
    end?: string;
    field: string;
  };
}

export interface WidgetPosition {
  row: number;
  col: number;
  width: number;   // 1-12 grid columns
  height: number;  // 1-8 grid rows
}

export interface ChartSpec {
  /** For ECharts widgets: the full ECharts option object */
  [key: string]: unknown;
}

export interface WidgetSpec {
  widget_id: string;
  dashboard_id: string;
  widget_type: WidgetType;
  title: string;
  data_query: DataQuery;
  chart_spec: ChartSpec;
  position: WidgetPosition;
  created_by: WidgetCreator;
  conversation_turn_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Dashboard {
  dashboard_id: string;
  name: string;
  type: "main" | "project" | "custom";
  project_id?: string;
  widgets: WidgetSpec[];
}
```

### 3.3 WidgetRenderer Component

The central dispatch component. Receives a `WidgetSpec` and renders the appropriate widget component. Each widget is wrapped in a card container with a title bar, loading state, and error boundary.

```tsx
// src/components/widgets/WidgetRenderer.tsx

import React, { Suspense } from "react";
import type { WidgetSpec, WidgetType } from "@/types/widgets";

// Lazy-load widget components for code splitting
const BarChartWidget = React.lazy(() => import("./BarChartWidget"));
const LineChartWidget = React.lazy(() => import("./LineChartWidget"));
const PieChartWidget = React.lazy(() => import("./PieChartWidget"));
const GanttWidget = React.lazy(() => import("./GanttWidget"));
const TableWidget = React.lazy(() => import("./TableWidget"));
const KpiCardWidget = React.lazy(() => import("./KpiCardWidget"));
const SummaryTextWidget = React.lazy(() => import("./SummaryTextWidget"));
const PersonGridWidget = React.lazy(() => import("./PersonGridWidget"));
const TimelineWidget = React.lazy(() => import("./TimelineWidget"));
const ActivityFeedWidget = React.lazy(() => import("./ActivityFeedWidget"));

const WIDGET_COMPONENTS: Record<WidgetType, React.LazyExoticComponent<React.ComponentType<WidgetComponentProps>>> = {
  bar_chart: BarChartWidget,
  line_chart: LineChartWidget,
  pie_chart: PieChartWidget,
  gantt: GanttWidget,
  table: TableWidget,
  kpi_card: KpiCardWidget,
  summary_text: SummaryTextWidget,
  person_grid: PersonGridWidget,
  timeline: TimelineWidget,
  activity_feed: ActivityFeedWidget,
};

export interface WidgetComponentProps {
  spec: WidgetSpec;
  isLoading: boolean;
}

interface WidgetRendererProps {
  spec: WidgetSpec;
  isLoading?: boolean;
}

export default function WidgetRenderer({ spec, isLoading = false }: WidgetRendererProps) {
  const Component = WIDGET_COMPONENTS[spec.widget_type];

  if (!Component) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-600">Unknown widget type: {spec.widget_type}</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl bg-white shadow-card border border-gray-100 overflow-hidden flex flex-col"
      style={{
        gridColumn: `${spec.position.col + 1} / span ${spec.position.width}`,
        gridRow: `${spec.position.row + 1} / span ${spec.position.height}`,
      }}
    >
      {/* Widget title bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-50">
        <h3 className="text-sm font-semibold text-gray-800 truncate">{spec.title}</h3>
        <WidgetMenu widgetId={spec.widget_id} />
      </div>

      {/* Widget body */}
      <div className="flex-1 p-4 min-h-0">
        <Suspense fallback={<WidgetSkeleton />}>
          <Component spec={spec} isLoading={isLoading} />
        </Suspense>
      </div>
    </div>
  );
}

function WidgetSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 bg-gray-100 rounded w-3/4" />
      <div className="h-32 bg-gray-50 rounded" />
    </div>
  );
}

function WidgetMenu({ widgetId }: { widgetId: string }) {
  // Dropdown menu for widget actions: refresh, edit, remove
  return (
    <button
      className="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-50"
      aria-label="Widget options"
    >
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
      </svg>
    </button>
  );
}
```

### 3.4 WidgetGrid Component

Renders all widgets for a dashboard using CSS Grid. Handles the 12-column layout system.

```tsx
// src/components/widgets/WidgetGrid.tsx

import { useDashboardStore } from "@/stores/dashboardStore";
import { useWidgetDataStore } from "@/stores/widgetDataStore";
import WidgetRenderer from "./WidgetRenderer";
import WidgetErrorBoundary from "./WidgetErrorBoundary";

export default function WidgetGrid() {
  const widgets = useDashboardStore((s) => s.widgets);
  const loadingWidgets = useWidgetDataStore((s) => s.loadingWidgets);

  if (widgets.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-lg">No widgets yet.</p>
        <p className="text-sm mt-1">Ask ChiefOps to create one — e.g., "Show me tasks per person for this project."</p>
      </div>
    );
  }

  return (
    <div
      className="grid gap-4"
      style={{
        gridTemplateColumns: "repeat(12, 1fr)",
        gridAutoRows: "minmax(80px, auto)",
      }}
    >
      {widgets.map((widget) => (
        <WidgetErrorBoundary key={widget.widget_id} widgetId={widget.widget_id}>
          <WidgetRenderer
            spec={widget}
            isLoading={loadingWidgets.has(widget.widget_id)}
          />
        </WidgetErrorBoundary>
      ))}
    </div>
  );
}
```

### 3.5 ECharts Widget Example

All ECharts-based widgets follow the same pattern. Here is the `BarChartWidget` as a representative example:

```tsx
// src/components/widgets/BarChartWidget.tsx

import ReactECharts from "echarts-for-react";
import type { WidgetComponentProps } from "./WidgetRenderer";

const THEME_COLORS = ["#1E3A5F", "#00BCD4", "#4CAF50", "#FF9800", "#F44336", "#9C27B0"];

export default function BarChartWidget({ spec, isLoading }: WidgetComponentProps) {
  if (isLoading) return <ChartSkeleton />;

  const chartSpec = spec.chart_spec;

  // Apply theme colors if not already set
  const option = {
    ...chartSpec,
    color: chartSpec.color || THEME_COLORS,
    tooltip: chartSpec.tooltip || { trigger: "axis", axisPointer: { type: "shadow" } },
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: "100%", width: "100%" }}
      opts={{ renderer: "svg" }}
      notMerge={true}
    />
  );
}

function ChartSkeleton() {
  return <div className="w-full h-full bg-gray-50 rounded animate-pulse" />;
}
```

---

## 4. State Management (Zustand)

Three Zustand stores manage the dashboard, widget CRUD, and cached query data.

### 4.1 Dashboard Store

Manages which dashboard is active and its widget list.

```typescript
// src/stores/dashboardStore.ts

import { create } from "zustand";
import type { Dashboard, WidgetSpec } from "@/types/widgets";
import { apiClient } from "@/lib/api";

interface DashboardState {
  // State
  currentDashboard: Dashboard | null;
  widgets: WidgetSpec[];
  isLoading: boolean;
  error: string | null;

  // Actions
  loadDashboard: (dashboardId: string) => Promise<void>;
  loadProjectDashboard: (projectId: string) => Promise<void>;
  addWidget: (widget: WidgetSpec) => void;
  removeWidget: (widgetId: string) => void;
  updateWidgetPosition: (widgetId: string, position: WidgetSpec["position"]) => void;
  clearDashboard: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  currentDashboard: null,
  widgets: [],
  isLoading: false,
  error: null,

  loadDashboard: async (dashboardId: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiClient.get<Dashboard>(`/api/v1/dashboards/${dashboardId}`);
      set({
        currentDashboard: res.data,
        widgets: res.data.widgets,
        isLoading: false,
      });
    } catch (err) {
      set({ error: "Failed to load dashboard", isLoading: false });
    }
  },

  loadProjectDashboard: async (projectId: string) => {
    await get().loadDashboard(`${projectId}_custom`);
  },

  addWidget: (widget) => {
    set((s) => ({ widgets: [...s.widgets, widget] }));
  },

  removeWidget: (widgetId) => {
    set((s) => ({ widgets: s.widgets.filter((w) => w.widget_id !== widgetId) }));
  },

  updateWidgetPosition: (widgetId, position) => {
    set((s) => ({
      widgets: s.widgets.map((w) =>
        w.widget_id === widgetId ? { ...w, position } : w
      ),
    }));
  },

  clearDashboard: () => {
    set({ currentDashboard: null, widgets: [], error: null });
  },
}));
```

### 4.2 Widget CRUD Store

Handles widget creation, updates, and deletion via the API.

```typescript
// src/stores/widgetStore.ts

import { create } from "zustand";
import type { WidgetSpec, DataQuery } from "@/types/widgets";
import { apiClient } from "@/lib/api";
import { useDashboardStore } from "./dashboardStore";

interface WidgetCrudState {
  // State
  isSaving: boolean;
  savingWidgetId: string | null;
  error: string | null;

  // Actions
  createWidget: (dashboardId: string, spec: Partial<WidgetSpec>) => Promise<WidgetSpec | null>;
  updateWidget: (widgetId: string, updates: Partial<WidgetSpec>) => Promise<void>;
  deleteWidget: (widgetId: string) => Promise<void>;
  refreshWidgetData: (widgetId: string) => Promise<void>;
}

export const useWidgetStore = create<WidgetCrudState>((set) => ({
  isSaving: false,
  savingWidgetId: null,
  error: null,

  createWidget: async (dashboardId, spec) => {
    set({ isSaving: true, error: null });
    try {
      const res = await apiClient.post<WidgetSpec>(`/api/v1/widgets`, {
        dashboard_id: dashboardId,
        ...spec,
      });
      useDashboardStore.getState().addWidget(res.data);
      set({ isSaving: false });
      return res.data;
    } catch (err) {
      set({ error: "Failed to create widget", isSaving: false });
      return null;
    }
  },

  updateWidget: async (widgetId, updates) => {
    set({ isSaving: true, savingWidgetId: widgetId, error: null });
    try {
      await apiClient.patch(`/api/v1/widgets/${widgetId}`, updates);
      set({ isSaving: false, savingWidgetId: null });
    } catch (err) {
      set({ error: "Failed to update widget", isSaving: false, savingWidgetId: null });
    }
  },

  deleteWidget: async (widgetId) => {
    set({ isSaving: true, savingWidgetId: widgetId, error: null });
    try {
      await apiClient.delete(`/api/v1/widgets/${widgetId}`);
      useDashboardStore.getState().removeWidget(widgetId);
      set({ isSaving: false, savingWidgetId: null });
    } catch (err) {
      set({ error: "Failed to delete widget", isSaving: false, savingWidgetId: null });
    }
  },

  refreshWidgetData: async (widgetId) => {
    try {
      const res = await apiClient.get<WidgetSpec>(
        `/api/v1/widgets/${widgetId}/data?refresh=true`
      );
      // Update the widget in the dashboard store with fresh chart_spec
      const dashStore = useDashboardStore.getState();
      const updated = dashStore.widgets.map((w) =>
        w.widget_id === widgetId ? { ...w, chart_spec: res.data.chart_spec } : w
      );
      useDashboardStore.setState({ widgets: updated });
    } catch (err) {
      // Silent fail for refresh — widget shows stale data
    }
  },
}));
```

### 4.3 Widget Data Store

Manages loading states and cached query results per widget. Tracks which widgets are currently fetching data.

```typescript
// src/stores/widgetDataStore.ts

import { create } from "zustand";

interface WidgetDataState {
  // State
  loadingWidgets: Set<string>;
  dataCache: Map<string, { data: unknown; fetchedAt: number }>;

  // Actions
  setLoading: (widgetId: string, loading: boolean) => void;
  setCachedData: (widgetId: string, data: unknown) => void;
  getCachedData: (widgetId: string) => unknown | null;
  isCacheStale: (widgetId: string, maxAgeMs?: number) => boolean;
  clearCache: () => void;
}

export const useWidgetDataStore = create<WidgetDataState>((set, get) => ({
  loadingWidgets: new Set(),
  dataCache: new Map(),

  setLoading: (widgetId, loading) => {
    set((s) => {
      const next = new Set(s.loadingWidgets);
      if (loading) {
        next.add(widgetId);
      } else {
        next.delete(widgetId);
      }
      return { loadingWidgets: next };
    });
  },

  setCachedData: (widgetId, data) => {
    set((s) => {
      const next = new Map(s.dataCache);
      next.set(widgetId, { data, fetchedAt: Date.now() });
      return { dataCache: next };
    });
  },

  getCachedData: (widgetId) => {
    const entry = get().dataCache.get(widgetId);
    return entry ? entry.data : null;
  },

  isCacheStale: (widgetId, maxAgeMs = 300_000) => {
    const entry = get().dataCache.get(widgetId);
    if (!entry) return true;
    return Date.now() - entry.fetchedAt > maxAgeMs;
  },

  clearCache: () => {
    set({ dataCache: new Map(), loadingWidgets: new Set() });
  },
}));
```

### 4.4 Store Interaction Flow

```
COO says "Show me a bar chart of tasks per person"
    │
    ▼
AI Layer generates WidgetSpec JSON
    │
    ▼
widgetStore.createWidget()       ← POST /api/v1/widgets
    │
    ├── Backend saves to MongoDB
    ├── Backend runs DataQueryEngine.execute() on the data_query
    ├── Backend populates chart_spec with real data
    └── Returns complete WidgetSpec
    │
    ▼
dashboardStore.addWidget()       ← adds to widgets array
    │
    ▼
WidgetGrid re-renders            ← React picks up new widget
    │
    ▼
WidgetRenderer dispatches        ← routes to BarChartWidget
    │
    ▼
BarChartWidget renders ECharts   ← chart_spec → ECharts option
```

On subsequent dashboard loads, the flow is simpler:

```
dashboardStore.loadDashboard()   ← GET /api/v1/dashboards/{id}
    │
    ▼
API returns Dashboard with       ← widgets already have populated chart_specs
populated WidgetSpec[]
    │
    ▼
WidgetGrid renders all widgets   ← no additional API calls needed
```

Widget data refresh (triggered by re-ingestion or manual refresh):

```
WebSocket event: "data_ingested"
    │
    ▼
For each widget in current dashboard:
    widgetDataStore.setLoading(widgetId, true)
    widgetStore.refreshWidgetData(widgetId)    ← GET /api/v1/widgets/{id}/data?refresh=true
    widgetDataStore.setLoading(widgetId, false)
```
