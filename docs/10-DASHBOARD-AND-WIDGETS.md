# Dashboard & Widgets: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | **Dashboard & Widgets** | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Dashboard Architecture Overview

ChiefOps has three distinct dashboard levels. Each serves a different purpose in the COO's workflow, and each has different rules about layout, content, and customization.

### 1.1 Three Dashboard Levels

| Level | Scope | Layout | Content Generation | Customizable |
|-------|-------|--------|-------------------|--------------|
| **Main Dashboard** | Global — across all projects | Fixed, system-defined | System-generated from aggregated data | No |
| **Project Dashboard (Static)** | Single project | Fixed, identical for every project | Auto-generated when project data is ingested or updated | No |
| **Project Dashboard (Custom)** | Single project | Fully dynamic | COO creates, removes, and modifies widgets entirely through NL conversation | Yes |

### 1.2 Main Dashboard

The global view. The COO opens ChiefOps and this is what they see. It provides a health-at-a-glance picture across every tracked project.

**What it shows:**
- Health score (0-100) with directional trend
- Active alert count
- AI-generated briefing text
- Project overview cards (one per project)
- Team activity summary
- Activity feed (recent events from Slack + Jira)

**Layout rules:** Fixed. The COO cannot add, remove, or rearrange sections. The system renders the same layout every time, populated with current data.

### 1.3 Project Dashboard (Static)

Auto-generated per project. Every project gets the same layout — the system fills it with project-specific data. When new data is ingested (Slack export, Jira CSV, Drive files), the dashboard regenerates its content.

**What it shows:**
- Project header with status, completion %, deadline, health score
- Timeline/Gantt chart (milestones, tasks, deadlines)
- People involved (person cards in a grid)
- Task breakdown by status (bar chart)
- Risk panel with severity levels
- Technical readiness checklist and architect questions
- Communication insights from Slack analysis

**Layout rules:** Fixed, identical across projects. Content is project-specific but the structure never changes.

### 1.4 Project Dashboard (Custom)

The dynamic layer. The COO manages this dashboard entirely through natural language. There is no drag-and-drop widget builder, no configuration panel, no settings modal. The COO speaks, and the dashboard changes.

**What it shows:** Whatever the COO has asked for — bar charts, line charts, KPI cards, tables, person grids, timelines, summaries, or any combination.

**Layout rules:** Dynamic. The AI auto-places widgets on a 12-column grid. The COO can ask for repositioning through conversation.

### 1.5 Navigation Between Dashboards

```
URL Structure:
  /                          → Main Dashboard
  /projects/:projectId       → Project Dashboard (Static)
  /projects/:projectId/custom → Project Dashboard (Custom)
```

The frontend router determines which dashboard to render. The Main Dashboard and Project Static Dashboard are React components with hardcoded layouts. The Custom Dashboard is a generic widget renderer that reads widget specs from the API.

---

## 2. Main Dashboard Layout

The Main Dashboard is a single-page view with a fixed vertical layout. No tabs, no sub-pages, no pagination. The COO sees everything at once (with scrolling for the activity feed).

### 2.1 Layout Structure

