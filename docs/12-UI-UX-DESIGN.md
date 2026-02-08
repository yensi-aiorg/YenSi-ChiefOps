# UI/UX Design: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | **UI/UX Design**

---

## 1. Design Philosophy

ChiefOps is not a traditional dashboard tool. It is a **conversational operations advisor** that happens to have a visual layer. Every design decision flows from this core identity.

### 1.1 NL-First Interaction Model

The conversation is the product. Every other visual element exists to support, contextualize, or result from a natural language interaction.

| Principle | What It Means | What It Does NOT Mean |
|-----------|--------------|----------------------|
| **Conversation is primary** | The COO types questions and gets answers | There is no UI at all |
| **No forms except where unavoidable** | Settings and file upload are the only form-based pages | Everything must go through chat |
| **Ask, don't configure** | "Show me a burndown for Alpha" instead of opening a chart builder | The AI guesses what the COO wants |
| **Context follows the COO** | The system knows which project the COO is looking at | The COO must re-state context every time |

The search bar at the top of every page is the single most important UI element. It is always visible, always ready, and always the first thing the eye is drawn to.

### 1.2 Visual Excellence

ChiefOps must sell itself on sight. When a prospect sees a demo or screenshot, the reaction must be: "I want that."

- **Clean whitespace** — breathing room between elements, never cramped
- **Professional color palette** — deep blues and teals, not startup-trendy gradients
- **Sharp typography** — Inter for readability, JetBrains Mono for data
- **Purposeful data visualization** — charts that communicate insight, not just display numbers
- **Subtle polish** — micro-animations, smooth transitions, consistent spacing

This is a product for COOs at Series A/B startups. The aesthetic must convey: **competence, clarity, and control**.

### 1.3 Information Density

A COO needs to see a lot of data without feeling overwhelmed. The design achieves this through:

- **Hierarchical layouts** — most important metrics largest and highest
- **Card-based composition** — discrete information units that scan quickly
- **Color-coded status** — green/amber/red understood at a glance
- **Sparklines and trends** — directional data without requiring full charts
- **Numerical precision** — exact numbers for scores, percentages, and counts

### 1.4 Progressive Disclosure

Information unfolds in layers:

1. **Layer 0 — Glanceable** — Health scores, status badges, trend arrows visible on the dashboard without any interaction
2. **Layer 1 — Scannable** — AI briefing text, project cards with metrics, team overview numbers visible on the dashboard with minimal scrolling
3. **Layer 2 — Queryable** — Detailed analysis, deep-dive charts, person-level data available through natural language queries
4. **Layer 3 — Exportable** — Full reports, comprehensive data views generated on demand

The COO never has to drill through nested menus. They see the summary, and if they want more, they ask.

### 1.5 Consistent Styling (YENSI Branding-Ready)

All visual tokens (colors, fonts, spacing, shadows) are defined as CSS custom properties and Tailwind theme extensions. When YENSI branding guidelines are finalized, a single theme file update propagates across the entire application.

```
/* Theme structure — single source of truth */
:root {
  --color-primary: #1E3A5F;
  --color-accent: #00BCD4;
  --color-success: #4CAF50;
  --color-warning: #FF9800;
  --color-danger: #F44336;
  --color-bg: #F5F7FA;
  --color-card: #FFFFFF;
  --color-text: #1A1A2E;
  --color-muted: #6B7280;
  --font-heading: 'Inter', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-elevated: 0 10px 15px -3px rgba(0,0,0,0.1);
  --transition-default: 200ms ease;
  --transition-slow: 300ms ease;
}
```

---

## 2. Page Structure & Navigation

### 2.1 Application Pages

ChiefOps has exactly six page types. This deliberate constraint keeps the product focused and learnable.

| # | Page | Route | Purpose | Form UI? |
|---|------|-------|---------|----------|
| 1 | Main Dashboard | `/` | Global operational overview | No |
| 2 | Project Dashboard (Static) | `/project/:id` | Auto-generated project view | No |
| 3 | Project Dashboard (Custom) | `/project/:id/custom` | NL-customized widget layout | No |
| 4 | Report Preview | `/project/:id/report/:reportId` | Report viewing and NL editing | No |
| 5 | Data Ingestion | `/ingest` | File upload and processing | **Yes** |
| 6 | Settings | `/settings` | Branding, preferences, project config | **Yes** |

Only two pages (Data Ingestion and Settings) contain traditional form elements. Every other page is driven entirely by the conversational interface and auto-generated content.

### 2.2 Navigation Architecture

#### Left Sidebar (Persistent)

The left sidebar is the primary structural navigation element. It is always present on desktop, collapsible on tablet.

```
┌──────────────────┐
│  ◆ ChiefOps      │  ← Logo / brand mark (clickable → Main Dashboard)
│                   │
│  ▸ Main Dashboard │  ← Always first, highlighted when active
│  ─────────────── │
│  PROJECTS         │  ← Section label (uppercase, small, muted)
│  ● Alpha          │  ← Green dot = on track
│  ◐ Beta           │  ← Amber dot = at risk
│  ● Gamma          │  ← Green dot = on track
│  ○ Delta          │  ← Red dot = behind
│  ─────────────── │
│  ⚙ Settings       │
│  ⬆ Data Ingestion │
│                   │
│  ─────────────── │
│  ◯ v0.1.0        │  ← Version indicator (bottom)
└──────────────────┘
```

**Sidebar specifications:**

| Property | Value |
|----------|-------|
| Width (expanded) | 240px |
| Width (collapsed) | 64px (icons only) |
| Background | `#FFFFFF` with right border `1px solid #E5E7EB` |
| Project dot size | 8px diameter |
| Active item | Background `#EBF5FF`, left border 3px `--color-primary` |
| Hover item | Background `#F3F4F6` |
| Transition | 300ms ease (collapse/expand) |
| Z-index | 40 |

**Project list behavior:**

- Projects are sorted by health score (lowest first, so problems are visible)
- Each project shows: status dot, project name (truncated at 20 chars with ellipsis), health score number
- Clicking a project navigates to `/project/:id` (Static Dashboard)
- No nested navigation under projects — the project dashboard itself provides all project-level views
- If there are more than 10 projects, the list becomes scrollable with a subtle fade at the bottom

#### Top Bar (Persistent)

The top bar is the COO's primary interaction surface. It spans the full width above the content area (to the right of the sidebar).

```
┌─────────────────────────────────────────────────────────────────────┐
│  [≡]   🔍 Ask anything about your operations...       ⚡ 87  🔔 3  │
│         ▲                                               ▲     ▲    │
│     Search bar                                      Health  Alerts │
│   (NL input)                                         Score        │
└─────────────────────────────────────────────────────────────────────┘
```

**When inside a project view, the top bar adds context:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  [≡]   🔍 Ask about Project Alpha...    Alpha ● On Track  ⚡ 87 🔔 3│
└─────────────────────────────────────────────────────────────────────┘
```

**Top bar specifications:**

| Property | Value |
|----------|-------|
| Height | 56px |
| Background | `#FFFFFF` with bottom border `1px solid #E5E7EB` |
| Position | Fixed, top of content area |
| Z-index | 50 |
| Shadow | `0 1px 3px rgba(0,0,0,0.04)` |

**Top bar elements (left to right):**

1. **Hamburger toggle** (`[≡]`) — collapses/expands the sidebar (only visible below 1440px; above 1440px the sidebar is always expanded)
2. **Search bar** — the global NL input (see Section 3 for full specification)
3. **Project context badge** — visible only on project pages; shows project name, status dot, status label
4. **Health Score** — global health score with lightning icon, color-coded (green > 70, amber 40-70, red < 40)
5. **Alert count** — bell icon with red badge showing unread alert count; clicking opens alerts dropdown
6. **Chat toggle** — button to open/close the chat sidebar (see Section 3)

#### No Traditional Menu Dropdowns

ChiefOps deliberately avoids dropdown menus, hamburger-hidden navigation, and nested menu structures. The rationale:

- **Discoverability through conversation** — the COO asks for what they need rather than hunting through menus
- **Reduced cognitive load** — fewer choices visible means faster decisions
- **Consistent interaction pattern** — the search bar is always the answer to "how do I..."
- **Cleaner aesthetic** — no menu bars cluttering the interface

The only dropdown-like elements in the entire application are:
1. The alerts panel (clicking the bell icon)
2. File type selector on the Data Ingestion page
3. Settings dropdowns (timezone, language)

---

## 3. The Conversational Interface

The conversational interface is the heart of ChiefOps. It operates in two complementary modes: **Quick Query** and **Chat Sidebar**.

### 3.1 Quick Query (Search Bar)

The search bar is always visible in the top bar. It is the primary entry point for all natural language interactions.

#### Visual States

**Default (unfocused):**
```
┌──────────────────────────────────────────────────────────┐
│  🔍  Ask anything about your operations...               │
└──────────────────────────────────────────────────────────┘
```
- Width: `min(600px, 50vw)`
- Height: 40px
- Background: `#F3F4F6`
- Border: `1px solid #E5E7EB`
- Border radius: 20px (pill shape)
- Placeholder text: `#9CA3AF`, font-size 14px
- Icon: magnifying glass, `#9CA3AF`

**Focused (no input yet):**
```
┌──────────────────────────────────────────────────────────────┐
│  🔍  │                                                   ⌘K │
├──────────────────────────────────────────────────────────────┤
│  Recent Queries                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  What's the status of Project Alpha?                  │   │
│  │  Who hasn't committed code this week?                 │   │
│  │  Show me the sprint burndown for Beta                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Suggested                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📋 Give me today's briefing                          │   │
│  │  📊 Show project health overview                      │   │
│  │  👥 Who needs attention this week?                    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```
- Width expands to `min(700px, 60vw)` with smooth animation (200ms)
- Height remains 40px (input), dropdown panel appears below
- Background: `#FFFFFF`
- Border: `2px solid --color-accent` (teal)
- Shadow: `--shadow-elevated`
- Dropdown: max-height 400px, scroll if needed
- Recent queries: last 5, most recent first
- Suggested queries: contextual (different per page)
- Keyboard shortcut hint: `Cmd+K` / `Ctrl+K` shown at right edge

**Typing (input present):**
```
┌──────────────────────────────────────────────────────────────┐
│  🔍  What's the risk status for Alpha?               ↵ Send │
├──────────────────────────────────────────────────────────────┤
│  Auto-suggestions (if applicable)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  What's the risk status for Alpha sprint 23?          │   │
│  │  What's the risk summary for Alpha?                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```
- Send button appears at right edge (teal, pill shape)
- Submit on Enter key
- Auto-suggestions appear if the system can predict completions
- Esc key: clears input and unfocuses

#### Response Handling

When the COO submits a query, the response routing depends on complexity:

**Simple query (factual answer, single metric, short text):**

The response appears as an **inline card** directly below the search bar, pushing page content down slightly.