```
+============================================================================+
|  TOP BAR                                                                    |
|  +---------------------+  +-----------------------------+  +-----------+   |
|  |  HEALTH SCORE       |  |  QUICK SEARCH BAR           |  | ALERTS    |   |
|  |  87  ▲ +3           |  |  "Ask ChiefOps anything..." |  | 🔴 4     |   |
|  |  (large number)     |  |  (NL query input)           |  | (badge)   |   |
|  +---------------------+  +-----------------------------+  +-----------+   |
+============================================================================+
|  BRIEFING PANEL                                                             |
|  +------------------------------------------------------------------------+ |
|  |  "Good morning. Project Alpha is on track for its Feb 15 milestone.    | |
|  |   Two risks flagged on Project Beta — Jira backlog grew 23% this week. | |
|  |   Sarah Chen has been quiet for 3 days. No blockers on Gamma."         | |
|  +------------------------------------------------------------------------+ |
+============================================================================+
|  PROJECT CARDS GRID                                                         |
|  +------------------------+  +------------------------+  +---------------+ |
|  |  Project Alpha         |  |  Project Beta          |  |  Project      | |
|  |  ● Active              |  |  ● At Risk             |  |  Gamma        | |
|  |  Completion: 72%       |  |  Completion: 41%       |  |  ● Active     | |
|  |  Health: 91            |  |  Health: 63             |  |  Comp: 88%   | |
|  |  Deadline: Mar 15      |  |  Deadline: Feb 28      |  |  Health: 94  | |
|  |  Risks: 1              |  |  Risks: 4              |  |  Risks: 0    | |
|  +------------------------+  +------------------------+  +---------------+ |
+============================================================================+
|  TEAM OVERVIEW                        |  ACTIVITY FEED                      |
|  +----------------------------------+ |  +---------------------------------+|
|  |  Very Active: 8                  | |  |  10:23 AM — Sarah pushed 3      ||
|  |  Active: 12                      | |  |  commits to alpha-backend       ||
|  |  Moderate: 5                     | |  |  10:11 AM — Jira: BETA-142     ||
|  |  Quiet: 3                        | |  |  moved to "In Review"           ||
|  |  Inactive: 2                     | |  |  09:55 AM — Slack #alpha:       ||
|  |                                  | |  |  "API integration complete"      ||
|  |  Total tracked: 30              | |  |  09:30 AM — Risk flagged:       ||
|  +----------------------------------+ |  |  Beta deadline at risk           ||
|                                       |  |  ...                             ||
|                                       |  +---------------------------------+|
+============================================================================+
```

### 2.2 Top Bar

| Element | Details |
|---------|---------|
| **Health Score** | Aggregate score 0-100 across all projects. Large numeric display (48px font). Trend arrow (up/down/flat) with delta from previous calculation. Background color shifts: green (75-100), amber (50-74), red (0-49). |
| **Quick Search Bar** | Full-width NL input. Placeholder: "Ask ChiefOps anything...". Submits to the NL query pipeline. Always visible on every page. |
| **Alert Count Badge** | Circular badge showing count of unresolved alerts. Red background if count > 0. Clicking opens the alert panel. |

### 2.3 Briefing Panel

AI-generated text refreshed after each data ingestion. Three to five sentences summarizing the current state across all projects. Written in direct, executive-friendly language — no bullet points, no jargon. The briefing is stored in the `briefings` collection and regenerated when underlying data changes.

### 2.4 Project Cards Grid

Responsive grid of project summary cards. Each card is clickable (navigates to the Project Static Dashboard).

| Card Field | Source | Display |
|------------|--------|---------|
| Project name | `projects.name` | Bold heading |
| Status | `projects.status` | Color-coded badge: `active` (green), `at_risk` (amber), `blocked` (red), `completed` (blue), `planning` (gray) |
| Completion % | `projects.completion_percentage` | Progress bar + numeric value |
| Health score | `projects.health_score` | Numeric 0-100 with color coding |
| Deadline | `projects.deadline` | Date string, red if within 7 days |
| Key risk count | Count of `risks` with severity `high` or `critical` | Numeric badge |

Cards are arranged in a responsive grid: 3 columns on desktop (1200px+), 2 on tablet (768-1199px), 1 on mobile (<768px).

### 2.5 Team Overview

Summary panel showing the distribution of `activity_level` across all tracked people. Data comes from the `people` collection aggregation. No individual names — just counts per activity tier. Clicking navigates to the People page.

### 2.6 Activity Feed

Reverse-chronological list of recent events. Sources: Slack messages (from `slack_messages`), Jira task transitions (from `jira_tasks`), system events (alerts created, reports generated). Maximum 50 items displayed, with lazy-load scrolling. Each item shows timestamp, source icon (Slack/Jira/System), and a one-line description.

---

## 3. Project Dashboard (Static) Layout

Every project gets the same dashboard layout. The system populates it with project-specific data. This dashboard is not customizable — it is the consistent, predictable view that the COO can rely on for any project.

### 3.1 Layout Structure

```
+============================================================================+
|  PROJECT HEADER                                                             |
|  +------------------------------------------------------------------------+ |
|  |  Project Alpha                                              Health: 91 | |
|  |  ● Active    Completion: 72%    Deadline: Mar 15, 2026                 | |
|  +------------------------------------------------------------------------+ |
+============================================================================+
|  TIMELINE / GANTT                                                           |
|  +------------------------------------------------------------------------+ |
|  |  [ECharts Gantt Chart]                                                 | |
|  |  ═══════ Design Phase ══════                                           | |
|  |          ════════════ Backend Dev ════════════                          | |
|  |                    ══════ Frontend Dev ══════                           | |
|  |                              ▼ Milestone: API Complete                 | |
|  |                                        ══ QA ══                        | |
|  |  Jan         Feb         Mar         Apr                               | |
|  +------------------------------------------------------------------------+ |
+============================================================================+
|  PEOPLE                                  |  TASK BREAKDOWN                  |
|  +-------------------------------------+ |  +------------------------------+|
|  |  [Person]  [Person]  [Person]       | |  |  [ECharts Bar Chart]         ||
|  |  Sarah C.  Mike T.   Lisa P.        | |  |  ████████ Done: 34           ||
|  |  Lead Dev  Backend   Designer       | |  |  █████ In Progress: 21       ||
|  |  ●Active   ●Active   ●Moderate     | |  |  ███ To Do: 15               ||
|  |                                     | |  |  █ Blocked: 3                ||
|  |  [Person]  [Person]  [Person]       | |  |                              ||
|  |  ...                                | |  |                              ||
|  +-------------------------------------+ |  +------------------------------+|
+============================================================================+
|  RISK PANEL                              |  TECHNICAL READINESS             |
|  +-------------------------------------+ |  +------------------------------+|
|  |  ▲ Critical: API rate limiting      | |  |  ☑ Database schema finalized ||
|  |    may cause data loss at scale     | |  |  ☑ Auth flow implemented     ||
|  |    Identified: Feb 5                | |  |  ☐ Load testing pending      ||
|  |                                     | |  |  ☐ CI/CD pipeline setup      ||
|  |  ▲ High: No dedicated QA resource  | |  |                              ||
|  |    for frontend testing             | |  |  Architect Questions:        ||
|  |    Identified: Feb 3                | |  |  • Cache invalidation        ||
|  |                                     | |  |    strategy?                 ||
|  |  △ Medium: Slack channel has low   | |  |  • WebSocket scaling plan?   ||
|  |    engagement from design team      | |  |                              ||
|  +-------------------------------------+ |  +------------------------------+|
+============================================================================+
|  COMMUNICATION INSIGHTS                                                     |
|  +------------------------------------------------------------------------+ |
|  |  Slack activity: 142 messages this week (▲ 12% from last week)         | |
|  |  Most active channel: #alpha-backend (68 messages)                     | |
|  |  Key topics: API integration, database migration, auth flow            | |
|  |  Sentiment: Mostly positive. One tension thread around deadline scope. | |
|  +------------------------------------------------------------------------+ |
+============================================================================+
```

### 3.2 Project Header

| Element | Source | Display |
|---------|--------|---------|
| Project name | `projects.name` | Large heading, 28px |
| Status badge | `projects.status` | Same color coding as Main Dashboard cards |
| Completion % | `projects.completion_percentage` | Progress bar (full width) + numeric percentage |
| Deadline | `projects.deadline` | Date string. Red text if overdue. Amber if within 7 days. |
| Health score | `projects.health_score` | Large numeric (36px) with color background circle |