```
┌──────────────────────────────────────────────────────────────┐
│  🔍  What's Alpha's health score?                    ↵ Send │
└──────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│  ◆ Project Alpha Health Score                          [✕]  │
│                                                              │
│     ╭───╮                                                    │
│     │87 │   ▲ +3 from last week                             │
│     ╰───╯                                                    │
│                                                              │
│  Sprint: 78  │  Communication: 91  │  Documentation: 82     │
│                                                              │
│  ────────────────────────────────────────────────────        │
│  💬 Ask a follow-up...                                       │
└──────────────────────────────────────────────────────────────┘
```

- Card: white background, `--shadow-elevated`, border-radius 12px
- Appears with a slide-down animation (200ms)
- Dismissible with the [X] button or by clicking outside
- Has a mini follow-up input at the bottom
- If the COO asks a follow-up, the card auto-opens the full Chat Sidebar with context preserved

**Complex query (multi-part answer, chart, table, long analysis):**

The Chat Sidebar opens automatically and the response streams there.

#### Search Bar Specifications

| Property | Value |
|----------|-------|
| Keyboard shortcut | `Cmd+K` (Mac) / `Ctrl+K` (Windows/Linux) |
| Debounce (suggestions) | 300ms |
| Max input length | 500 characters |
| History stored | Last 50 queries per user (localStorage) |
| Context awareness | Automatically scopes to current project when on a project page |

### 3.2 Chat Sidebar

The Chat Sidebar is the full conversational interface for complex, multi-turn interactions.

#### Layout

```
┌────────────────────────────────────────┐
│  💬 Chat — Project Alpha          [─]  │  ← Header with context and minimize
│  ──────────────────────────────────── │
│                                        │
│                     ┌────────────────┐ │
│                     │ What's Alpha's │ │  ← User message (right-aligned, blue)
│                     │ team velocity? │ │
│                     └────────────────┘ │
│                                        │
│  ┌────────────────────────────────┐    │
│  │ Project Alpha's team velocity  │    │  ← Assistant message (left, gray)
│  │ over the last 4 sprints:      │    │
│  │                                │    │
│  │  ┌──────────────────────────┐ │    │
│  │  │  ╱╲    ╱╲               │ │    │  ← Inline chart
│  │  │ ╱  ╲  ╱  ╲  ╱╲         │ │    │
│  │  │╱    ╲╱    ╲╱  ╲        │ │    │
│  │  │ S20   S21   S22  S23    │ │    │
│  │  └──────────────────────────┘ │    │
│  │                                │    │
│  │ Velocity has been trending    │    │
│  │ upward. Sprint 22 saw a 15%  │    │
│  │ increase due to Raj and       │    │
│  │ Priya's output.              │    │
│  │                                │    │
│  │ ┌──────────┐ ┌─────────────┐ │    │
│  │ │📌 Pin to │ │📊 Add to    │ │    │  ← Action buttons
│  │ │ dashboard │ │ report      │ │    │
│  │ └──────────┘ └─────────────┘ │    │
│  └────────────────────────────────┘    │
│                                        │
│  ──────────────────────────────────── │
│  ┌────────────────────────────────┐    │
│  │ Type a message...         [➤] │    │  ← Input area
│  └────────────────────────────────┘    │
└────────────────────────────────────────┘
```

#### Chat Sidebar Specifications

| Property | Value |
|----------|-------|
| Width | 400px (fixed) |
| Position | Right side of viewport, overlays content |
| Background | `#FFFFFF` |
| Border | Left border `1px solid #E5E7EB` |
| Shadow | `-4px 0 15px rgba(0,0,0,0.05)` |
| Z-index | 45 |
| Open/close transition | Slide from right, 300ms ease |
| Header height | 48px |
| Input area height | 56px (expandable to 120px for long messages) |

#### Message Bubbles

**User messages:**

| Property | Value |
|----------|-------|
| Alignment | Right |
| Background | `#1E3A5F` (primary blue) |
| Text color | `#FFFFFF` |
| Border radius | 16px 16px 4px 16px (flat bottom-right corner) |
| Max width | 85% of sidebar width |
| Padding | 12px 16px |
| Font size | 14px |
| Timestamp | Below bubble, right-aligned, 11px, `#9CA3AF` |

**Assistant messages:**

| Property | Value |
|----------|-------|
| Alignment | Left |
| Background | `#F3F4F6` |
| Text color | `#1A1A2E` |
| Border radius | 16px 16px 16px 4px (flat bottom-left corner) |
| Max width | 90% of sidebar width |
| Padding | 12px 16px |
| Font size | 14px |
| Timestamp | Below bubble, left-aligned, 11px, `#9CA3AF` |

#### Rich Content in Assistant Messages

Assistant messages can contain structured content beyond plain text:

**Inline charts:**
- Rendered as interactive ECharts instances inside the message bubble
- Chart height: 200px within the bubble
- Full ECharts interactivity (hover tooltips, zoom on time-series)
- Below the chart: action buttons ("Pin to dashboard", "Add to report", "Expand")

**Tables:**
- Rendered as styled HTML tables inside the bubble
- Max 5 visible rows, "Show all N rows" link if more
- Columns auto-sized, horizontally scrollable if needed
- Sortable by clicking column headers

**Person cards:**
- Compact inline cards showing: avatar placeholder (initials), name, role, key metric
- Clickable to expand into full person detail (within the chat)

**Report links:**
- Styled as a card with report icon, title, and "Open" button
- Clicking opens the Report Preview page

**Action buttons:**
- Appear below rich content blocks
- Pill-shaped, outlined style (border only, no fill)
- On hover: fill with light accent color
- Common actions: "Pin to dashboard", "Add to report", "Show more detail", "Export this"

#### Context Management

The Chat Sidebar maintains conversation context:

- **Project scoping:** When the COO is on a project page, the chat is automatically scoped to that project. The header shows "Chat - Project Alpha".
- **Global context:** When on the Main Dashboard, the chat has global context across all projects.
- **Stream switching:** If the COO navigates to a different project, the chat switches context. The previous conversation is preserved and accessible.
- **Conversation history:** Stored per project stream. The COO can scroll up to see previous messages.
- **Context indicator:** A subtle label below the header shows the active context: "Talking about: Project Alpha, Sprint 23"

#### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+K` / `Ctrl+K` | Focus the search bar |
| `Cmd+Shift+C` / `Ctrl+Shift+C` | Toggle chat sidebar |
| `Escape` | Close inline response card / unfocus search bar |
| `Enter` | Send message (in chat input) |
| `Shift+Enter` | New line (in chat input) |
| `Up Arrow` (in empty input) | Edit last sent message |

### 3.3 Inline Chart Rendering in Chat

When the AI generates a chart in response to a question, it is rendered as a fully interactive ECharts instance within the assistant's message bubble.

**Chart rendering flow:**

1. COO asks: "Show me the sprint velocity trend for Alpha"
2. AI Layer generates a response containing a chart specification (JSON)
3. Frontend detects the chart spec in the response stream
4. A `ChartContainer` component renders inside the `ChatBubble`
5. The chart is interactive (hover tooltips, click events)
6. Below the chart, action buttons appear

**Chart-to-widget promotion:**

When the COO says "Add that to my dashboard" or "Pin that chart":

1. The chart specification is extracted from the message
2. A new widget is created on the Custom Dashboard
3. The widget is placed in the next available grid position
4. Confirmation appears in the chat: "Added velocity trend chart to your Alpha dashboard."

**Supported chart types in chat:**

| Chart Type | Use Case | ECharts Type |
|-----------|----------|--------------|
| Line | Trends over time (velocity, score history) | `line` |
| Bar | Comparisons (per-person output, task counts) | `bar` |
| Pie/Donut | Proportions (task distribution, time allocation) | `pie` |
| Gauge | Single metrics (health score, completion %) | `gauge` |
| Heatmap | Activity density (commit heatmap, communication) | `heatmap` |
| Radar | Multi-axis comparison (person skills, project health) | `radar` |
| Gantt | Timeline (sprint schedule, milestones) | Custom via `bar` |
| Table | Structured data | HTML (not ECharts) |

---

## 4. Main Dashboard Layout

The Main Dashboard (`/`) is the COO's morning starting point. It provides a global operational overview across all projects.

### 4.1 Full Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◆ ChiefOps          🔍 Ask anything about your operations...   ⚡87  🔔 3 │
├──────────┬─────────────────────────────────────────────────────────────────┤
│          │                                                                 │
│  MAIN    │  ┌───────────────────────────────────────────────────────────┐ │
│  ────    │  │                  GLOBAL HEALTH SCORE                      │ │
│          │  │                                                           │ │
│ ▸ Main   │  │      ╭────────╮                                          │ │
│ Dashboard│  │      │        │     Overall: 87/100  ▲ +3 this week     │ │
│          │  │      │   87   │                                          │ │
│ PROJECTS │  │      │        │     Sprint Health    ████████░░  78     │ │
│ ● Alpha  │  │      ╰────────╯     Communication   █████████░  91     │ │
│ ◐ Beta   │  │                      Documentation   ████████░░  82     │ │
│ ● Gamma  │  │                      Team Capacity   ███████░░░  71     │ │
│ ○ Delta  │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│ ──────── │  ┌───────────────────────────────────────────────────────────┐ │
│ ⚙ Set.   │  │  ◆ AI BRIEFING                           Feb 8, 2026    │ │
│ ⬆ Ingest │  │  ───────────────────────────────────────────────────     │ │
│          │  │  Good morning. Here's your operational snapshot:          │ │
│          │  │                                                           │ │
│          │  │  ✅ Sprint velocity is up 12% across all projects.       │ │
│          │  │  ✅ Project Alpha remains on track for the March 15      │ │
│          │  │     deadline. Milestone 3 was completed yesterday.        │ │
│          │  │  ⚠️ Project Beta sprint is at risk — 3 tasks unassigned, │ │
│          │  │     estimated 40 hours of work with 2 days remaining.    │ │
│          │  │  🔴 Anil Gupta has been inactive for 5 days. Last seen  │ │
│          │  │     in Slack on Feb 3. He owns 4 open tasks in Beta.    │ │
│          │  │  📊 Weekly CEO report is ready for your review.          │ │
│          │  │                                                           │ │
│          │  │  💬 Ask me anything for more detail.                      │ │
│          │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│          │  PROJECT OVERVIEW                                               │
│          │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│          │  │  Alpha   │ │  Beta    │ │  Gamma   │ │  Delta   │         │
│          │  │          │ │          │ │          │ │          │         │
│          │  │  ✅ 87%  │ │  ⚠️ 52%  │ │  ✅ 91%  │ │  🔴 28%  │         │
│          │  │  On Track│ │  At Risk │ │  On Track│ │  Behind  │         │
│          │  │          │ │          │ │          │ │          │         │
│          │  │ 12 tasks │ │ 8 tasks  │ │ 5 tasks  │ │ 15 tasks │         │
│          │  │ 3 people │ │ 4 people │ │ 2 people │ │ 6 people │         │
│          │  │ Mar 15   │ │ Feb 28   │ │ Done     │ │ Apr 1    │         │
│          │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│          │                                                                 │
│          │  ┌──────────────────────────┐ ┌─────────────────────────────┐ │
│          │  │  TEAM OVERVIEW           │ │  ACTIVITY FEED              │ │
│          │  │  ─────────────────────── │ │  ─────────────────────────  │ │
│          │  │                          │ │                             │ │
│          │  │  ●  Active      42       │ │  10:23  Raj committed 3    │ │
│          │  │  ◐  Quiet        8       │ │         files to Alpha     │ │
│          │  │  ○  Inactive     3       │ │  10:15  Sprint 23 started  │ │
│          │  │  ─────────────────────── │ │         for Beta           │ │
│          │  │  Total          53       │ │  09:58  Priya merged PR    │ │
│          │  │                          │ │         #142 in Gamma      │ │
│          │  │  Top Performer:          │ │  09:45  Weekly report      │ │
│          │  │  Priya (Output: 94)      │ │         generated          │ │
│          │  │                          │ │  09:30  3 new Slack msgs   │ │
│          │  │  Needs Attention:        │ │         flagged for review │ │
│          │  │  Anil (Inactive 5d)      │ │                             │ │
│          │  │  Rohit (Quiet 3d)        │ │  ─────────────────────────  │ │
│          │  │                          │ │  Show all activity →        │ │
│          │  └──────────────────────────┘ └─────────────────────────────┘ │
│          │                                                                 │
│          │  ┌───────────────────────────────────────────────────────────┐ │
│          │  │  UPCOMING DEADLINES                                      │ │
│          │  │  ───────────────────────────────────────────────────     │ │
│          │  │                                                           │ │
│          │  │  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░  Feb 28  Beta Sprint 23 ends         │ │
│          │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░  Mar 15  Alpha v1.0 release          │ │
│          │  │  ▓▓▓▓▓▓░░░░░░░░░░  Apr  1  Delta MVP deadline          │ │
│          │  │                                                           │ │
│          │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
└──────────┴─────────────────────────────────────────────────────────────────┘
```

### 4.2 Section Specifications

#### Global Health Score Card

| Property | Value |
|----------|-------|
| Position | Top of content area, full width |
| Height | ~160px |
| Layout | Circular gauge (left), sub-scores with progress bars (right) |
| Gauge | 120px diameter, color gradient (red 0-40, amber 40-70, green 70-100) |
| Sub-score bars | 200px wide, 8px height, rounded caps |
| Trend indicator | Arrow up/down with delta value, green for positive, red for negative |
| Background | White card, `--shadow-card` |

#### AI Briefing Card

| Property | Value |
|----------|-------|
| Position | Below health score, full width |
| Min height | 180px, expandable |
| Header | "AI Briefing" with diamond icon, date right-aligned |
| Content | Bulleted text with status icons (check, warning, red circle) |
| Typography | 15px body text, 1.6 line height for readability |
| Footer | Muted text "Ask me anything for more detail." as a clickable prompt |
| Background | White card with subtle left border (3px, `--color-accent`) |

#### Project Overview Cards

| Property | Value |
|----------|-------|
| Layout | Horizontal row, wrapping on smaller screens |
| Card width | 200px minimum, flex-grow |
| Card height | ~180px |
| Content | Project name (bold), health score with status icon, status label, task count, people count, deadline |
| Status styling | Background tint matching status color (10% opacity) |
| Hover | Elevate shadow, scale 1.01 |
| Click | Navigate to `/project/:id` |

#### Team Overview Panel

| Property | Value |
|----------|-------|
| Layout | Left half of bottom row (50% width) |
| Content | Active/Quiet/Inactive counts with colored dots, total, top performer, needs-attention list |
| Active dot | Green, 8px |
| Quiet dot | Amber, 8px |
| Inactive dot | Red, 8px |

#### Activity Feed Panel

| Property | Value |
|----------|-------|
| Layout | Right half of bottom row (50% width) |
| Content | Time-stamped activity entries, most recent first |
| Entry format | `HH:MM  Description` |
| Max visible | 8 entries, "Show all activity" link at bottom |
| Scroll | Internal scroll if needed |

#### Upcoming Deadlines Bar

| Property | Value |
|----------|-------|
| Layout | Full width, bottom of page |
| Visualization | Horizontal progress bars with date labels |
| Bar color | Gradient based on time remaining (green > 2 weeks, amber 1-2 weeks, red < 1 week) |
| Date label | Right-aligned, bold |
| Description | After date, regular weight |

---

## 5. Project Dashboard (Static) Layout

The Static Project Dashboard (`/project/:id`) is auto-generated from ingested data. The COO does not configure it — it shows a standardized view of every project.

### 5.1 Full Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◆ ChiefOps     🔍 Ask about Project Alpha...   Alpha ● On Track  ⚡87 🔔3 │
├──────────┬─────────────────────────────────────────────────────────────────┤
│          │                                                                 │
│  MAIN    │  ┌───────────────────────────────────────────────────────────┐ │
│  ────    │  │  PROJECT ALPHA                                            │ │
│          │  │  AI-powered Operations Assistant                          │ │
│ ▸ Main   │  │  ───────────────────────────────────────────────────     │ │
│ Dashboard│  │                                                           │ │
│          │  │  Status: ✅ On Track    Health: 87/100  ▲ +3             │ │
│ PROJECTS │  │  Sprint: 23 (Day 8/14)  Deadline: Mar 15, 2026           │ │
│ ▸ Alpha  │  │  Owner: Sarah K.        Team Size: 8                     │ │
│ ● Beta   │  │                                                           │ │
│ ● Gamma  │  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐     │ │
│ ○ Delta  │  │  │Tasks│ │Done │ │Vel. │ │Comm.│ │Docs │ │Risk │     │ │
│          │  │  │ 12  │ │ 78% │ │ 34  │ │ 91  │ │ 82  │ │ Low │     │ │
│ ──────── │  │  │total│ │comp.│ │pts  │ │score│ │score│ │level│     │ │
│ ⚙ Set.   │  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘     │ │
│ ⬆ Ingest │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│          │  ┌───────────────────────────────────────────────────────────┐ │
│          │  │  TIMELINE / GANTT                                         │ │
│          │  │  ───────────────────────────────────────────────────     │ │
│          │  │        Jan    │    Feb     │    Mar     │                 │ │
│          │  │  M1 ▓▓▓▓▓▓▓▓▓█                                          │ │
│          │  │  M2           ▓▓▓▓▓▓▓▓▓▓▓█                              │ │
│          │  │  M3                  ░░░░░░▓▓▓▓▓█                        │ │
│          │  │  M4                              ░░░░░░░░░░█             │ │
│          │  │  ─────────────────────────────────────────────           │ │
│          │  │  █ = Complete  ▓ = In Progress  ░ = Upcoming             │ │
│          │  │  Today: ──────────────|                                   │ │
│          │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│          │  ┌────────────────────────────┐ ┌──────────────────────────┐ │
│          │  │  PEOPLE                    │ │  TASK BREAKDOWN          │ │
│          │  │  ──────────────────────── │ │  ────────────────────── │ │
│          │  │                            │ │                          │ │
│          │  │  ┌──────┐  ┌──────┐       │ │  Done      ████████  9  │ │
│          │  │  │  RK  │  │  PS  │       │ │  In Prog   ███░░░░░  4  │ │
│          │  │  │ Raj K│  │Priya │       │ │  To Do     ██░░░░░░  3  │ │
│          │  │  │ Lead │  │Senior│       │ │  Blocked   █░░░░░░░  1  │ │
│          │  │  │ ⚡ 94 │  │ ⚡ 88 │       │ │                          │ │
│          │  │  └──────┘  └──────┘       │ │  ────────────────────── │ │
│          │  │  ┌──────┐  ┌──────┐       │ │  By Priority:            │ │
│          │  │  │  AG  │  │  VM  │       │ │  Critical   ██░░░  2    │ │
│          │  │  │Anil G│  │Vikas │       │ │  High       ████░  4    │ │
│          │  │  │Junior│  │ Mid  │       │ │  Medium     ██████ 7    │ │
│          │  │  │ ⚠  23│  │ ⚡ 76 │       │ │  Low        ████░  4    │ │
│          │  │  └──────┘  └──────┘       │ │                          │ │
│          │  │                            │ │  Unassigned: 2 tasks     │ │
│          │  │  ... +4 more              │ │                          │ │
│          │  └────────────────────────────┘ └──────────────────────────┘ │
│          │                                                                 │
│          │  ┌────────────────────────────┐ ┌──────────────────────────┐ │
│          │  │  RISK PANEL                │ │  TECH READINESS          │ │
│          │  │  ──────────────────────── │ │  ────────────────────── │ │
│          │  │                            │ │                          │ │
│          │  │  Overall Risk: LOW         │ │  ✅ CI/CD pipeline       │ │
│          │  │                            │ │  ✅ Test coverage > 60%  │ │
│          │  │  ⚠ Schedule Risk           │ │  ✅ Staging environment  │ │
│          │  │    Milestone 3 has 2 days  │ │  ⚠  Monitoring setup    │ │
│          │  │    of buffer remaining.    │ │  ✅ Security audit       │ │
│          │  │    3 tasks unassigned.     │ │  🔴 Load testing        │ │
│          │  │                            │ │  ✅ Documentation        │ │
│          │  │  ✅ Resource Risk           │ │  ⚠  Disaster recovery   │ │
│          │  │    Team capacity at 85%.   │ │                          │ │
│          │  │    No single points of     │ │  Score: 6/8 (75%)       │ │
│          │  │    failure detected.       │ │                          │ │
│          │  │                            │ │                          │ │
│          │  │  ✅ Communication Risk      │ │                          │ │
│          │  │    Active Slack channels,  │ │                          │ │
│          │  │    regular standups.       │ │                          │ │
│          │  └────────────────────────────┘ └──────────────────────────┘ │
│          │                                                                 │
└──────────┴─────────────────────────────────────────────────────────────────┘
```

### 5.2 Section Specifications

#### Project Header

| Property | Value |
|----------|-------|
| Position | Top of content area, full width |
| Height | ~200px |
| Layout | Project name + description (left), KPI row (bottom) |
| Project name | 24px, bold, `--color-text` |
| Description | 14px, `--color-muted` |
| Status badge | Pill shape, colored background (green/amber/red), white text |
| KPI row | 6 KPI cards in a horizontal flex row |
| KPI card | 100px wide, metric (24px bold), label (12px muted), border-right separator |

#### Timeline / Gantt Chart

| Property | Value |
|----------|-------|
| Position | Below header, full width |
| Height | 250px |
| Implementation | ECharts custom bar chart with horizontal bars |
| Milestones | One row per milestone, labeled left |
| Bar colors | Complete: `--color-primary`, In progress: `--color-accent`, Upcoming: `#E5E7EB` |
| Today line | Vertical dashed red line at current date |
| Interactivity | Hover shows milestone details, click opens detail in chat |

#### People Grid