### 3.3 Timeline / Gantt

Rendered with Apache ECharts via `echarts-for-react`. The Gantt chart shows:

- **Milestones:** Diamond markers on the timeline. Data from `projects.milestones`.
- **Task phases:** Horizontal bars grouped by phase/epic. Data from `jira_tasks` grouped by epic or parent field.
- **Deadlines:** Vertical red dashed lines for the project deadline and milestone due dates.
- **Today marker:** Vertical solid line at the current date.

The chart uses a custom ECharts configuration with the ChiefOps theme. Time axis is auto-scaled to fit the project's date range with 10% padding on each side.

### 3.4 People Section

Grid of person cards for everyone involved in the project. Each card shows:

| Card Field | Source |
|------------|--------|
| Name | `people.name` |
| Avatar | `people.avatar_url` (fallback: initials) |
| Role | `people.role` |
| Activity level | `people.activity_level` — color-coded dot |
| Tasks assigned | `people.tasks_assigned` (filtered to this project) |

Cards are sorted by activity level (most active first). Grid layout: 4 columns on desktop, 3 on tablet, 2 on mobile.

### 3.5 Task Breakdown

Horizontal bar chart rendered with ECharts. Bars represent task counts grouped by status: Done, In Progress, To Do, Blocked. Data sourced from `jira_tasks` filtered by `project_id`, grouped by `status`.

### 3.6 Risk Panel

Vertical list of risk items from `projects.risks`, sorted by severity (critical first). Each item shows:

- Severity icon and label (Critical, High, Medium, Low)
- Risk description text
- Date identified
- Color coding: Critical = red, High = orange, Medium = amber, Low = gray

### 3.7 Technical Readiness

Checklist rendered from `projects.technical_readiness`. Each item shows a checkbox icon (filled or empty) and description text. Below the checklist, a section labeled "Architect Questions" lists unresolved technical questions extracted by the AI during analysis.

### 3.8 Communication Insights

Summary panel showing Slack activity metrics for this project. Data is aggregated from `slack_messages` filtered by project-related channels. Shows: message count with trend, most active channel, key topic keywords, and overall sentiment assessment.

---

## 4. Dynamic Widget System

The Custom Dashboard is powered by a dynamic widget system. Widgets are JSON specifications stored in MongoDB. The frontend reads these specs from the API and renders them using a generic widget renderer component. The COO manages widgets entirely through natural language conversation.

### 4.1 Widget Spec Structure

Every widget is stored as a document in the `dashboard_widgets` collection. The full JSON structure is:

```json
{
  "widget_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "dashboard_id": "proj_alpha_uuid_custom",
  "widget_type": "bar_chart",
  "title": "Tasks per Person — Project Alpha",
  "data_query": {
    "source": "jira_tasks",
    "group_by": "assignee",
    "metric": "count",
    "split_by": null,
    "filters": {
      "project_id": "proj_alpha_uuid"
    },
    "time_range": null
  },
  "chart_spec": {
    "xAxis": { "type": "category", "data": [] },
    "yAxis": { "type": "value" },
    "series": [{ "type": "bar", "data": [] }],
    "tooltip": { "trigger": "axis" },
    "grid": { "left": "3%", "right": "4%", "bottom": "3%", "containLabel": true }
  },
  "position": {
    "row": 0,
    "col": 0,
    "width": 6,
    "height": 4
  },
  "created_by": "coo_conversation",
  "created_at": "2026-02-08T14:30:00Z",
  "updated_at": "2026-02-08T14:30:00Z",
  "conversation_turn_id": "turn_xyz_uuid"
}
```

**Field reference** (authoritative schema in [Data Models](./03-DATA-MODELS.md)):