| Property | Value |
|----------|-------|
| Position | Left half of the third row |
| Layout | Grid of `PersonCard` components, 2 columns |
| PersonCard height | 80px |
| Content | Initials avatar (colored circle), name, role, output score |
| Warning state | Amber border for quiet, red border for inactive |
| Overflow | "+N more" link if more than 6 people |

#### Task Breakdown

| Property | Value |
|----------|-------|
| Position | Right half of the third row |
| Layout | Two grouped horizontal bar charts |
| Group 1 | By status (Done, In Progress, To Do, Blocked) |
| Group 2 | By priority (Critical, High, Medium, Low) |
| Bar style | Filled portion with count label at right |
| Footer | "Unassigned: N tasks" in warning style if N > 0 |

#### Risk Panel

| Property | Value |
|----------|-------|
| Position | Left half of the fourth row |
| Layout | Overall risk badge (top), categorized risk entries (below) |
| Risk categories | Schedule, Resource, Communication, Technical (auto-detected) |
| Entry format | Status icon, risk name (bold), description text (normal) |
| Colors | Green for low, amber for medium, red for high |

#### Technical Readiness Checklist

| Property | Value |
|----------|-------|
| Position | Right half of the fourth row |
| Layout | Vertical checklist with status icons |
| Items | CI/CD, Test Coverage, Staging, Monitoring, Security, Load Testing, Docs, DR |
| Status icons | Green check (ready), amber warning (partial), red circle (not ready) |
| Score | Bottom summary "N/M (X%)" |

---

## 6. Project Dashboard (Custom) Layout

The Custom Dashboard (`/project/:id/custom`) is where the COO builds their own view through conversation. It starts empty and is populated entirely through natural language.

### 6.1 Empty State

```
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                                                                       │
│                                                                       │
│                          ┌─────────────┐                             │
│                          │   ◇   ◇     │                             │
│                          │     ◆       │                             │
│                          │   ◇   ◇     │                             │
│                          └─────────────┘                             │
│                                                                       │
│                Your custom dashboard is empty.                        │
│                                                                       │
│          Ask me to add charts and insights about this project.        │
│                                                                       │
│             Try: "Show me a burndown chart for this sprint"           │
│             Try: "Add a team activity heatmap"                        │
│             Try: "Track velocity over the last 6 sprints"            │
│                                                                       │
│                    ┌─────────────────────────────────┐               │
│                    │ 🔍 What would you like to see?   │               │
│                    └─────────────────────────────────┘               │
│                                                                       │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

**Empty state specifications:**

| Property | Value |
|----------|-------|
| Icon | Abstract chart/diamond illustration, `--color-muted` at 40% opacity |
| Heading | 20px, bold, `--color-text` |
| Subheading | 15px, `--color-muted` |
| Suggestions | 14px, `--color-accent`, clickable (auto-populates search bar) |
| CTA input | Centered search input, same styling as top bar search |

### 6.2 Populated State

```
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐ │
│  │ 📊 Sprint Burndown       │  │ 📈 Velocity Trend (6 Sprints)    │ │
│  │ ─────────────────────── │  │ ──────────────────────────────  │ │
│  │                          │  │                                  │ │
│  │    ╲                     │  │         ╱╲                       │ │
│  │     ╲  ╱╲               │  │    ╱╲  ╱  ╲  ╱╲                │ │
│  │      ╲╱  ╲              │  │   ╱  ╲╱    ╲╱  ╲               │ │
│  │           ╲             │  │  ╱                ╲              │ │
│  │            ╲            │  │ ╱                                │ │
│  │                          │  │                                  │ │
│  │  Day 1  ...  Day 14     │  │ S18  S19  S20  S21  S22  S23   │ │
│  └──────────────────────────┘  └──────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐ │
│  │ 🔥 Team Activity Heatmap │  │ 📋 Task Distribution             │ │
│  │ ─────────────────────── │  │ ──────────────────────────────  │ │
│  │                          │  │                                  │ │
│  │     M  T  W  T  F       │  │  Raj    ████████░░ 8            │ │
│  │ Raj ▓▓ ▓▓ ▓  ▓▓ ▓▓     │  │  Priya  ███████░░░ 7            │ │
│  │ Pri ▓▓ ▓  ▓▓ ▓▓ ▓      │  │  Vikas  █████░░░░░ 5            │ │
│  │ Vik ▓  ▓▓ ▓  ▓  ▓▓     │  │  Anil   ██░░░░░░░░ 2            │ │
│  │ Ani ░  ░  ░  ░  ░      │  │                                  │ │
│  │                          │  │  ⚠ Anil has 2 tasks, inactive  │ │
│  └──────────────────────────┘  └──────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ 📝 Key Insights (AI-Generated)                                   │ │
│  │ ────────────────────────────────────────────────────────────    │ │
│  │                                                                  │ │
│  │  Sprint 23 is 57% through the timeline and 78% complete on      │ │
│  │  story points. The team is ahead of the ideal burndown line.    │ │
│  │                                                                  │ │
│  │  Raj and Priya are carrying 65% of the workload. Consider       │ │
│  │  redistributing Anil's tasks to Vikas.                          │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 6.3 Widget Grid System

| Property | Value |
|----------|-------|
| Grid columns | 12 |
| Column gap | 16px |
| Row gap | 16px |
| Padding (outer) | 24px |
| Widget sizes | Small: 4 cols, Medium: 6 cols, Large: 12 cols |
| Default chart height | Small: 250px, Medium: 300px, Large: 200px |
| Min widget height | 200px |
| Max widgets per page | 12 (soft limit, AI will suggest creating a new view) |

### 6.4 Widget Frame Component

Every widget on the custom dashboard is wrapped in a `WidgetFrame`:

```
┌──────────────────────────────────────────────┐
│  📊 Widget Title                       [···] │  ← Title bar with menu
│  ──────────────────────────────────────────  │
│                                              │
│              (Widget content)                │
│                                              │
│                                              │
│  ──────────────────────────────────────────  │
│  Last updated: 2 hours ago                   │  ← Footer (optional)
└──────────────────────────────────────────────┘
```

**Widget frame specifications:**

| Property | Value |
|----------|-------|
| Border | `1px solid #E5E7EB` |
| Border radius | 12px |
| Background | `#FFFFFF` |
| Shadow | `--shadow-card` |
| Title bar height | 44px |
| Title font | 14px, semi-bold, `--color-text` |
| Title icon | Widget type icon (chart, table, text, etc.) |
| Menu button (`[...]`) | Opens dropdown: "Remove", "Refresh", "Resize" |
| Footer | 12px, `--color-muted`, optional |
| Hover | Shadow elevates to `--shadow-elevated` |

**No drag-and-drop or manual resize handles.** The AI manages widget placement and sizing. If the COO wants to rearrange, they say: "Move the burndown chart to the top" or "Make the heatmap larger."

---

## 7. Report Preview Layout

The Report Preview page (`/project/:id/report/:reportId`) provides a document-like view of generated reports with a conversation panel for NL-driven editing.

### 7.1 Full Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◆ ChiefOps     🔍 Ask about this report...     Alpha Report    ⚡87 🔔 3  │
├──────────┬──────────────────────────────────┬──────────────────────────────┤
│          │                                    │                            │
│  MAIN    │  ┌────────────────────────────┐   │ 💬 Report Editor           │
│  ────    │  │  ┌──────────────────────┐  │   │ ──────────────────────    │
│          │  │  │                      │  │   │                            │
│ ▸ Main   │  │  │  📄 WEEKLY OPS REPORT│  │   │  This report was auto-    │
│ Dashboard│  │  │     Project Alpha    │  │   │  generated from your      │
│          │  │  │     Feb 3-8, 2026    │  │   │  latest data. You can     │
│ PROJECTS │  │  │                      │  │   │  ask me to edit any       │
│ ▸ Alpha  │  │  │  Executive Summary   │  │   │  section.                 │
│ ● Beta   │  │  │  ─────────────────  │  │   │                            │
│ ● Gamma  │  │  │  Project Alpha is   │  │   │         ┌──────────────┐  │
│ ○ Delta  │  │  │  on track for the   │  │   │         │ Rewrite the  │  │
│          │  │  │  March 15 deadline.  │  │   │         │ executive    │  │
│ ──────── │  │  │  Sprint velocity    │  │   │         │ summary to   │  │
│ ⚙ Set.   │  │  │  increased 12%...   │  │   │         │ be more      │  │
│ ⬆ Ingest │  │  │                      │  │   │         │ concise.     │  │
│          │  │  │  Health Score        │  │   │         └──────────────┘  │
│          │  │  │  ┌────────────┐     │  │   │                            │
│          │  │  │  │  87 / 100  │     │  │   │  ┌──────────────────────┐ │
│          │  │  │  │  ▲ +3      │     │  │   │  │ Done. I've shortened │ │
│          │  │  │  └────────────┘     │  │   │  │ the executive summary│ │
│          │  │  │                      │  │   │  │ from 120 words to 45.│ │
│          │  │  │  Team Performance   │  │   │  │ The key metrics are  │ │
│          │  │  │  ─────────────────  │  │   │  │ preserved.           │ │
│          │  │  │                      │  │   │  │                      │ │
│          │  │  │  ┌────────────────┐ │  │   │  │ ┌────────┐┌────────┐│ │
│          │  │  │  │ Velocity Chart │ │  │   │  │ │ Accept ││ Reject ││ │
│          │  │  │  │  ╱╲  ╱╲      │ │  │   │  │ └────────┘└────────┘│ │
│          │  │  │  │ ╱  ╲╱  ╲     │ │  │   │  └──────────────────────┘ │
│          │  │  │  └────────────────┘ │  │   │                            │
│          │  │  │                      │  │   │                            │
│          │  │  │  --- page break --- │  │   │                            │
│          │  │  │                      │  │   │                            │
│          │  │  │  Risk Assessment    │  │   │                            │
│          │  │  │  ─────────────────  │  │   │                            │
│          │  │  │  ...                │  │   │  ┌──────────────────────┐ │
│          │  │  │                      │  │   │  │ Type a message... ➤ │ │
│          │  │  └──────────────────────┘  │   │  └──────────────────────┘ │
│          │  │                              │   │                            │
│          │  │  ┌────────────────────────┐ │   │                            │
│          │  │  │ 📥 Export PDF  📋 Copy │ │   │                            │
│          │  │  └────────────────────────┘ │   │                            │
│          │  └────────────────────────────┘   │                            │
│          │                                    │                            │
└──────────┴──────────────────────────────────┴──────────────────────────────┘
```

### 7.2 Section Specifications

#### Report Content Panel (Left, 65%)

| Property | Value |
|----------|-------|
| Width | 65% of content area |
| Layout | Centered document with page styling |
| Document width | 680px max (within the 65% panel) |
| Background | Light gray (`#F0F2F5`) behind the document |
| Page background | White with subtle shadow (paper effect) |
| Page padding | 48px horizontal, 56px vertical |
| Page breaks | Visible dashed line with "Page N" label |
| Charts | Live interactive ECharts (not static images) |
| Font | 15px body, 1.7 line height for readability |
| Headings | Hierarchical sizing (H1: 24px, H2: 20px, H3: 16px) |
| Scroll | Vertical scroll of the full document |

#### Report Editor / Conversation Panel (Right, 35%)

| Property | Value |
|----------|-------|
| Width | 35% of content area |
| Background | `#FFFFFF` |
| Border | Left border `1px solid #E5E7EB` |
| Layout | Same as Chat Sidebar but integrated (not overlaid) |
| Initial message | System message explaining the report was auto-generated |
| Edit flow | COO requests change in chat, AI proposes edit with Accept/Reject buttons |
| Accept button | Green, updates the report live |
| Reject button | Gray, keeps original text |

#### Export Bar

| Property | Value |
|----------|-------|
| Position | Bottom of report panel, sticky |
| Height | 56px |
| Buttons | "Export PDF" (primary, filled), "Copy to Clipboard" (secondary, outlined) |
| Background | White with top border |

### 7.3 Report Editing Flow

1. COO views auto-generated report
2. COO types in conversation panel: "Make the executive summary shorter"
3. AI generates revised text, shows in chat with diff highlighting
4. Chat message includes "Accept" and "Reject" buttons
5. If accepted: report content updates live with a subtle highlight animation on the changed section
6. If rejected: original text preserved, AI asks for further guidance
7. Multiple edits can be made before exporting

---

## 8. Data Ingestion Page

The Data Ingestion page (`/ingest`) is one of only two pages in ChiefOps that uses traditional form UI elements. This is intentional — file upload is inherently a form-based interaction.

### 8.1 Full Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◆ ChiefOps          🔍 Ask anything about your operations...   ⚡87 🔔 3  │
├──────────┬─────────────────────────────────────────────────────────────────┤
│          │                                                                 │
│  MAIN    │  DATA INGESTION                                                │
│  ────    │  Import your operational data from Slack, Jira, and Drive.     │
│          │                                                                 │
│ ▸ Main   │  ┌───────────────────────────────────────────────────────────┐ │
│ Dashboard│  │                                                           │ │
│          │  │  ┌───────────────────────────────────────────────────┐   │ │
│ PROJECTS │  │  │                                                   │   │ │
│ ● Alpha  │  │  │                                                   │   │ │
│ ◐ Beta   │  │  │          ⬆                                       │   │ │
│ ● Gamma  │  │  │                                                   │   │ │
│ ○ Delta  │  │  │    Drag and drop files here                      │   │ │
│          │  │  │    or click to browse                             │   │ │
│ ──────── │  │  │                                                   │   │ │
│ ⚙ Set.   │  │  │    Supported: .zip (Slack), .csv (Jira),        │   │ │
│ ⬆ Ingest │  │  │    folders (Google Drive)                        │   │ │
│          │  │  │                                                   │   │ │
│          │  │  └───────────────────────────────────────────────────┘   │ │
│          │  │                                                           │ │
│          │  │  File Type:  [Slack ZIP Export ▾]                         │ │
│          │  │  Project:    [Project Alpha    ▾]                         │ │
│          │  │                                                           │ │
│          │  │            [ Upload & Process ]                           │ │
│          │  │                                                           │ │
│          │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│          │  ACTIVE PROCESSING                                              │
│          │  ┌───────────────────────────────────────────────────────────┐ │
│          │  │  📄 slack-export-feb2026.zip         Project Alpha       │ │
│          │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░  67%  Processing... │ │
│          │  │  Step: Parsing channels (23/34)                          │ │
│          │  │                                                           │ │
│          │  │  📄 jira-export.csv                  Project Beta        │ │
│          │  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  100%  ✅ Complete   │ │
│          │  │  Processed: 89 tasks, 12 epics, 245 comments            │ │
│          │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
│          │  INGESTION HISTORY                                              │
│          │  ┌───────────────────────────────────────────────────────────┐ │
│          │  │  Date         File                  Project   Status     │ │
│          │  │  ─────────────────────────────────────────────────────── │ │
│          │  │  Feb 8        slack-export.zip       Alpha    ✅ Done    │ │
│          │  │               342 messages, 14 docs                      │ │
│          │  │  Feb 7        jira-export.csv        Beta     ✅ Done    │ │
│          │  │               89 tasks, 245 comments                     │ │
│          │  │  Feb 5        drive-folder            Alpha    ✅ Done    │ │
│          │  │               23 documents, 8 sheets                     │ │
│          │  │  Feb 3        slack-export.zip       Gamma    ⚠ Partial │ │
│          │  │               156 messages (3 files skipped)             │ │
│          │  └───────────────────────────────────────────────────────────┘ │
│          │                                                                 │
└──────────┴─────────────────────────────────────────────────────────────────┘
```

### 8.2 Section Specifications

#### Drop Zone

| Property | Value |
|----------|-------|
| Height | 240px |
| Border | `2px dashed #D1D5DB`, border-radius 16px |
| Background | `#FAFBFC` |
| Hover / drag-over | Border color `--color-accent`, background `#F0FDFA` |
| Icon | Upload arrow, 48px, `--color-muted` |
| Primary text | 16px, semi-bold, `--color-text` |
| Secondary text | 14px, `--color-muted` |
| Click | Opens native file picker |
| Multi-file | Supported |

#### File Configuration

| Property | Value |
|----------|-------|
| File type selector | Dropdown with options: "Slack ZIP Export", "Jira CSV Export", "Google Drive Folder" |
| Project selector | Dropdown listing all projects + "Create New Project" option |
| Upload button | Primary button, `--color-primary` background, white text, 48px height |
| Disabled state | Button grayed out until file and project are selected |

#### Progress Display

| Property | Value |
|----------|-------|
| Progress bar | Full width, 8px height, rounded caps |
| Bar color | `--color-accent` (fill), `#E5E7EB` (track) |
| Percentage | Right of bar, 14px, bold |
| Step indicator | Below bar, 13px, `--color-muted` |
| Complete state | Green check, green text "Complete" |
| Summary | Below complete state, showing counts of processed items |

#### Ingestion History Table

| Property | Value |
|----------|-------|
| Layout | Full-width table |
| Columns | Date, File, Project, Status |
| Row height | 56px (two-line: file name + summary) |
| Status | Check (done), warning (partial), red X (failed) |
| Partial state | Amber with note about skipped items |
| Pagination | Show last 20 ingestions, "Show more" link |

---

## 9. Color Palette & Typography

### 9.1 Core Color Palette

```
Primary Colors
┌──────────────────────────────────────────────────┐
│  ██████  Primary       #1E3A5F  Deep blue        │
│  ██████  Primary Dark  #152C4A  Darker blue      │
│  ██████  Primary Light #2B5182  Lighter blue      │
│  ██████  Accent        #00BCD4  Bright teal/cyan │
│  ██████  Accent Dark   #0097A7  Darker teal      │
│  ██████  Accent Light  #4DD0E1  Lighter teal     │
└──────────────────────────────────────────────────┘

Semantic Colors
┌──────────────────────────────────────────────────┐
│  ██████  Success       #4CAF50  Green             │
│  ██████  Success BG    #E8F5E9  Light green bg   │
│  ██████  Warning       #FF9800  Amber             │
│  ██████  Warning BG    #FFF3E0  Light amber bg   │
│  ██████  Danger        #F44336  Red               │
│  ██████  Danger BG     #FFEBEE  Light red bg      │
│  ██████  Info          #2196F3  Blue              │
│  ██████  Info BG       #E3F2FD  Light blue bg    │
└──────────────────────────────────────────────────┘

Neutral Colors
┌──────────────────────────────────────────────────┐
│  ██████  Text          #1A1A2E  Dark gray-blue   │
│  ██████  Text Sec.     #4A5568  Medium dark gray  │
│  ██████  Muted         #6B7280  Medium gray       │
│  ██████  Placeholder   #9CA3AF  Light gray        │
│  ██████  Border        #E5E7EB  Very light gray   │
│  ██████  Background    #F5F7FA  Off-white         │
│  ██████  Card          #FFFFFF  Pure white         │
│  ██████  Surface       #FAFBFC  Near-white        │
└──────────────────────────────────────────────────┘
```

### 9.2 Status Colors

| Status | Primary Color | Background Tint | Text on Tint | Usage |
|--------|-------------|-----------------|-------------|-------|
| On Track | `#4CAF50` | `#E8F5E9` | `#2E7D32` | Project on track, healthy metrics |
| At Risk | `#FF9800` | `#FFF3E0` | `#E65100` | Warning conditions, approaching limits |
| Behind | `#F44336` | `#FFEBEE` | `#C62828` | Behind schedule, critical issues |
| Completed | `#1E3A5F` | `#EBF5FF` | `#1E3A5F` | Finished milestones, closed items |
| Inactive | `#9CA3AF` | `#F3F4F6` | `#6B7280` | Inactive people, stale data |

### 9.3 Typography

#### Font Families

| Usage | Font | Fallback Stack | Weight Range |
|-------|------|---------------|-------------|
| Headings | Inter | `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` | 600, 700 |
| Body | Inter | `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` | 400, 500 |
| Data/Code | JetBrains Mono | `'Fira Code', 'Consolas', monospace` | 400, 500 |

#### Type Scale

| Token | Size | Line Height | Weight | Usage |
|-------|------|-------------|--------|-------|
| `text-xs` | 11px | 16px | 400 | Timestamps, footnotes |
| `text-sm` | 13px | 20px | 400 | Secondary labels, metadata |
| `text-base` | 15px | 24px | 400 | Body text, descriptions |
| `text-lg` | 17px | 28px | 500 | Emphasized body, card titles |
| `text-xl` | 20px | 28px | 600 | Section headings |
| `text-2xl` | 24px | 32px | 700 | Page headings |
| `text-3xl` | 30px | 36px | 700 | Hero numbers (health score) |
| `text-4xl` | 36px | 40px | 700 | Dashboard primary metric |

#### Tailwind Configuration

```typescript
// tailwind.config.ts (relevant excerpt)
export default {
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      fontSize: {
        'xs':   ['0.6875rem', { lineHeight: '1rem' }],
        'sm':   ['0.8125rem', { lineHeight: '1.25rem' }],
        'base': ['0.9375rem', { lineHeight: '1.5rem' }],
        'lg':   ['1.0625rem', { lineHeight: '1.75rem' }],
        'xl':   ['1.25rem',   { lineHeight: '1.75rem' }],
        '2xl':  ['1.5rem',    { lineHeight: '2rem' }],
        '3xl':  ['1.875rem',  { lineHeight: '2.25rem' }],
        '4xl':  ['2.25rem',   { lineHeight: '2.5rem' }],
      },
    },
  },
};
```

### 9.4 Spacing Scale

All spacing follows a 4px base unit:

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight gaps (icon to text) |
| `space-2` | 8px | Element internal padding |
| `space-3` | 12px | Small gaps between elements |
| `space-4` | 16px | Standard gap, grid gap |
| `space-5` | 20px | Medium section padding |
| `space-6` | 24px | Card padding, page margin |
| `space-8` | 32px | Section separation |
| `space-10` | 40px | Large section separation |
| `space-12` | 48px | Page-level padding |
| `space-16` | 64px | Major section breaks |