| Field | Type | Description |
|-------|------|-------------|
| `widget_id` | UUID v4 string | Unique identifier |
| `dashboard_id` | string | Format: `"{project_id}_custom"` or `"main"` |
| `widget_type` | enum | One of: `bar_chart`, `line_chart`, `pie_chart`, `gantt`, `table`, `kpi_card`, `summary_text`, `person_grid`, `timeline`, `activity_feed` |
| `title` | string | Display title shown above the widget |
| `data_query` | DataQuery object | Defines what data to fetch and how to aggregate. Resolved into MongoDB aggregation pipelines at render time. |
| `chart_spec` | dict | ECharts JSON option object. Populated with real data by the backend before sending to the frontend. |
| `position` | WidgetPosition object | Grid placement: `row`, `col`, `width` (1-12), `height` (1-8) |
| `created_by` | enum | `"coo_conversation"` or `"system_default"` |
| `conversation_turn_id` | string or null | Links back to the conversation turn that created this widget |
| `created_at` / `updated_at` | datetime | UTC timestamps |

### 4.2 Widget Creation Flow

```
COO speaks:
  "Show me a bar chart of tasks per person for Project Alpha"
         |
         v
+-------------------+
| NL Query Pipeline |  Intent classified as: widget_create
+-------------------+
         |
         v
+-------------------+
| AI Layer          |  Generates:
| (Widget Prompt)   |  - widget_type: bar_chart
+-------------------+  - title: "Tasks per Person — Project Alpha"
         |             - data_query: { source: "jira_tasks", group_by: "assignee", ... }
         v             - chart_spec: { xAxis: {...}, yAxis: {...}, series: [...] }
+-------------------+
| Widget Manager    |  1. Validates the widget spec against Pydantic model
| (Backend)         |  2. Assigns position using auto-placement algorithm
+-------------------+  3. Stores in dashboard_widgets collection
         |             4. Returns widget_id to frontend
         v
+-------------------+
| Data Query Engine |  1. Reads data_query from the widget spec
| (Backend)         |  2. Builds MongoDB aggregation pipeline
+-------------------+  3. Executes pipeline, gets result data
         |             4. Populates chart_spec with real data values
         v
+-------------------+
| Widget Renderer   |  1. Receives widget spec + populated chart_spec
| (Frontend)        |  2. Selects React component by widget_type
+-------------------+  3. Passes chart_spec to echarts-for-react
         |             4. Widget appears on the Custom Dashboard
         v
    [Widget visible on dashboard]
```

### 4.3 Widget Modification Flow

```
COO speaks:
  "Change that tasks chart to a pie chart"
         |
         v
+-------------------+
| NL Query Pipeline |  Intent: widget_modify
+-------------------+  Resolves "that tasks chart" to widget_id via:
         |               - Most recently discussed widget in conversation
         |               - Title fuzzy match across dashboard widgets
         v
+-------------------+
| AI Layer          |  Generates updated fields:
+-------------------+  - widget_type: pie_chart
         |             - chart_spec: { series: [{ type: "pie", ... }] }
         v             (data_query remains unchanged)
+-------------------+
| Widget Manager    |  1. Loads existing widget by widget_id
+-------------------+  2. Merges updated fields
         |             3. Updates document in MongoDB
         v             4. Returns updated widget to frontend
+-------------------+
| Frontend          |  WebSocket pushes updated widget spec
+-------------------+  Widget re-renders in place with new chart type
```

### 4.4 Widget Deletion Flow

```
COO speaks:
  "Remove the tasks chart"
         |
         v
+-------------------+
| NL Query Pipeline |  Intent: widget_delete
+-------------------+  Resolves "the tasks chart" to widget_id
         |
         v
+-------------------+
| Widget Manager    |  1. Deletes document from dashboard_widgets
+-------------------+  2. Recalculates positions for remaining widgets (optional compaction)
         |             3. Returns confirmation
         v
+-------------------+
| Frontend          |  WebSocket pushes widget removal event
+-------------------+  Widget disappears from the grid
```