### 9.5 Elevation (Shadows)

| Level | Value | Usage |
|-------|-------|-------|
| `shadow-none` | `none` | Flat elements |
| `shadow-xs` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift (buttons) |
| `shadow-card` | `0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)` | Cards at rest |
| `shadow-elevated` | `0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)` | Hover state, dropdowns |
| `shadow-modal` | `0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)` | Modals, overlays |

### 9.6 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius-sm` | 6px | Buttons, inputs, small cards |
| `radius-md` | 10px | Medium cards, panels |
| `radius-lg` | 16px | Large cards, modals |
| `radius-xl` | 24px | Pills, search bar |
| `radius-full` | 9999px | Avatars, circular badges |

---

## 10. Component Library

The following reusable components form the ChiefOps design system. Each component is a React component with TypeScript props and Tailwind styling.

### 10.1 HealthScoreBadge

A circular score indicator with a color gradient that communicates operational health at a glance.

```
Visual:
     ╭────────╮
     │        │
     │   87   │     ← Large: 120px diameter, score centered
     │        │
     ╰────────╯
       ▲ +3          ← Trend indicator below

     ╭────╮
     │ 87 │           ← Small: 40px diameter, score only
     ╰────╯
```

**Props:**
```typescript
interface HealthScoreBadgeProps {
  score: number;            // 0-100
  previousScore?: number;   // For trend calculation
  size: 'sm' | 'md' | 'lg'; // 40px | 80px | 120px
  showTrend?: boolean;      // Show up/down arrow with delta
  label?: string;           // Optional label below (e.g., "Sprint Health")
}
```

**Color logic:**
- 0-39: Red gradient (`#F44336` to `#FFCDD2`)
- 40-69: Amber gradient (`#FF9800` to `#FFE0B2`)
- 70-100: Green gradient (`#4CAF50` to `#C8E6C9`)

**Rendering:** Uses SVG with a circular arc (stroke-dasharray for partial fill) or an ECharts gauge for the large variant.

### 10.2 ProjectCard

A compact card displaying project status, health score, and key metrics. Used on the Main Dashboard's project overview row.

```
┌──────────────────┐
│  Alpha            │  ← Project name (bold)
│                   │
│  ✅  87%          │  ← Status icon + health score
│  On Track         │  ← Status label
│                   │
│  12 tasks         │  ← Task count
│  3 people         │  ← Team size
│  Mar 15           │  ← Deadline
└──────────────────┘
```

**Props:**
```typescript
interface ProjectCardProps {
  project: {
    id: string;
    name: string;
    healthScore: number;
    status: 'on_track' | 'at_risk' | 'behind' | 'completed';
    taskCount: number;
    teamSize: number;
    deadline: Date | null;
  };
  onClick: (projectId: string) => void;
}
```

**Styling:**
- Background: White
- Border: `1px solid #E5E7EB`
- Border-left: 4px solid status color (green/amber/red/blue)
- Border-radius: 12px
- Hover: Shadow elevates, slight scale (1.01)
- Transition: 200ms

### 10.3 PersonCard

A team member card showing identity, role, and key performance metrics. Used in the project People Grid.

```
┌──────────────────────────┐
│  ┌────┐                  │
│  │ RK │  Raj Kumar       │  ← Initials avatar + name
│  └────┘  Lead Engineer   │  ← Role
│          ────────────── │
│  Output: ⚡ 94           │  ← Output score with icon
│  Tasks: 8  │  Msgs: 142  │  ← Task and message counts
│  Last active: 2h ago     │  ← Recency
└──────────────────────────┘
```

**Props:**
```typescript
interface PersonCardProps {
  person: {
    id: string;
    name: string;
    role: string;
    outputScore: number;
    taskCount: number;
    messageCount: number;
    lastActive: Date;
    status: 'active' | 'quiet' | 'inactive';
  };
  compact?: boolean; // Smaller variant for inline use
}
```

**Avatar colors:** Generated deterministically from the person's name hash. Uses a palette of 12 distinct, accessible colors.

**Status indication:**
- Active: No special styling
- Quiet: Amber left border (3px)
- Inactive: Red left border (3px), muted text

### 10.4 AlertBanner

A notification banner for warnings, information, and errors. Appears at the top of the content area when there are alerts.

```
┌────────────────────────────────────────────────────────────────────┐
│  ⚠  Project Beta sprint is at risk — 3 tasks unassigned.    [✕]  │
└────────────────────────────────────────────────────────────────────┘
```

**Props:**
```typescript
interface AlertBannerProps {
  type: 'info' | 'warning' | 'error' | 'success';
  message: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  action?: {
    label: string;
    onClick: () => void;
  };
}
```

**Styling by type:**

| Type | Background | Border-left | Icon |
|------|-----------|------------|------|
| Info | `#E3F2FD` | `4px #2196F3` | Info circle |
| Warning | `#FFF3E0` | `4px #FF9800` | Warning triangle |
| Error | `#FFEBEE` | `4px #F44336` | Error circle |
| Success | `#E8F5E9` | `4px #4CAF50` | Check circle |

### 10.5 KpiCard

A metric display component with the current value, trend, and label.

```
┌───────────────────┐
│  Sprint Velocity   │  ← Label (muted, small)
│  34 pts            │  ← Value (large, bold)
│  ▲ +12%            │  ← Trend (colored)
└───────────────────┘
```

**Props:**
```typescript
interface KpiCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: {
    direction: 'up' | 'down' | 'flat';
    value: string; // e.g., "+12%", "-3 pts"
    isPositive: boolean; // Determines color (up can be bad for some metrics)
  };
  size?: 'sm' | 'md' | 'lg';
}
```

### 10.6 ChatBubble

Message bubble component for the conversational interface.

**Props:**
```typescript
interface ChatBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  richContent?: {
    type: 'chart' | 'table' | 'person_card' | 'report_link';
    data: unknown; // Type-specific data
  }[];
  actions?: {
    label: string;
    icon?: string;
    onClick: () => void;
  }[];
  isStreaming?: boolean; // Show typing indicator
}
```

**Streaming state:** When `isStreaming` is true, text appears character by character with a blinking cursor at the end. Rich content (charts, tables) renders only after the text is complete.

### 10.7 ChartContainer

A wrapper for ECharts instances that handles loading, error states, and responsive sizing.

```
Normal state:
┌──────────────────────────────┐
│  (ECharts instance)          │
│                              │
│  Chart content here          │
│                              │
└──────────────────────────────┘

Loading state:
┌──────────────────────────────┐
│                              │
│        ◌ Loading...          │
│                              │
└──────────────────────────────┘

Error state:
┌──────────────────────────────┐
│                              │
│   ⚠ Failed to load chart    │
│   [Retry]                    │
│                              │
└──────────────────────────────┘
```

**Props:**
```typescript
interface ChartContainerProps {
  option: EChartsOption;        // ECharts configuration object
  height?: number | string;     // Default: 300px
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  onChartReady?: (chart: ECharts) => void;
  responsive?: boolean;         // Default: true (auto-resize)
}
```

**Behavior:**
- Auto-resizes when container dimensions change (ResizeObserver)
- Shows a skeleton shimmer during loading
- Applies consistent theme (colors, fonts) from the global ECharts theme
- Handles empty data state with "No data available" message

### 10.8 SearchBar

The global natural language input component.

**Props:**
```typescript
interface SearchBarProps {
  placeholder?: string;
  onSubmit: (query: string) => void;
  recentQueries?: string[];
  suggestions?: string[];
  contextLabel?: string; // e.g., "Project Alpha"
  size?: 'default' | 'hero'; // Hero is for empty dashboard state
}
```

### 10.9 Sidebar

The left navigation sidebar.

**Props:**
```typescript
interface SidebarProps {
  projects: {
    id: string;
    name: string;
    healthScore: number;
    status: 'on_track' | 'at_risk' | 'behind' | 'completed';
  }[];
  activeProjectId?: string;
  activePage: 'dashboard' | 'project' | 'settings' | 'ingest';
  collapsed: boolean;
  onToggle: () => void;
  onProjectClick: (projectId: string) => void;
  onNavigate: (page: string) => void;
}
```

### 10.10 WidgetFrame

Container for dashboard widgets on the custom dashboard.

**Props:**
```typescript
interface WidgetFrameProps {
  title: string;
  icon: 'chart' | 'table' | 'text' | 'metric' | 'heatmap' | 'list';
  children: React.ReactNode;
  lastUpdated?: Date;
  onRemove?: () => void;
  onRefresh?: () => void;
  colSpan?: 4 | 6 | 8 | 12; // Grid column span
}
```

---

## 11. Responsive Design

### 11.1 Breakpoint Definitions

| Breakpoint | Width | Name | Priority |
|-----------|-------|------|----------|
| Desktop XL | 1440px+ | `xl` | Primary target |
| Desktop | 1024px - 1439px | `lg` | Full support |
| Tablet | 768px - 1023px | `md` | Secondary target |
| Mobile | < 768px | `sm` | Basic support (Step Zero deprioritized) |

### 11.2 Desktop XL (1440px+) — Primary

This is the target layout. All wireframes in this document represent this breakpoint.

| Element | Behavior |
|---------|----------|
| Sidebar | Always expanded (240px) |
| Top bar | Full width, search bar at 600px |
| Content | Flexible, multi-column widget grids |
| Chat sidebar | 400px overlay, does not compress content |
| Project cards | 4 per row |
| Report preview | 65%/35% split |

### 11.3 Desktop (1024px - 1439px)

| Element | Behavior |
|---------|----------|
| Sidebar | Collapsed by default (64px, icons only), expandable via hamburger |
| Top bar | Full width, search bar at 500px |
| Content | Flexible, widget grid adapts |
| Chat sidebar | 360px overlay |
| Project cards | 3 per row |
| Report preview | 60%/40% split |

### 11.4 Tablet (768px - 1023px)

| Element | Behavior |
|---------|----------|
| Sidebar | Hidden by default, slides in as overlay (hamburger toggle) |
| Top bar | Full width, search bar at 400px |
| Content | Single-column layout, widgets stack vertically |
| Chat sidebar | Full width overlay (replaces content view) |
| Project cards | 2 per row |
| Report preview | Tabbed view (toggle between report and chat) |
| Team/Activity panels | Stack vertically (full width each) |

### 11.5 Mobile (< 768px) — Deprioritized

Mobile is not a priority for Step Zero. The COO uses ChiefOps on a laptop or desktop. However, basic functionality must not break.

| Element | Behavior |
|---------|----------|
| Sidebar | Hidden, hamburger overlay |
| Top bar | Compact: search icon (expands on tap), health score hidden |
| Content | Single column, all cards full width |
| Chat | Full-screen takeover (conversation-only mode) |
| Project cards | 1 per row |
| Charts | Simplified (reduced interactivity) |
| Report preview | Report only (edit in separate chat view) |
| Data ingestion | Simplified drop zone, full-width form elements |