### 4.5 Auto-Refresh on Data Ingestion

When new data is ingested (Slack export, Jira CSV, Drive files), the system triggers a refresh of all widgets whose `data_query` references the affected data source.

```
Ingestion Pipeline completes
         |
         v
+-------------------+
| Refresh Trigger   |  Identifies affected collections
+-------------------+  (e.g., "jira_tasks" changed)
         |
         v
+-------------------+
| Widget Manager    |  Queries dashboard_widgets where
+-------------------+  data_query.source matches affected collection
         |
         v
+-------------------+
| Data Query Engine |  Re-executes aggregation pipelines
+-------------------+  for each affected widget
         |
         v
+-------------------+
| WebSocket Push    |  Sends updated chart_spec to
+-------------------+  connected frontend clients
         |
         v
    [Widgets update in real time on dashboard]
```

The frontend does not poll. The backend pushes updates through WebSocket when data changes.

---

## 5. Grid System

### 5.1 Grid Specification

The Custom Dashboard uses a 12-column grid system. This is a logical grid — the frontend maps grid coordinates to CSS grid positions.

| Property | Value |
|----------|-------|
| Columns | 12 |
| Row height | 80px base unit |
| Gap | 16px between widgets |
| Max width | 1440px (centered) |
| Padding | 24px on each side |

### 5.2 AI Auto-Placement

There is no drag-and-drop. The AI determines where to place new widgets based on:

1. **Available space:** Scan the grid for the first open position that fits the widget's default size.
2. **Logical grouping:** Related widgets are placed adjacent when possible (e.g., a KPI card next to its detail chart).
3. **Reading order:** Top-left to bottom-right, following natural scan patterns.

The auto-placement algorithm is deterministic:

```python
def find_next_position(existing_widgets: list[WidgetPosition], new_width: int, new_height: int) -> WidgetPosition:
    """
    Scan the grid top-to-bottom, left-to-right for the first
    open rectangle that fits the requested dimensions.
    """
    occupied = build_occupancy_grid(existing_widgets)
    for row in range(MAX_ROWS):
        for col in range(13 - new_width):  # Ensure widget fits within 12 columns
            if is_region_free(occupied, row, col, new_width, new_height):
                return WidgetPosition(row=row, col=col, width=new_width, height=new_height)
    # Append to next available row if grid is full
    max_row = max((w.row + w.height for w in existing_widgets), default=0)
    return WidgetPosition(row=max_row, col=0, width=new_width, height=new_height)
```

### 5.3 Default Sizes per Widget Type

| Widget Type | Default Width | Default Height | Grid Columns | Grid Rows |
|-------------|--------------|----------------|--------------|-----------|
| `bar_chart` | 6 | 4 | Half width | 320px |
| `line_chart` | 6 | 4 | Half width | 320px |
| `pie_chart` | 4 | 4 | Third width | 320px |
| `gantt` | 12 | 5 | Full width | 400px |
| `table` | 12 | 4 | Full width | 320px |
| `kpi_card` | 3 | 2 | Quarter width | 160px |
| `summary_text` | 6 | 3 | Half width | 240px |
| `person_grid` | 6 | 4 | Half width | 320px |
| `timeline` | 12 | 5 | Full width | 400px |
| `activity_feed` | 6 | 5 | Half width | 400px |

### 5.4 Responsive Behavior

| Breakpoint | Grid Columns | Behavior |
|------------|-------------|----------|
| >= 1200px | 12 | Full grid layout |
| 768-1199px | 6 | All widgets scale to max 6 columns. Widgets wider than 6 are clamped. |
| < 768px | 1 | Single column stack. All widgets render full width. |

---

## 6. NL Widget Management Examples

The COO manages the Custom Dashboard entirely through conversation. Below are representative examples covering creation, modification, deletion, and complex operations.

### 6.1 Widget Creation