### 11.6 Tailwind Breakpoint Configuration

```typescript
// tailwind.config.ts (screens excerpt)
export default {
  theme: {
    screens: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1440px',
      '2xl': '1920px',
    },
  },
};
```

---

## 12. Animation & Transitions

All animations in ChiefOps are **subtle and professional**. They serve functional purposes: indicating state changes, guiding attention, and providing feedback. They are never playful, bouncy, or attention-grabbing.

### 12.1 Dashboard Load Sequence

When the dashboard loads, widgets appear in a staggered sequence:

```
Time 0ms:    Page background visible, skeleton shimmer on widget positions
Time 100ms:  Health Score card fades in (opacity 0→1, translateY 8px→0, 300ms)
Time 200ms:  AI Briefing card fades in (same animation)
Time 350ms:  Project cards fade in together (same animation)
Time 500ms:  Bottom panels fade in (same animation)
Time 700ms:  All content settled, skeletons removed
```

**CSS implementation:**
```css
@keyframes widget-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.widget-enter {
  animation: widget-enter 300ms ease-out forwards;
}

/* Stagger delays applied via inline styles or nth-child */
.widget-enter:nth-child(1) { animation-delay: 100ms; }
.widget-enter:nth-child(2) { animation-delay: 200ms; }
.widget-enter:nth-child(3) { animation-delay: 350ms; }
.widget-enter:nth-child(4) { animation-delay: 500ms; }
```

### 12.2 Chart Transitions

ECharts handles its own animation system. We configure:

| Property | Value | Purpose |
|----------|-------|---------|
| `animation` | `true` | Enable animations |
| `animationDuration` | `800` | Base duration for initial render |
| `animationDurationUpdate` | `500` | Duration for data updates |
| `animationEasing` | `'cubicInOut'` | Easing function |
| `animationEasingUpdate` | `'cubicInOut'` | Update easing |

When chart data updates (e.g., new ingestion), the chart smoothly transitions between old and new states. Bar charts animate height, line charts animate along the path, and pie charts animate slice angles.

### 12.3 Sidebar Transitions

| Transition | Duration | Easing | Property |
|-----------|----------|--------|----------|
| Collapse/expand | 300ms | `ease` | `width` |
| Item hover | 150ms | `ease` | `background-color` |
| Active indicator | 200ms | `ease` | `border-left`, `background-color` |

### 12.4 Chat Sidebar

| Transition | Duration | Easing | Property |
|-----------|----------|--------|----------|
| Open/close | 300ms | `cubic-bezier(0.4, 0, 0.2, 1)` | `transform: translateX` |
| Message appear | 200ms | `ease-out` | `opacity`, `transform: translateY(12px)` |
| Typing indicator | 1200ms | `steps(3)` | Dot animation (opacity cycle) |

### 12.5 Widget Add/Remove

| Transition | Duration | Easing | Property |
|-----------|----------|--------|----------|
| Widget add | 300ms | `ease-out` | `opacity: 0→1`, `transform: scale(0.95)→scale(1)` |
| Widget remove | 200ms | `ease-in` | `opacity: 1→0`, `transform: scale(1)→scale(0.95)` |
| Grid reflow | 400ms | `ease` | Layout shift (CSS Grid animation) |

### 12.6 Micro-interactions

| Element | Trigger | Animation |
|---------|---------|-----------|
| Button | Hover | Background color shift, 150ms |
| Button | Click | Scale 0.97 for 100ms, then back |
| Card | Hover | Shadow elevation, 200ms |
| Search bar | Focus | Width expand, border color, 200ms |
| Alert banner | Appear | Slide down from top, 250ms |
| Alert banner | Dismiss | Fade out + slide up, 200ms |
| Toggle switch | Toggle | Slide + color change, 200ms |
| Tooltip | Hover (300ms delay) | Fade in, 150ms |
| Inline response card | Appear | Slide down + fade in, 200ms |
| Inline response card | Dismiss | Fade out + slide up, 150ms |

### 12.7 Performance Guidelines

- All animations use `transform` and `opacity` only (GPU-accelerated, no layout thrash)
- Use `will-change` sparingly and only on elements that are about to animate
- Respect `prefers-reduced-motion`: when enabled, disable all non-essential animations
- Chart animations are the heaviest; if the page has more than 6 visible charts, reduce `animationDuration` to 400ms

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 13. Dark Mode (Future)

Dark mode is **planned but NOT implemented in Step Zero**. However, the design system is structured to make dark mode adoption trivial.

### 13.1 Approach

All color values are referenced via CSS custom properties (defined in `:root`). Dark mode will be implemented by defining an alternate set of values under a class or media query:

```css
/* Light mode (default) */
:root {
  --color-bg: #F5F7FA;
  --color-card: #FFFFFF;
  --color-text: #1A1A2E;
  --color-muted: #6B7280;
  --color-border: #E5E7EB;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
}

/* Dark mode (future) */
.dark {
  --color-bg: #0F172A;
  --color-card: #1E293B;
  --color-text: #F1F5F9;
  --color-muted: #94A3B8;
  --color-border: #334155;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2);
}
```

### 13.2 Implementation Checklist (For Future Phase)

- [ ] Define dark mode color tokens for all semantic colors
- [ ] Ensure all components reference CSS variables, not hardcoded hex values
- [ ] Test chart readability in dark mode (ECharts has a built-in dark theme)
- [ ] Update status colors for adequate contrast on dark backgrounds
- [ ] Add toggle in Settings page (and respect `prefers-color-scheme` media query)
- [ ] Test all shadow values (shadows need to be darker/different on dark backgrounds)
- [ ] Verify avatar and icon visibility
- [ ] Update Data Ingestion drop zone styling

### 13.3 Current Requirement

For Step Zero, every component must use CSS custom properties for its colors. No hardcoded hex values in component-level styles. This single requirement ensures dark mode can be added later by defining new variable values without touching any component code.

---

## 14. Accessibility

ChiefOps must be accessible to users with disabilities. The following requirements apply to Step Zero.

### 14.1 Keyboard Navigation

| Requirement | Implementation |
|------------|----------------|
| All interactive elements focusable | Tab order follows visual layout (top-to-bottom, left-to-right) |
| Focus visible indicator | 2px solid `--color-accent` outline with 2px offset (never hidden) |
| Sidebar navigation | Arrow keys to move between items, Enter to select |
| Search bar | `Cmd+K` / `Ctrl+K` to focus, `Escape` to blur |
| Chat sidebar | `Cmd+Shift+C` / `Ctrl+Shift+C` to toggle, `Tab` to move between messages |
| Chat input | `Enter` to send, `Shift+Enter` for newline |
| Dashboard widgets | `Tab` to move between widgets, `Enter` to interact |
| Inline response card | `Escape` to dismiss, `Tab` to reach follow-up input |
| Project cards | `Enter` or `Space` to navigate to project |
| Drop zone | `Enter` or `Space` to open file picker |

### 14.2 ARIA Labels and Roles

| Component | ARIA Implementation |
|-----------|---------------------|
| Search bar | `role="search"`, `aria-label="Search operations"`, `aria-expanded` for dropdown |
| Sidebar | `role="navigation"`, `aria-label="Main navigation"` |
| Project list | `role="list"`, each project `role="listitem"` |
| Chat sidebar | `role="complementary"`, `aria-label="Chat assistant"` |
| Chat messages | `role="log"`, `aria-live="polite"` for new messages |
| Health score | `role="meter"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`, `aria-label` |
| Charts | `role="img"`, `aria-label` with chart description, fallback table for screen readers |
| Alert banner | `role="alert"`, `aria-live="assertive"` for errors, `aria-live="polite"` for info |
| Progress bar | `role="progressbar"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"` |
| Widget frame | `role="region"`, `aria-label` with widget title |
| KPI cards | `aria-label` combining label, value, and trend (e.g., "Sprint Velocity: 34 points, up 12 percent") |
| Person cards | `aria-label` combining name, role, and status |

### 14.3 Color Contrast

All text must meet WCAG AA contrast requirements:

| Combination | Ratio Required | Compliance |
|------------|---------------|------------|
| `--color-text` on `--color-card` | 4.5:1 minimum | `#1A1A2E` on `#FFFFFF` = 16.1:1 (pass) |
| `--color-muted` on `--color-card` | 4.5:1 minimum | `#6B7280` on `#FFFFFF` = 5.0:1 (pass) |
| `--color-text` on `--color-bg` | 4.5:1 minimum | `#1A1A2E` on `#F5F7FA` = 14.3:1 (pass) |
| White on `--color-primary` | 4.5:1 minimum | `#FFFFFF` on `#1E3A5F` = 9.7:1 (pass) |
| Status colors on white | 3:1 minimum (large text) | All status colors verified |

**Important:** Status colors alone must never be the only indicator. Always pair with:
- Icons (checkmark, warning triangle, X circle)
- Text labels ("On Track", "At Risk", "Behind")
- Shape or position differences

### 14.4 Screen Reader Support

#### Chart Accessibility

Every ECharts chart must have a screen-reader-accessible fallback:

```html
<div role="img" aria-label="Sprint velocity trend showing increase from 28 to 34 points over the last 4 sprints">
  <!-- ECharts canvas renders here -->
  <table class="sr-only">
    <caption>Sprint Velocity Trend</caption>
    <thead>
      <tr><th>Sprint</th><th>Velocity (points)</th></tr>
    </thead>
    <tbody>
      <tr><td>Sprint 20</td><td>28</td></tr>
      <tr><td>Sprint 21</td><td>30</td></tr>
      <tr><td>Sprint 22</td><td>32</td></tr>
      <tr><td>Sprint 23</td><td>34</td></tr>
    </tbody>
  </table>
</div>
```

The `sr-only` class (visually hidden, screen-reader visible):

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

#### Dashboard Data

The AI Briefing section must be inside an `aria-live="polite"` region so screen readers announce updates when new briefings are generated.

Health scores use `role="meter"` with full value attributes so screen readers announce: "Overall health score: 87 out of 100."

#### Chat Interface

- New messages announced via `aria-live="polite"`
- Streaming responses announced once complete (not character by character)
- Rich content (charts, tables) announced with summary descriptions
- Action buttons within messages are keyboard-focusable and labeled

### 14.5 Focus Management

| Scenario | Focus Behavior |
|----------|---------------|
| Chat sidebar opens | Focus moves to chat input |
| Chat sidebar closes | Focus returns to the element that opened it |
| Inline response appears | Focus moves to the response card |
| Inline response dismissed | Focus returns to search bar |
| Modal dialog opens | Focus trapped within modal |
| Modal dialog closes | Focus returns to trigger element |
| Page navigation | Focus moves to main content heading |
| Alert banner appears | Focus moves to alert (if error), stays put (if info/warning) |

### 14.6 Testing Requirements

| Test Type | Tool | Standard |
|-----------|------|----------|
| Automated accessibility | axe-core (via @axe-core/react in dev) | Zero violations at AA level |
| Keyboard navigation | Manual testing | All interactions reachable via keyboard |
| Screen reader | VoiceOver (Mac) + NVDA (Windows) | All content readable, logical order |
| Color contrast | Chrome DevTools contrast checker | AA minimum on all text |
| Focus visibility | Manual testing | Focus ring visible on all interactive elements |

---

## 15. Settings Page Layout

The Settings page (`/settings`) is the second page with traditional form elements.

### 15.1 Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ◆ ChiefOps          🔍 Ask anything about your operations...   ⚡87 🔔 3  │
├──────────┬─────────────────────────────────────────────────────────────────┤
│          │                                                                 │
│  MAIN    │  SETTINGS                                                      │
│  ────    │                                                                 │
│          │  ┌─────────────┬──────────────────────────────────────────────┐│
│ ▸ Main   │  │             │                                              ││
│ Dashboard│  │  General    │  GENERAL                                     ││
│          │  │  Projects   │  ───────────────────────────────────────     ││
│ PROJECTS │  │  Appearance │                                              ││
│ ● Alpha  │  │  Data       │  Organization Name                           ││
│ ◐ Beta   │  │             │  ┌──────────────────────────────────────┐   ││
│ ● Gamma  │  │             │  │ YENSI Solutions                      │   ││
│ ○ Delta  │  │             │  └──────────────────────────────────────┘   ││
│          │  │             │                                              ││
│ ──────── │  │             │  Timezone                                    ││
│ ⚙ Set.   │  │             │  ┌──────────────────────────────────────┐   ││
│ ⬆ Ingest │  │             │  │ Asia/Kolkata (IST)               ▾ │   ││
│          │  │             │  └──────────────────────────────────────┘   ││
│          │  │             │                                              ││
│          │  │             │  Default Report Language                     ││
│          │  │             │  ┌──────────────────────────────────────┐   ││
│          │  │             │  │ English                            ▾ │   ││
│          │  │             │  └──────────────────────────────────────┘   ││
│          │  │             │                                              ││
│          │  │             │  AI Briefing Time                            ││
│          │  │             │  ┌──────────────────────────────────────┐   ││
│          │  │             │  │ 09:00 AM                              │   ││
│          │  │             │  └──────────────────────────────────────┘   ││
│          │  │             │                                              ││
│          │  │             │            [ Save Changes ]                  ││
│          │  │             │                                              ││
│          │  └─────────────┴──────────────────────────────────────────────┘│
│          │                                                                 │
└──────────┴─────────────────────────────────────────────────────────────────┘
```

### 15.2 Settings Sections

| Section | Contents |
|---------|----------|
| **General** | Organization name, timezone, language, AI briefing time |
| **Projects** | List of projects with edit/archive options, create new project button |
| **Appearance** | Logo upload (for reports), primary brand color picker, report template selection |
| **Data** | Data retention settings, export all data button, clear project data (with confirmation) |

### 15.3 Settings Form Specifications

| Element | Style |
|---------|-------|
| Text input | Height 40px, border `1px solid #D1D5DB`, radius 8px, padding 12px |
| Dropdown | Same as text input, with chevron icon right-aligned |
| Save button | Primary button, full width within form column |
| Section nav | Left tab list, 180px wide, vertical |
| Active tab | Background `#EBF5FF`, left border 3px `--color-primary` |

---

## 16. Loading States & Skeletons

Every component has a loading state to prevent layout shift and provide visual feedback.

### 16.1 Skeleton Shimmer

```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton {
  background: linear-gradient(
    90deg,
    #F3F4F6 25%,
    #E5E7EB 50%,
    #F3F4F6 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}
```

### 16.2 Component Loading States

| Component | Skeleton Shape |
|-----------|---------------|
| HealthScoreBadge | Gray circle |
| ProjectCard | Rectangle matching card dimensions |
| PersonCard | Rectangle with circle (avatar) + lines (text) |
| KpiCard | Rectangle with large block (value) + small block (label) |
| ChartContainer | Rectangle with centered spinner |
| AI Briefing | Rectangle with 4 horizontal lines of varying width |
| Activity Feed | 5 stacked line skeletons |
| Search bar results | 3 stacked line skeletons in dropdown |

### 16.3 Error States

| State | Display |
|-------|---------|
| API error (recoverable) | Red alert banner at top with retry action |
| Chart data error | "Unable to load chart" message in chart container with retry button |
| Chat error | Error message in chat bubble with "Retry" option |
| Ingestion failure | Red status in progress display with error detail expandable |
| Network offline | Full-width yellow banner: "You're offline. Some features may be unavailable." |

---

## 17. ECharts Theme Configuration

A custom ECharts theme ensures all charts are visually consistent with the ChiefOps design system.

### 17.1 Theme Definition

```typescript
// src/config/echartsTheme.ts
export const chiefopsTheme = {
  color: [
    '#1E3A5F',  // Primary blue
    '#00BCD4',  // Accent teal
    '#4CAF50',  // Green
    '#FF9800',  // Amber
    '#F44336',  // Red
    '#9C27B0',  // Purple
    '#2196F3',  // Light blue
    '#795548',  // Brown
    '#607D8B',  // Blue-gray
    '#E91E63',  // Pink
  ],
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, -apple-system, sans-serif',
    color: '#1A1A2E',
  },
  title: {
    textStyle: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontWeight: 600,
      fontSize: 16,
      color: '#1A1A2E',
    },
    subtextStyle: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: 13,
      color: '#6B7280',
    },
  },
  line: {
    smooth: true,
    symbolSize: 6,
    lineStyle: {
      width: 2.5,
    },
  },
  bar: {
    barMaxWidth: 40,
    itemStyle: {
      borderRadius: [4, 4, 0, 0],
    },
  },
  pie: {
    itemStyle: {
      borderColor: '#FFFFFF',
      borderWidth: 2,
    },
  },
  gauge: {
    axisLine: {
      lineStyle: {
        color: [
          [0.4, '#F44336'],
          [0.7, '#FF9800'],
          [1, '#4CAF50'],
        ],
      },
    },
  },
  tooltip: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderWidth: 1,
    textStyle: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: 13,
      color: '#1A1A2E',
    },
    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);',
  },
  legend: {
    textStyle: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: 12,
      color: '#6B7280',
    },
  },
  categoryAxis: {
    axisLine: {
      lineStyle: { color: '#E5E7EB' },
    },
    axisTick: {
      lineStyle: { color: '#E5E7EB' },
    },
    axisLabel: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: 12,
      color: '#6B7280',
    },
    splitLine: {
      lineStyle: { color: '#F3F4F6' },
    },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      fontFamily: 'Inter, -apple-system, sans-serif',
      fontSize: 12,
      color: '#6B7280',
    },
    splitLine: {
      lineStyle: { color: '#F3F4F6' },
    },
  },
};
```

### 17.2 Theme Registration

```typescript
// In app initialization
import * as echarts from 'echarts/core';
import { chiefopsTheme } from './config/echartsTheme';

echarts.registerTheme('chiefops', chiefopsTheme);

// Usage in components
<ReactECharts option={chartOption} theme="chiefops" />
```

---

## 18. Design Handoff Checklist

This section serves as a reference for the frontend engineering team when implementing the designs.

### 18.1 Implementation Priority Order

| Priority | Page/Component | Complexity | Dependency |
|----------|---------------|-----------|------------|
| P0 | SearchBar + Quick Query | High | Core NL interaction |
| P0 | Sidebar | Medium | Page structure |
| P0 | Top Bar | Medium | Page structure |
| P0 | Main Dashboard (layout + static content) | High | Sidebar, Top Bar |
| P0 | HealthScoreBadge | Low | ECharts gauge |
| P0 | ProjectCard | Low | None |
| P0 | KpiCard | Low | None |
| P1 | Chat Sidebar | High | WebSocket, AI Layer |
| P1 | ChatBubble (text) | Medium | Chat Sidebar |
| P1 | ChartContainer | Medium | ECharts theme |
| P1 | Project Dashboard (Static) | High | All card components |
| P1 | AlertBanner | Low | None |
| P1 | PersonCard | Low | None |
| P2 | ChatBubble (rich content) | High | ChartContainer, AI Layer |
| P2 | Project Dashboard (Custom) | High | WidgetFrame, Chat |
| P2 | WidgetFrame | Medium | None |
| P2 | Data Ingestion page | Medium | File upload API |
| P3 | Report Preview | High | Report generation API |
| P3 | Settings page | Medium | Settings API |
| P3 | Loading skeletons | Low | None |
| P3 | Animations & transitions | Low | None |

### 18.2 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State management | Zustand | Lightweight, TypeScript-friendly, no boilerplate |
| CSS approach | Tailwind CSS with CSS custom properties | Utility-first + theming flexibility |
| Chart library | Apache ECharts (echarts-for-react) | Rich chart types, animation support, custom themes |
| Routing | React Router v6 | Standard, well-supported |
| HTTP client | Axios | Interceptors for auth, error handling |
| Form handling | Controlled components (no form library) | Only 2 form pages, library is overkill |
| Responsive | Tailwind breakpoints | Built-in, consistent |
| Animation | CSS transitions + ECharts built-in | No animation library needed for subtle effects |

### 18.3 File Structure (UI Layer)

```
src/
  components/
    common/
      AlertBanner.tsx
      ChartContainer.tsx
      HealthScoreBadge.tsx
      KpiCard.tsx
      SearchBar.tsx
      WidgetFrame.tsx
    chat/
      ChatSidebar.tsx
      ChatBubble.tsx
      ChatInput.tsx
      InlineResponseCard.tsx
    dashboard/
      ProjectCard.tsx
      PersonCard.tsx
      AiBriefing.tsx
      ActivityFeed.tsx
      DeadlineBar.tsx
    layout/
      AppLayout.tsx
      Sidebar.tsx
      TopBar.tsx
    report/
      ReportViewer.tsx
      ReportEditor.tsx
    ingestion/
      DropZone.tsx
      IngestionProgress.tsx
      IngestionHistory.tsx
    settings/
      SettingsForm.tsx
      SettingsTabs.tsx
  pages/
    MainDashboard.tsx
    ProjectDashboardStatic.tsx
    ProjectDashboardCustom.tsx
    ReportPreview.tsx
    DataIngestion.tsx
    Settings.tsx
  config/
    echartsTheme.ts
    tailwind.theme.ts
  styles/
    globals.css          /* CSS custom properties, reset, sr-only */
    animations.css       /* Keyframes and animation classes */
  hooks/
    useChat.ts
    useSearchBar.ts
    useWidgetGrid.ts
  stores/
    chatStore.ts         /* Zustand store for chat state */
    dashboardStore.ts    /* Zustand store for widget layout */
    uiStore.ts           /* Zustand store for sidebar, theme */
```

---

*This document is the authoritative UI/UX design reference for ChiefOps Step Zero. All frontend implementation should conform to the layouts, specifications, and interaction patterns defined here. Deviations require discussion with the design lead.*