| COO Says | AI Action | Widget Type | Data Query |
|----------|-----------|-------------|------------|
| "Show me a bar chart of tasks per person for Alpha" | Creates bar chart | `bar_chart` | source: `jira_tasks`, group_by: `assignee`, metric: `count`, filters: `{project_id: alpha}` |
| "Add a pie chart showing task status distribution" | Creates pie chart | `pie_chart` | source: `jira_tasks`, group_by: `status`, metric: `count` |
| "I want to see a line chart of Slack activity over the last 30 days" | Creates line chart | `line_chart` | source: `slack_messages`, group_by: `date`, metric: `count`, time_range: last 30 days |
| "Put up a KPI card showing total open tasks" | Creates KPI card | `kpi_card` | source: `jira_tasks`, metric: `count`, filters: `{status: {$ne: "done"}}` |
| "Show me a table of all people and their task counts" | Creates table | `table` | source: `people`, metric: `count:tasks_assigned` |
| "Add a Gantt of the milestones for this project" | Creates Gantt | `gantt` | source: `projects.milestones`, filters: `{project_id: current}` |
| "Show the activity feed for Project Beta" | Creates activity feed | `activity_feed` | source: `slack_messages`, filters: `{project_id: beta}` |
| "Give me a summary of the project risks" | Creates summary text | `summary_text` | AI-generated text from `projects.risks` |

### 6.2 Widget Modification

| COO Says | AI Action |
|----------|-----------|
| "Change that to a horizontal bar chart" | Updates `chart_spec` orientation on the most recently referenced widget |
| "Make the tasks chart show story points instead of count" | Updates `data_query.metric` from `count` to `sum:story_points` |
| "Add a breakdown by status to the tasks per person chart" | Updates `data_query.split_by` to `status`, changes chart to stacked bar |
| "Rename that widget to 'Engineering Velocity'" | Updates `title` field |
| "Make the pie chart bigger — full width" | Updates `position.width` to 12 and recalculates adjacent widget positions |
| "Filter the activity feed to only show messages from this week" | Updates `data_query.time_range` to current week |
| "Show only critical and high risks in the risk summary" | Updates `data_query.filters` to include severity filter |

### 6.3 Widget Deletion

| COO Says | AI Action |
|----------|-----------|
| "Remove the pie chart" | Deletes widget matching type `pie_chart` on current dashboard |
| "Get rid of the tasks table" | Deletes widget matching title containing "tasks" and type `table` |
| "Clear all widgets from this dashboard" | Deletes all widgets where `dashboard_id` matches current project custom dashboard |
| "I don't need the activity feed anymore" | Deletes widget matching type `activity_feed` |

### 6.4 Complex Operations

| COO Says | AI Action |
|----------|-----------|
| "Set up a dashboard for Alpha with task breakdown, team overview, and a burndown" | Creates three widgets in sequence: `bar_chart` (tasks by status), `person_grid` (team), `line_chart` (burndown) |
| "Move the KPI cards to the top row" | Updates `position.row` to 0 for all `kpi_card` widgets and shifts other widgets down |
| "Replace the table with a bar chart showing the same data" | Deletes the `table` widget, creates a `bar_chart` widget with the same `data_query`, places it in the same position |
| "Compare task completion rates between Alpha and Beta side by side" | Creates two `bar_chart` widgets, each 6 columns wide, positioned adjacent. Filters scoped to respective projects |

---

## 7. ECharts Theme

All charts in ChiefOps — dashboard widgets, project static charts, and inline conversation charts — use a consistent custom ECharts theme. The theme is registered once at application startup and applied automatically to every `echarts-for-react` instance.

### 7.1 Theme Registration

```typescript
// src/config/echarts-theme.ts

import * as echarts from 'echarts/core';

const chiefopsTheme = {
  color: [
    '#1E3A5F',  // Primary blue
    '#00BCD4',  // Accent teal
    '#4CAF50',  // Success green
    '#FF9800',  // Warning orange
    '#F44336',  // Danger red
    '#9C27B0',  // Purple (extended palette)
    '#3F51B5',  // Indigo (extended palette)
    '#009688',  // Deep teal (extended palette)
    '#795548',  // Brown (extended palette)
    '#607D8B',  // Blue-gray (extended palette)
  ],

  backgroundColor: 'transparent',

  textStyle: {
    fontFamily: "'Inter', sans-serif",
    color: '#1A1A2E',
  },

  title: {
    textStyle: {
      fontFamily: "'Inter', sans-serif",
      fontWeight: 600,
      fontSize: 14,
      color: '#1A1A2E',
    },
    subtextStyle: {
      fontFamily: "'Inter', sans-serif",
      fontSize: 12,
      color: '#6B7280',
    },
  },

  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '15%',
    containLabel: true,
  },

  categoryAxis: {
    axisLine: { lineStyle: { color: '#E5E7EB' } },
    axisTick: { show: false },
    axisLabel: {
      fontFamily: "'Inter', sans-serif",
      fontSize: 11,
      color: '#6B7280',
    },
    splitLine: { show: false },
  },

  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      fontFamily: "'Inter', sans-serif",
      fontSize: 11,
      color: '#6B7280',
    },
    splitLine: {
      lineStyle: { color: '#F3F4F6', type: 'dashed' },
    },
  },

  tooltip: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderWidth: 1,
    textStyle: {
      fontFamily: "'Inter', sans-serif",
      fontSize: 12,
      color: '#1A1A2E',
    },
    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-radius: 8px;',
  },

  legend: {
    textStyle: {
      fontFamily: "'Inter', sans-serif",
      fontSize: 12,
      color: '#6B7280',
    },
    icon: 'roundRect',
    itemWidth: 12,
    itemHeight: 12,
    itemGap: 16,
  },

  bar: {
    barMaxWidth: 40,
    itemStyle: { borderRadius: [4, 4, 0, 0] },
  },

  line: {
    smooth: true,
    symbolSize: 6,
    lineStyle: { width: 2 },
  },

  pie: {
    itemStyle: { borderColor: '#FFFFFF', borderWidth: 2 },
    label: {
      fontFamily: "'Inter', sans-serif",
      fontSize: 12,
    },
  },
};

echarts.registerTheme('chiefops', chiefopsTheme);

export default chiefopsTheme;
```

### 7.2 Theme Usage

Every chart component applies the theme by name:

```tsx
import ReactECharts from 'echarts-for-react';

<ReactECharts
  option={chartOption}
  theme="chiefops"
  style={{ height: '100%', width: '100%' }}
/>
```

### 7.3 Color Assignment Rules

| Usage | Color(s) |
|-------|----------|
| Primary data series | `#1E3A5F` (primary blue) |
| Secondary data series | `#00BCD4` (accent teal) |
| Status — completed/done | `#4CAF50` (green) |
| Status — in progress | `#00BCD4` (teal) |
| Status — blocked/overdue | `#F44336` (red) |
| Status — to do/planned | `#E5E7EB` (gray) |
| Status — at risk/warning | `#FF9800` (orange) |
| Multi-series charts | Cycle through the full 10-color palette in order |

### 7.4 Data Label Typography

| Context | Font | Size | Weight |
|---------|------|------|--------|
| Axis labels | Inter | 11px | 400 |
| Tooltip text | Inter | 12px | 400 |
| Tooltip values | JetBrains Mono | 13px | 600 |
| KPI card main number | JetBrains Mono | 48px | 700 |
| KPI card label | Inter | 13px | 500 |
| Chart title | Inter | 14px | 600 |

---

**See also:** [Widget Types & Components Reference](./10B-WIDGET-TYPES-AND-COMPONENTS.md) for detailed widget type definitions, ECharts configurations, data query engine, and React component architecture.
