# Memory System: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | **Memory System** | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | [People Intelligence](./09-PEOPLE-INTELLIGENCE.md) | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

The memory system is the most critical architectural component of ChiefOps. It is what transforms a stateless AI question-answering tool into a persistent, context-aware operations advisor that learns, remembers, and builds upon every conversation, every Slack thread, every Jira update, and every correction the COO makes — across days, weeks, and months.

This document describes the complete design: why progressive memory compaction exists, how the three-layer architecture works, how conversations from all sources flow into per-project streams, how compaction is triggered and executed, and how context is assembled for every AI request.

---

## 1. Why Progressive Memory Compaction

### The Problem

Most AI chat applications use a simple sliding window: send the last N conversation turns to the model. When N = 10, here is what happens:

```
Turn 1:  COO: "Who is Raj?"
Turn 2:  AI:  "Raj appears to be a junior developer on Project Alpha."
Turn 3:  COO: "No, Raj is the Lead Architect. He's been with us 4 years."
Turn 4:  AI:  "Understood. Raj is the Lead Architect on Project Alpha..."
Turn 5:  COO: "What's the sprint velocity?"
Turn 6:  AI:  "Based on the last 3 sprints..."
Turn 7:  COO: "Show me Priya's tasks."
Turn 8:  AI:  "Priya is working on PROJ-142, PROJ-155..."
Turn 9:  COO: "Priya handles backend, not frontend. Update that."
Turn 10: AI:  "Noted. Priya is a backend engineer..."
Turn 11: COO: "How is Project Alpha doing?"   <-- Turn 1-4 just fell off the window
Turn 12: AI:  "Raj is a junior developer..."   <-- WRONG. The correction is gone.
```

The critical correction from Turn 3 ("Raj is the Lead Architect") is lost the moment it leaves the sliding window. This is unacceptable for an operations advisor. The COO made a correction once and expects the system to remember it permanently.

The problem compounds with Slack data. The COO's team discusses important decisions in Slack every day. A key architectural decision made in Slack three weeks ago is just as important as something said five minutes ago. Without a memory system, all of that context evaporates.

### The Solution: Summary + Last 10

Instead of sending only the last 10 raw turns, we build a **progressive summary of ALL previous conversations** (including Slack messages), compact it over time, and send it alongside the last 10 turns:

```
What the AI receives for every request:
┌──────────────────────────────────────────────────────────────┐
│  HARD FACTS (always present, never compacted)                │
│  "Raj = Lead Architect (corrected by COO, Jan 15)"           │
│  "Priya = Backend Engineer (corrected by COO, Jan 15)"       │
│  "Alpha deadline = March 20"                                 │
│  "Board meeting every last Friday"                           │
│  ... (~300-500 tokens)                                       │
├──────────────────────────────────────────────────────────────┤
│  COMPACTED SUMMARY (rolling, progressively shrinks)          │
│  "Over the past 3 weeks, the COO has focused on Alpha's      │
│  sprint velocity and team allocation. Key discussions:        │
│  sprint velocity trending down (3.2 → 2.8), Priya            │
│  reassigned to backend services, concern about March          │
│  deadline feasibility. Slack activity shows team discussing   │
│  database migration risks and API rate limiting issues.       │
│  The architect proposed a phased rollout..."                  │
│  ... (~1500-2000 tokens)                                     │
├──────────────────────────────────────────────────────────────┤
│  LAST 10 RAW TURNS (full detail, verbatim)                   │
│  Turn N-9: COO: "What about the API integration?"            │
│  Turn N-8: AI:  "The API integration has 3 open tasks..."    │
│  ...                                                         │
│  Turn N-0: COO: "How is Project Alpha doing?"                │
│  ... (~3000-5000 tokens)                                     │
└──────────────────────────────────────────────────────────────┘
```

The AI now has:
- **Long-term memory** — the compacted summary of ALL past conversations (including Slack) and hard facts that are never lost
- **Immediate context** — the last 10 raw turns with full detail for conversational continuity

Even if the COO corrected Raj's role 200 conversations ago, that fact lives in Hard Facts and is included in every single prompt. Even if a Slack discussion about database migration risks happened three weeks ago, it is captured in the compacted summary or retrievable via Citex semantic search.

### Why This Matters for an Operations Advisor

ChiefOps is not a chatbot. It is a persistent advisor that builds institutional knowledge over time. The memory system is what makes this possible:

| Without Memory System | With Memory System |
|-----------------------|--------------------|
| Forgets corrections after 10 turns | Remembers corrections permanently |
| Cannot reference old Slack discussions | Slack context lives in project summaries |
| Each session starts from scratch | Each session builds on all prior context |
| COO must repeat context constantly | COO establishes facts once, system remembers |
| AI contradicts itself across sessions | AI maintains consistent understanding |
| Loses nuance over time | Preserves key details while compacting less important ones |

---

## 2. Three-Layer Memory Architecture

The memory system is organized into three distinct layers, each with different retention characteristics, storage strategies, and roles in the AI prompt.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   THREE-LAYER MEMORY ARCHITECTURE                   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 1: HARD FACTS                                         │  │
│  │  ─────────────────                                           │  │
│  │  Extracted corrections, decisions, established truths         │  │
│  │  NEVER compacted. Always in every prompt.                    │  │
│  │  Storage: MongoDB conversation_facts collection              │  │
│  │  Growth: Slow and predictable (~5-20 new facts per week)     │  │
│  │  Token budget: ~300-500 tokens                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 2: COMPACTED SUMMARY                                  │  │
│  │  ─────────────────────────                                   │  │
│  │  Rolling summary of ALL past conversations + Slack           │  │
│  │  Progressively compressed. Capped at ~1500-2000 tokens.      │  │
│  │  Storage: MongoDB compacted_summaries + Citex (indexed)      │  │
│  │  Older summaries archived but searchable via Citex           │  │
│  │  Token budget: ~1500-2000 tokens                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 3: RECENT TURNS                                       │  │
│  │  ─────────────────────                                       │  │
│  │  Last 10 COO conversation turns, verbatim                    │  │
│  │  Full messages + full AI responses                           │  │
│  │  Plus relevant recent Slack highlights (if applicable)       │  │
│  │  Storage: MongoDB conversation_turns collection              │  │
│  │  Token budget: ~3000-5000 tokens                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  BACKUP: CITEX SEMANTIC INDEX                                │  │
│  │  ──────────────────────────                                  │  │
│  │  All session summaries, compacted summaries, and Slack       │  │
│  │  summaries are indexed in Citex for semantic retrieval.      │  │
│  │  When the COO asks about something from weeks ago,           │  │
│  │  Citex retrieves the relevant archived summaries.            │  │
│  │  This is NOT a memory layer — it is the safety net.          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Hard Facts (Never Compacted)

Hard facts are the bedrock of the memory system. They are explicit, verified pieces of information that the AI must always know.

**What qualifies as a hard fact:**

| Category | Examples |
|----------|----------|
| Role corrections | "Raj = Lead Architect (corrected by COO, Jan 15)" |
| Assignment corrections | "Priya handles backend, not frontend (corrected by COO, Jan 15)" |
| Deadlines and dates | "Alpha deadline = March 20", "Board meeting every last Friday" |
| Key decisions | "Decided to use PostgreSQL instead of MySQL (from Slack, Jan 12)" |
| Organizational facts | "Engineering team = 12 people", "VP of Eng reports to COO" |
| Project facts | "Alpha uses microservices architecture", "Beta is client-facing" |
| Preferences | "COO prefers executive summaries under 200 words" |
| Blockers/dependencies | "Alpha blocked on vendor API access since Jan 10" |

**Storage schema (MongoDB `conversation_facts` collection):**

```json
{
  "_id": "fact_a1b2c3d4",
  "project_id": "project_alpha",       // null for global facts
  "stream_type": "project",            // "project" | "global"
  "fact_text": "Raj is the Lead Architect on Project Alpha",
  "category": "role_correction",
  "source": {
    "type": "coo_conversation",         // "coo_conversation" | "slack" | "jira"
    "turn_id": "turn_x9y8z7",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "extracted_by": "ai_fact_extraction",
  "confidence": 1.0,                    // 1.0 for COO corrections, 0.7-0.9 for AI-extracted
  "supersedes": "fact_e5f6g7h8",        // ID of the fact this replaces (if correction)
  "active": true,                        // false if superseded
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**How facts are extracted:**

1. **From COO corrections** (confidence = 1.0): When the COO says "No, Raj is the Lead Architect", the AI response is analyzed for factual corrections. Any correction explicitly made by the COO is stored with full confidence.

2. **From COO statements** (confidence = 0.95): When the COO states something factual: "The board meeting is every last Friday." This is not a correction, but an established truth.

3. **From Slack messages** (confidence = 0.7-0.9): When the AI processes Slack data and identifies key decisions or assignments: "In #project-alpha, the team decided to switch to PostgreSQL (Jan 12)."

4. **From Jira data** (confidence = 0.8): Task assignments, sprint dates, and status changes from Jira CSV data.

**Fact deduplication and supersession:**

When a new fact contradicts an existing fact, the old fact is marked `active: false` and the new fact's `supersedes` field points to the old fact ID. Only active facts are included in the prompt. The supersession chain is preserved for auditability.

```
Fact 1 (active: false): "Raj = Junior Developer"     [from Jira data, Jan 5]
Fact 2 (active: true):  "Raj = Lead Architect"        [COO correction, Jan 15, supersedes Fact 1]
```

**Token budget:** Hard facts are formatted as a concise bulleted list. With typical usage (50-100 active facts per project, 20-30 global facts), this stays within ~300-500 tokens.

### Layer 2: Compacted Summary (Progressively Shrinks)

The compacted summary is a rolling, AI-generated narrative that captures the essence of ALL past conversations and Slack activity for a project. It is the system's "institutional memory."

**What the compacted summary captures:**

- Topics discussed and their outcomes
- Insights surfaced by the AI
- Concerns raised by the COO
- Patterns observed across conversations
- Key Slack discussion themes and conclusions
- Progress milestones and status changes
- Recurring issues or blockers
- Context about team dynamics and communication patterns

**Storage schema (MongoDB `compacted_summaries` collection):**

```json
{
  "_id": "summary_p1q2r3s4",
  "project_id": "project_alpha",        // null for global stream
  "stream_type": "project",             // "project" | "global"
  "summary_type": "active",             // "active" | "session" | "weekly" | "monthly" | "archived"
  "summary_text": "Over the past 3 weeks, the COO has focused on Alpha's sprint velocity and team allocation. Key discussions include: sprint velocity trending down from 3.2 to 2.8 story points per day, Priya reassigned from frontend to backend services (COO correction, Jan 15), concern about March 20 deadline feasibility given current velocity. Slack activity shows the engineering team discussing database migration risks, with the architect proposing a phased rollout approach. The API rate limiting issue was resolved by implementing exponential backoff. The COO requested a comparison of Alpha vs Beta timelines. The team identified 3 unassigned critical-path tasks that need owners by next sprint.",
  "token_count": 1450,
  "covers_period": {
    "from": "2025-01-01T00:00:00Z",
    "to": "2025-01-21T23:59:59Z"
  },
  "sources_included": {
    "coo_turns": 47,
    "slack_messages": 312,
    "jira_updates": 28,
    "session_summaries_merged": 6
  },
  "compaction_generation": 3,            // How many times this has been compacted
  "parent_summary_ids": ["summary_a1", "summary_a2", "summary_a3"],
  "citex_document_id": "citex_doc_x1y2", // Reference to Citex index for semantic search
  "created_at": "2025-01-21T00:00:00Z",
  "updated_at": "2025-01-21T00:00:00Z"
}
```

**How compaction works (high level):**

Session summaries are generated after every ~20 COO turns or at the end of a session. These session summaries are merged into the active compacted summary. When the active summary exceeds ~2000 tokens, the AI compacts it: merging older content into more concise form while preserving recent detail. The detailed compaction pipeline is described in Section 7.

**Citex integration:** Every compacted summary (active, session, weekly, monthly, archived) is indexed in Citex with its full text and metadata. When the COO asks about something that was discussed weeks ago, the Citex semantic search retrieves relevant archived summaries, even if they have been compacted out of the active summary. See [Citex Integration](./05-CITEX-INTEGRATION.md).

**Token budget:** The active compacted summary is capped at ~1500-2000 tokens. This is enforced by the compaction pipeline — when the active summary exceeds 2000 tokens, a compaction cycle is triggered.

### Layer 3: Recent Turns (Raw, Full Detail)

The most recent conversation turns are kept verbatim. This provides the AI with full conversational context for the current interaction — exact wording, nuance, tone, and complete AI responses.

**What is stored:**

- The last 10 COO conversation turns (COO message + AI response = 1 turn)
- Each turn stored with full text, no summarization, no truncation
- Relevant recent Slack highlights may be appended if they are contextually important to the current conversation

**Storage schema (MongoDB `conversation_turns` collection):**

```json
{
  "_id": "turn_t1u2v3w4",
  "project_id": "project_alpha",
  "stream_type": "project",
  "turn_number": 47,
  "source": "coo_conversation",          // "coo_conversation" | "slack_highlight"
  "page_context": "project_dashboard",    // Where the COO was when they sent this
  "coo_message": {
    "text": "How is the sprint velocity trending?",
    "timestamp": "2025-01-21T14:30:00Z"
  },
  "ai_response": {
    "text": "Based on the last 3 sprints, velocity has been trending down...",
    "timestamp": "2025-01-21T14:30:02Z",
    "tokens_used": 450,
    "sources_cited": ["jira_sprint_data", "slack_channel_engineering"]
  },
  "facts_extracted": ["fact_a1b2c3d4"],   // Any facts extracted from this turn
  "included_in_session_summary": "summary_p1q2r3s4",
  "created_at": "2025-01-21T14:30:00Z"
}
```

**Why 10 turns:** Ten turns provide sufficient conversational continuity for multi-step discussions while staying within a predictable token budget. The COO can have a back-and-forth about a topic (5-7 exchanges), change topics, and still have the earlier discussion visible. Combined with the compacted summary that captures everything before these 10 turns, no context is lost.

**Token budget:** ~3000-5000 tokens for 10 turns. This varies based on the length of COO messages and AI responses. If a particular conversation has unusually long responses, the effective turn count may be reduced to stay within budget.

---

## 3. Per-Project Streams

Every project in ChiefOps has exactly ONE memory stream. This stream combines ALL sources of information about that project into a single, unified context. The COO does not need to think about where information came from — the stream merges it all.

### Stream Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROJECT ALPHA MEMORY STREAM                      │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  HARD FACTS (Layer 1)                                        │  │
│  │                                                               │  │
│  │  From COO conversations:                                      │  │
│  │  - "Raj = Lead Architect" (COO correction, Jan 15)            │  │
│  │  - "Priya handles backend, not frontend" (COO, Jan 15)        │  │
│  │                                                               │  │
│  │  From Slack:                                                  │  │
│  │  - "Team decided to use PostgreSQL" (#project-alpha, Jan 12)  │  │
│  │  - "API vendor confirmed March 1 access" (DM, Jan 18)        │  │
│  │                                                               │  │
│  │  From Jira:                                                   │  │
│  │  - "Sprint 12 deadline = Jan 25" (Jira sprint data)           │  │
│  │  - "ALPHA-142 blocked on vendor API" (Jira status)            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  ACTIVE COMPACTED SUMMARY (Layer 2)                          │  │
│  │                                                               │  │
│  │  "Over the past 3 weeks: COO focused on sprint velocity      │  │
│  │  (trending down 3.2→2.8) and team allocation. Slack shows     │  │
│  │  active database migration discussion — architect proposed    │  │
│  │  phased rollout, team agreed Jan 14. API rate limiting        │  │
│  │  resolved with exponential backoff. 3 critical-path tasks     │  │
│  │  unassigned. COO concerned about March 20 feasibility..."     │  │
│  │                                                               │  │
│  │  [Merges: COO sessions + Slack weekly summaries + Jira        │  │
│  │   status changes into one unified narrative]                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  RECENT TURNS (Layer 3)                                      │  │
│  │                                                               │  │
│  │  Turn 43: COO: "Show me the sprint burndown"                  │  │
│  │           AI:  "Here's the Sprint 12 burndown..."             │  │
│  │  Turn 44: COO: "Why is velocity dropping?"                    │  │
│  │           AI:  "Three factors: 1) Priya's reassignment..."    │  │
│  │  ...                                                          │  │
│  │  Turn 47: COO: "How is the sprint velocity trending?"         │  │
│  │           AI:  "Based on the last 3 sprints..."               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### How Sources Flow Into Project Streams

All conversation sources are assigned to projects and flow into the appropriate project stream:

```
                    ┌──────────────────────┐
                    │   INCOMING SOURCES    │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
    │  Slack Messages │  │ COO Turns  │  │ Jira Tasks  │
    │  (data dumps)   │  │ (from UI)  │  │ (CSV data)  │
    └─────────┬──────┘  └─────┬──────┘  └──────┬──────┘
              │                │                │
              ▼                ▼                ▼
    ┌──────────────────────────────────────────────────┐
    │           PROJECT ASSIGNMENT ENGINE               │
    │                                                  │
    │  Slack:  Channel name → project mapping          │
    │  COO:    Page context → project routing           │
    │  Jira:   Project key → project mapping           │
    │  (AI assists for ambiguous cases)                │
    └──────────────────────┬───────────────────────────┘
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼───┐  ┌────▼────┐  ┌────▼──────┐
    │ Alpha Stream │  │  Beta   │  │  Global   │
    │              │  │ Stream  │  │  Stream   │
    └─────────────┘  └─────────┘  └───────────┘
```

### Slack Message Assignment

Slack messages are assigned to project streams based on these rules, applied in order:

| Rule | Source | Assignment | Confidence |
|------|--------|------------|------------|
| 1. Channel name match | `#project-alpha` | Alpha stream | High |
| 2. Channel name match | `#project-beta` | Beta stream | High |
| 3. Jira key mention | Message contains "ALPHA-142" | Alpha stream | High |
| 4. Project name mention | Message mentions "Alpha" or "Project Alpha" | Alpha stream | Medium |
| 5. Topic-based split | `#engineering` message about "database migration for Alpha" | Alpha stream | Medium (AI-assisted) |
| 6. Cross-project | `#engineering` message about general architecture | Global stream | Medium |
| 7. General channels | `#general`, `#random`, `#announcements` | Global stream (unless project-specific) | Low |
| 8. DMs mentioning projects | DM: "Hey, about the Alpha deadline..." | Alpha stream | Medium (AI-assisted) |

**AI-assisted routing for ambiguous messages:**

For channels like `#engineering`, `#design`, or `#general` that discuss multiple projects, the AI analyzes message content to determine project assignment:

```
Input:  "#engineering message: 'The API rate limiting fix is deployed.
         @raj can you verify it works with the Alpha integration?'"

AI analysis:
  - Mentions "Alpha integration" → relates to Project Alpha
  - Mentions @raj → known Alpha team member
  - Topic: API rate limiting → matches Alpha context

Assignment: Alpha stream (confidence: 0.85)
```

Messages that cannot be confidently assigned to a project go to the Global stream.

### DM Routing

Direct messages mentioning projects are routed to the relevant project streams:

```
DM between Raj and Priya:
  "Hey, about the Alpha deadline — I think we need
   2 more sprints for the database migration."

AI analysis:
  - Mentions "Alpha deadline" → Project Alpha
  - Mentions "database migration" → matches Alpha context
  - Both Raj and Priya are Alpha team members

Assignment: Alpha stream
```

DMs that are purely social or do not mention any project go to the Global stream. DMs that mention multiple projects may be split: the message is assigned to the most relevant project, with a cross-reference note added to other mentioned projects.

---

## 4. Global Stream

The Global stream is a cross-project memory stream that captures organizational-level context. It stores facts, summaries, and recent turns that are not specific to any single project.

### What Goes in the Global Stream

| Category | Examples |
|----------|----------|
| Organizational preferences | "COO prefers Gantt charts for timeline visualization" |
| Company-wide events | "Board meeting every last Friday", "All-hands on first Monday" |
| Cross-project observations | "Engineering velocity is down across all projects this month" |
| General Slack discussions | Messages from `#general`, `#announcements`, `#random` |
| COO preferences | "COO prefers executive summaries under 200 words" |
| Company facts | "Company has 80 employees", "Series B funding closed Dec 2024" |
| Tool preferences | "Team uses Figma for design, not Sketch" |
| Cross-project conversations | COO asks on main dashboard: "How are things overall?" |

### How Global Facts Are Used

When the AI answers a question about any project, it loads BOTH the project stream AND global stream facts. This ensures that organizational context applies universally:

```
Assembling context for "How is Project Alpha doing?":

  1. Project Alpha hard facts     → "Raj = Lead Architect", "Alpha deadline = March 20"
  2. Global hard facts            → "Board meeting every last Friday", "COO prefers Gantt charts"
  3. Project Alpha active summary → "Sprint velocity trending down, 3 unassigned tasks..."
  4. Project Alpha last 10 turns  → [verbatim recent conversation]
  5. Citex retrieved chunks       → [semantically relevant data]
```

The global fact "COO prefers Gantt charts" influences how the AI presents timeline information, even though it was established in a conversation about a different project.

### Global Stream Structure

The Global stream has the same three-layer structure as project streams:

```json
{
  "stream_id": "stream_global",
  "stream_type": "global",
  "facts": [
    { "fact_text": "COO prefers Gantt charts", "source": "coo_conversation", ... },
    { "fact_text": "Board meeting every last Friday", "source": "coo_conversation", ... },
    { "fact_text": "Company uses Figma for design", "source": "slack", ... }
  ],
  "active_summary": "The COO has been focused on cross-project resource allocation...",
  "recent_turns": [
    { "coo_message": "How are things overall?", "ai_response": "...", ... }
  ]
}
```

---

## 5. Conversation Routing

When the COO sends a message, the system must determine which project stream to route it to. This routing is deterministic when possible and AI-assisted when ambiguous.

### Routing Rules

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONVERSATION ROUTING                            │
│                                                                     │
│  COO sends a message                                                │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────┐                                            │
│  │ Where is the COO?   │                                            │
│  └──────────┬──────────┘                                            │
│             │                                                       │
│   ┌─────────┼────────────┬──────────────────┐                       │
│   │         │            │                  │                       │
│   ▼         ▼            ▼                  ▼                       │
│ Project   Project      Main              Custom                     │
│ Dashboard Dashboard   Dashboard          Dashboard                  │
│ (Static)  (Custom)                       (for project X)            │
│   │         │            │                  │                       │
│   ▼         ▼            ▼                  ▼                       │
│ Route to  Route to     AI detects        Route to                   │
│ THIS      THIS         project from      project X                  │
│ project's project's    query content     stream                     │
│ stream    stream           │                                        │
│                            ▼                                        │
│                  ┌───────────────────┐                               │
│                  │ Query mentions    │                               │
│                  │ specific project? │                               │
│                  └────────┬──────────┘                               │
│                     Yes   │   No                                    │
│                   ┌───────┴───────┐                                  │
│                   ▼               ▼                                  │
│               Route to        Route to                              │
│               that project's  Global                                │
│               stream          stream                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Routing by Page Context

| Page | Routing Behavior |
|------|-----------------|
| **Project Dashboard (Static)** | Always routes to that project's stream. Query "How's the sprint?" is implicitly about this project. |
| **Project Dashboard (Custom)** | Always routes to that project's stream. Same as static. |
| **Main Dashboard** | AI analyzes the query to determine project. "How's Alpha doing?" routes to Alpha. "How are things overall?" routes to Global. |
| **Custom Dashboard (for project X)** | Routes to project X's stream. |

### Cross-Project Queries

When the COO asks a question that spans multiple projects from the main dashboard:

```
COO: "Compare Alpha and Beta progress"
```

The system:
1. Detects this is a cross-project query
2. Loads facts and summaries from BOTH Alpha and Beta streams
3. Loads Global stream facts
4. Routes the conversation turn to the Global stream (since it is not specific to one project)
5. The AI response draws from both project contexts

### Turn Metadata

Every conversation turn is stored with full routing metadata:

```json
{
  "turn_id": "turn_t1u2v3w4",
  "project_id": "project_alpha",
  "page_context": "project_dashboard_custom",
  "timestamp": "2025-01-21T14:30:00Z",
  "source": "coo_conversation",
  "routing_method": "page_context",      // "page_context" | "ai_detection" | "explicit_mention"
  "routing_confidence": 1.0
}
```

---

## 6. Slack Message Processing

Slack messages receive the SAME memory treatment as COO conversations. They are not second-class citizens — they are a primary source of organizational intelligence. The processing pipeline ensures Slack context is fully integrated into project memory streams.

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                   SLACK MESSAGE PROCESSING PIPELINE                  │
│                                                                     │
│  Step 1: PARSE AND ASSIGN TO PROJECTS                               │
│  ─────────────────────────────────────                               │
│  Input:  Raw Slack export (JSON per channel per day)                 │
│  Action: Parse messages, identify channels, resolve user IDs         │
│  Output: Structured messages with channel, author, timestamp, text   │
│  Assign: Each message → project stream (using rules from Section 3)  │
│                                                                     │
│       │                                                             │
│       ▼                                                             │
│                                                                     │
│  Step 2: PER-PROJECT SUMMARIZATION                                  │
│  ────────────────────────────────                                    │
│  Input:  All Slack messages for Project Alpha from this data dump    │
│  Action: AI generates a summary of Slack activity for this project   │
│  Output: Slack summary (~500-800 tokens per project)                 │
│  Prompt: "Summarize the following Slack conversations about Project  │
│           Alpha. Focus on: decisions made, blockers raised, task     │
│           assignments, technical discussions, timeline mentions,     │
│           and team dynamics."                                        │
│                                                                     │
│       │                                                             │
│       ▼                                                             │
│                                                                     │
│  Step 3: FACT EXTRACTION                                            │
│  ───────────────────────                                             │
│  Input:  Slack messages + AI-generated summary                       │
│  Action: AI identifies hard facts from Slack conversations           │
│  Output: Facts stored in conversation_facts collection               │
│  Prompt: "From these Slack conversations, extract:                   │
│           - Explicit decisions ('We decided to use X')               │
│           - Task assignments ('Hey Raj, can you pick up PROJ-142?')  │
│           - Deadlines mentioned ('We need this by March 1')          │
│           - Blockers ('Waiting on vendor API access')                │
│           - Role clarifications ('Priya is handling the backend')    │
│           Return each as a structured fact with confidence score."   │
│                                                                     │
│       │                                                             │
│       ▼                                                             │
│                                                                     │
│  Step 4: STORE RAW + SUMMARY + FACTS                                │
│  ───────────────────────────────────                                 │
│  Raw messages:   → MongoDB slack_messages collection                 │
│  Slack summary:  → MongoDB compacted_summaries (type: "slack_weekly")│
│  Extracted facts:→ MongoDB conversation_facts collection             │
│  All of above:   → Indexed in Citex for semantic search              │
│                                                                     │
│       │                                                             │
│       ▼                                                             │
│                                                                     │
│  Step 5: MERGE INTO PROJECT STREAM                                  │
│  ────────────────────────────────                                    │
│  Input:  New Slack summary + new Slack facts + existing project      │
│          stream (active summary + existing facts)                    │
│  Action: AI merges the new Slack summary into the project's active   │
│          compacted summary, creating a unified narrative that        │
│          combines COO conversation context and Slack context         │
│  Output: Updated active compacted summary for the project            │
│                                                                     │
│  Merge prompt: "Here is the current project summary and new Slack    │
│  activity. Merge the Slack highlights into the project summary,      │
│  maintaining chronological flow and highlighting where Slack          │
│  context adds to or clarifies the COO's previous discussions."       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Example: Slack Processing for Project Alpha

**Raw Slack messages from `#project-alpha` (January 12-18):**

```
[Jan 12, 10:15] @raj: The PostgreSQL migration is looking good.
                       Benchmarks show 3x improvement on read queries.
[Jan 12, 10:22] @priya: Nice! I'll update the connection pooling config
                         for the backend services.
[Jan 12, 14:00] @raj: @anil can you pick up ALPHA-142? It's the API
                       rate limiting fix.
[Jan 12, 14:05] @anil: Sure, I'll start on it tomorrow.
[Jan 14, 09:30] @raj: Team, I think we should do a phased rollout
                       for the DB migration. Stage 1: read replicas.
                       Stage 2: write migration.
[Jan 14, 09:45] @priya: Agreed. Less risk that way.
[Jan 14, 09:50] @deepak: +1 for phased approach.
[Jan 18, 11:00] @anil: ALPHA-142 is done. Implemented exponential
                        backoff. PR is up for review.
```

**Step 2 output — AI-generated Slack summary:**

> "Project Alpha Slack activity (Jan 12-18): The PostgreSQL migration showed strong benchmark results (3x read query improvement). Raj proposed a phased rollout — Stage 1: read replicas, Stage 2: write migration — and the team agreed (Priya, Deepak). Anil picked up ALPHA-142 (API rate limiting fix) and completed it with an exponential backoff implementation. Priya is updating connection pooling for backend services to support the new database."

**Step 3 output — Extracted facts:**

```json
[
  {
    "fact_text": "Team decided on phased rollout for DB migration (Stage 1: read replicas, Stage 2: write migration)",
    "category": "technical_decision",
    "source": { "type": "slack", "channel": "#project-alpha", "timestamp": "2025-01-14T09:30:00Z" },
    "confidence": 0.9
  },
  {
    "fact_text": "Anil assigned to ALPHA-142 (API rate limiting fix)",
    "category": "task_assignment",
    "source": { "type": "slack", "channel": "#project-alpha", "timestamp": "2025-01-12T14:00:00Z" },
    "confidence": 0.85
  },
  {
    "fact_text": "ALPHA-142 completed — implemented exponential backoff",
    "category": "task_completion",
    "source": { "type": "slack", "channel": "#project-alpha", "timestamp": "2025-01-18T11:00:00Z" },
    "confidence": 0.9
  },
  {
    "fact_text": "PostgreSQL migration benchmarks show 3x read query improvement",
    "category": "technical_metric",
    "source": { "type": "slack", "channel": "#project-alpha", "timestamp": "2025-01-12T10:15:00Z" },
    "confidence": 0.85
  }
]
```

**Step 5 output — Merged into project active summary:**

The AI takes the existing active summary (from previous COO conversations) and the new Slack summary, and produces a unified narrative:

> "Over the past 3 weeks, the COO has focused on Alpha's sprint velocity (trending down 3.2 to 2.8) and team allocation. **Slack activity confirms the engineering team made progress on key fronts:** the PostgreSQL migration benchmarks show 3x read query improvement, and the team agreed on a phased rollout (Stage 1: read replicas, Stage 2: write migration). Anil completed the API rate limiting fix (ALPHA-142) with exponential backoff. Priya is updating connection pooling for backend services. The COO corrected Raj's role to Lead Architect and Priya's focus to backend. 3 critical-path tasks remain unassigned. The COO expressed concern about March 20 deadline feasibility given current velocity."

This unified summary means the AI can answer questions like "What did the team decide about the database migration?" by drawing on Slack context that is now part of the project memory, without the COO having to ask specifically about Slack.

---

## 7. Compaction Pipeline

The compaction pipeline is the mechanism that keeps the memory system bounded in size while preserving maximum information. It operates at multiple timescales, from per-turn fact extraction to monthly deep compaction.

### 7.1 After Each Conversation Turn: Fact Extraction

**When:** Immediately after the AI generates a response to a COO message.

**What happens:**

1. The AI response is analyzed for new facts (corrections, decisions, established truths).
2. Any identified facts are stored in Layer 1 (Hard Facts).
3. If a fact contradicts an existing fact, the old fact is superseded.

**Implementation:**

```
Input to fact extraction:
  - COO message: "No, Raj is the Lead Architect. He's been with us 4 years."
  - AI response: "Understood. I've updated Raj's role to Lead Architect on Project Alpha."

Fact extraction prompt:
  "Analyze this conversation turn. Extract any facts that should be
   permanently remembered. Focus on:
   - Corrections to previously known information
   - New decisions or established truths
   - Role assignments or changes
   - Deadlines or date commitments
   - Preferences or standing instructions

   For each fact, indicate:
   - The fact text (concise, standalone)
   - Category (role_correction, deadline, decision, preference, etc.)
   - Confidence (1.0 for explicit COO statements, 0.7-0.9 for inferred)
   - Whether it supersedes a known fact (and which one)"

Output:
  {
    "facts": [
      {
        "fact_text": "Raj is the Lead Architect on Project Alpha (4 years tenure)",
        "category": "role_correction",
        "confidence": 1.0,
        "supersedes_description": "Any prior role assignment for Raj on Alpha"
      }
    ]
  }
```

This happens on every turn. Most turns produce zero new facts. Correction turns produce 1-3 facts. The overhead is minimal — a single fast AI call with a small prompt.

### 7.2 After Each Session (or Every ~20 Turns): Session Summary

**When:** After ~20 COO conversation turns within a project stream, or when the COO ends a session (closes browser, navigates away).

**What happens:**

1. The AI generates a session summary covering the turns since the last session summary.
2. The session summary captures: key discussions, insights, concerns, outcomes.
3. The session summary is stored in `compacted_summaries` with `summary_type: "session"`.
4. The session summary is indexed in Citex.
5. The session summary is merged into the project's active compacted summary.

**Session summary generation prompt:**

```
"You are summarizing a conversation session between the COO and
 ChiefOps about Project Alpha.

 Here are the turns from this session:
 [Turn 28 through Turn 47]

 Generate a concise summary (300-500 tokens) covering:
 - What topics were discussed
 - What insights or analysis were provided
 - What concerns the COO raised
 - What decisions or corrections were made
 - What was the overall outcome of this session

 Write in third person: 'The COO asked about...'
 'The system identified that...'

 Do NOT include facts that are already stored as hard facts.
 Focus on the narrative and context, not the raw data."
```

**Example session summary:**

> "Session 5 (Jan 21): The COO reviewed sprint velocity trends and expressed concern about the declining rate (3.2 to 2.8). The system identified three contributing factors: Priya's reassignment to backend, two team members on PTO, and an increase in bug tickets. The COO asked about timeline feasibility for March 20 — the system flagged that at current velocity, 3 of 14 remaining tasks are at risk. The COO requested a comparison with Project Beta's timeline and asked the system to generate a board report draft for next Friday."

### 7.3 Progressive Compaction (Weekly or When Summary Exceeds ~2000 Tokens)

**When:** The active compacted summary exceeds ~2000 tokens, OR at the end of each week (if the project was active that week).

**What happens:**

1. The AI takes the current active summary (which has been growing as session summaries were merged in).
2. The AI compacts it: older content is compressed more aggressively, recent content retains more detail.
3. Hard facts are NOT re-included in the summary (they are already in Layer 1).
4. The pre-compaction summary is archived and indexed in Citex.
5. The new, shorter summary replaces the active summary.

**Compaction prompt:**

```
"You are compacting a project memory summary. The summary has grown
 too large and needs to be compressed while preserving key information.

 Current active summary (2400 tokens):
 [full active summary text]

 Hard facts already stored separately (do not repeat these):
 [list of hard facts]

 Rules for compaction:
 1. Preserve the MOST RECENT context in more detail
 2. Compress OLDER context into high-level themes
 3. Never drop: blockers, unresolved concerns, pending actions
 4. Drop: resolved issues, completed tasks (unless pattern-relevant)
 5. Maintain chronological narrative flow
 6. Target: 1200-1500 tokens

 Produce the compacted summary."
```

**Before/After Compaction Example:**

**BEFORE (2400 tokens):**

> "Week of Jan 1-7: The COO onboarded with ChiefOps, uploading Slack exports from December and Jira CSV. Initial analysis identified 4 projects: Alpha, Beta, Gamma, and internal tooling. The COO was particularly interested in Alpha and Beta. The system identified 45 team members across all projects. The COO corrected several role assignments (these are now in hard facts). The COO asked about sprint velocity for Alpha and was surprised it was declining. The system explained that holiday PTO was a factor.
>
> Week of Jan 8-14: The COO focused heavily on Alpha's timeline. Sprint velocity data showed a continued decline from 3.2 to 2.8. The system identified that Priya's reassignment from frontend to backend (corrected by COO) and two team members on extended PTO were contributing factors. Slack activity from #project-alpha showed the team deciding on a phased database migration approach. The architect proposed Stage 1 (read replicas) and Stage 2 (write migration), and the team agreed. Anil picked up ALPHA-142 (API rate limiting) and completed it with exponential backoff. The COO asked about March 20 deadline feasibility and the system flagged 3 at-risk tasks.
>
> Week of Jan 15-21: The COO compared Alpha and Beta progress. Beta is ahead of schedule (82% complete vs Alpha's 61%). The COO asked why and the system identified that Beta has more stable team allocation and fewer scope changes. The COO requested a board report draft. Slack showed the Alpha team discussing test coverage concerns — only 45% coverage on the new API endpoints. The COO raised this as a risk. The COO also asked about hiring plans and whether adding a developer to Alpha would help. The system estimated a 2-week ramp-up time for a new developer."

**AFTER (1350 tokens):**

> "Weeks 1-2 (Jan 1-14): COO onboarded, identified 4 projects and 45 team members. Early focus on Alpha's declining sprint velocity (3.2 to 2.8) — attributed to team PTO and Priya's role change. Slack confirmed team agreement on phased DB migration (read replicas first, then write migration). ALPHA-142 (API rate limiting) completed with exponential backoff.
>
> Week 3 (Jan 15-21): Alpha at 61% completion vs Beta at 82%. Beta's advantage: stable team allocation and fewer scope changes. Key concerns: March 20 deadline feasibility with 3 at-risk tasks, test coverage only 45% on new API endpoints (COO flagged as risk). COO considering adding a developer to Alpha (system estimated 2-week ramp-up). Board report draft requested for next Friday. Slack showed test coverage discussion gaining urgency."

Notice how:
- Week 1 detail is compressed (onboarding details dropped)
- Week 2 key decisions are preserved (DB migration approach)
- Week 3 retains the most detail (most recent)
- Hard facts (Raj's role, Priya's role, deadlines) are NOT in the summary — they are in Layer 1
- Resolved issues (ALPHA-142 completed) are briefly noted but not detailed
- Unresolved concerns (test coverage, March 20 risk) retain full detail

### 7.4 Deep Compaction (Monthly or When Threshold Exceeded)

**When:** Monthly, or when the total compacted summary size across all archived summaries exceeds a threshold.

**What happens:**

1. Older compacted summaries (weekly summaries from previous months) are further compressed to essential themes only.
2. The most compressed form retains only: major decisions, unresolved long-running issues, and patterns.
3. The archived summaries remain in Citex for semantic retrieval — they are never deleted.
4. The oldest summaries move to "archive" status — they are no longer in the active prompt but are still searchable.

**Deep compaction example:**

Monthly summary for January:

> "January: Alpha project at 61% completion with declining velocity. Key decisions: phased DB migration, exponential backoff for API rate limiting. Ongoing concerns: March 20 deadline feasibility, test coverage gaps, team capacity. Beta ahead at 82%. COO considering adding developer to Alpha. Board report cycle established."

This is the most compressed form. If the COO asks about something specific from January ("What did the team decide about the database migration?"), Citex retrieves the relevant weekly or session summary that has more detail.

---

## 8. Compaction Triggers Table

| Trigger | Condition | Action | Output |
|---------|-----------|--------|--------|
| **New data extract** | COO uploads new Slack/Jira/Drive files | Slack messages summarized per project; facts extracted from all sources; summaries merged into project streams | Updated facts + updated active summaries per project |
| **Every COO turn** | After every AI response | Fact extraction from the turn | 0-3 new facts added to Layer 1 |
| **Every ~20 COO turns** | Turn count within a project stream reaches ~20 since last session summary | Session summary generated; merged into active summary | New session summary + updated active summary |
| **Summary exceeds ~2000 tokens** | Active compacted summary token count > 2000 | AI compacts: compress older content, preserve recent detail, never drop unresolved concerns | Shorter active summary (~1200-1500 tokens); pre-compaction version archived in Citex |
| **Weekly (if active)** | End of week, project had activity | All session summaries from the week compacted into one weekly summary | Weekly summary stored and indexed in Citex |
| **Monthly** | End of month | Weekly summaries from the month compacted into one monthly summary; oldest summaries moved to archive status | Monthly summary; archived summaries still Citex-searchable but no longer in active prompt |
| **Manual trigger** | COO says "Refresh memory" or similar | Full recompaction cycle: re-extract facts, regenerate active summary from all session summaries | Refreshed active summary and fact list |

### Trigger Interaction Diagram

```
                    Every COO Turn
                         │
                         ▼
                  ┌──────────────┐
                  │    Fact      │
                  │  Extraction  │──── New facts → Layer 1
                  └──────┬───────┘
                         │
                  (every ~20 turns)
                         │
                         ▼
                  ┌──────────────┐
                  │   Session    │
                  │   Summary    │──── Stored in Citex
                  └──────┬───────┘
                         │
                  (merged into active summary)
                         │
                         ▼
                  ┌──────────────┐
                  │   Active     │
                  │   Summary    │
                  │  > 2000 tk?  │
                  └──────┬───────┘
                    No   │   Yes
                    │    │    │
                    ▼    │    ▼
                  [wait] │  ┌──────────────┐
                         │  │  Progressive  │
                         │  │  Compaction   │──── Old version archived in Citex
                         │  └──────┬───────┘
                         │         │
                         │    (target: 1200-1500 tokens)
                         │         │
                         ▼         ▼
                  ┌──────────────────────┐
                  │  Active Summary      │
                  │  (~1500-2000 tokens)  │
                  └──────────────────────┘
                         │
                    (end of week)
                         │
                         ▼
                  ┌──────────────┐
                  │   Weekly     │
                  │  Compaction  │──── Weekly summary stored in Citex
                  └──────┬───────┘
                         │
                    (end of month)
                         │
                         ▼
                  ┌──────────────┐
                  │   Monthly    │
                  │  Compaction  │──── Monthly summary stored in Citex
                  └──────┬───────┘     Oldest summaries → archive status
                         │
                         ▼
                  ┌──────────────┐
                  │   Archive    │
                  │  (Citex only)│──── Not in active prompt
                  └──────────────┘     Retrievable via semantic search
```

---

## 9. Context Assembly for AI Requests

When the COO sends a message, the system assembles a complete context payload before calling the AI. This is the most important runtime operation in the memory system — it determines what the AI knows when it generates a response.

### Assembly Pipeline

```
COO sends: "Are we on track for the March 20 deadline?"
Page context: Project Alpha dashboard

                    ┌───────────────────────────────┐
                    │   CONTEXT ASSEMBLY PIPELINE     │
                    └───────────────┬───────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
   │  Load from   │         │  Load from   │         │  Query       │
   │  MongoDB     │         │  MongoDB     │         │  Citex       │
   │  (fast)      │         │  (fast)      │         │  (semantic)  │
   └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
          │                         │                         │
   ┌──────┴───────┐         ┌──────┴───────┐         ┌──────┴───────┐
   │ Project      │         │ Global       │         │ Relevant     │
   │ Alpha facts  │         │ stream facts │         │ chunks from  │
   │ Alpha active │         │              │         │ Slack, Jira, │
   │ summary      │         │              │         │ Drive docs   │
   │ Alpha last   │         │              │         │              │
   │ 10 turns     │         │              │         │              │
   └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │       PROMPT ASSEMBLY          │
                    │                               │
                    │  1. System prompt              │
                    │  2. Project hard facts         │
                    │  3. Global hard facts          │
                    │  4. Compacted summary          │
                    │  5. Last 10 raw turns          │
                    │  6. Citex retrieved chunks     │
                    │  7. Structured data summaries  │
                    │  8. Current query              │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        AI MODEL CALL           │
                    │   (via AI Adapter Pattern)     │
                    └───────────────────────────────┘
```

### Detailed Breakdown of Each Component

#### Component 1: System Prompt (~800 tokens)

The system prompt defines the AI's role, behavior, and output formatting rules. It is static and the same for every request (with minor variations based on the type of query).

```
"You are ChiefOps, an AI-powered Chief Operations Officer assistant.
You help the COO understand project status, team performance, and
operational risks. You have access to Slack conversations, Jira task
data, and Google Drive documents.

Rules:
- Be concise but thorough
- Flag risks proactively
- When uncertain, say so and explain your confidence level
- Reference specific data sources when making claims
- If corrected, acknowledge and update your understanding
- Use the hard facts provided as ground truth (highest priority)
- Use the compacted summary for historical context
- Use recent turns for conversational continuity
- Use Citex chunks for supporting evidence
..."
```

#### Component 2: Project Hard Facts (~300-500 tokens)

All active facts from the project's stream, formatted as a concise reference list.

```
"=== ESTABLISHED FACTS: Project Alpha ===
- Raj is the Lead Architect (COO correction, Jan 15)
- Priya handles backend, not frontend (COO correction, Jan 15)
- Alpha deadline: March 20
- Team decided on phased DB migration: Stage 1 read replicas, Stage 2 write migration (Slack, Jan 14)
- ALPHA-142 (API rate limiting) completed with exponential backoff (Slack, Jan 18)
- PostgreSQL migration benchmarks: 3x read query improvement (Slack, Jan 12)
- Sprint velocity declining: 3.2 → 2.8 (Jira data, Jan 21)
- Anil assigned to ALPHA-142 (Slack, Jan 12)
- Alpha at 61% completion as of Jan 21
- 3 critical-path tasks currently unassigned"
```

#### Component 3: Global Stream Facts (~200-300 tokens)

Organizational facts that apply across all projects.

```
"=== GLOBAL FACTS ===
- COO prefers Gantt charts for timeline views
- Board meeting every last Friday of the month
- Company has 80 employees (12 engineering)
- COO prefers executive summaries under 200 words
- Series B funding closed Dec 2024
- Team uses Figma for design"
```

#### Component 4: Compacted Summary from Project Stream (~1500-2000 tokens)

The active compacted summary, providing historical narrative context.

```
"=== PROJECT ALPHA CONTEXT SUMMARY ===
Weeks 1-2 (Jan 1-14): COO onboarded, identified 4 projects and
45 team members. Early focus on Alpha's declining sprint velocity
(3.2 to 2.8) — attributed to team PTO and Priya's role change.
Slack confirmed team agreement on phased DB migration...

Week 3 (Jan 15-21): Alpha at 61% completion vs Beta at 82%...
[full active summary as shown in Section 7.3]"
```

#### Component 5: Last 10 Raw COO Turns (~3000-5000 tokens)

Verbatim recent conversation, preserving full detail and nuance.

```
"=== RECENT CONVERSATION ===

[Turn 38] COO: Show me the sprint burndown for Alpha
AI: Here's the Sprint 12 burndown for Project Alpha. You started
    with 34 story points and have completed 21 as of today...

[Turn 39] COO: Why is velocity dropping?
AI: Three contributing factors for Alpha's velocity decline:
    1. Priya's reassignment from frontend to backend (Jan 10)...

...

[Turn 47] COO: Are we on track for the March 20 deadline?  ← CURRENT
```

#### Component 6: Citex Retrieved Chunks (~3000-6000 tokens)

Semantic search results from Citex, retrieved based on the current query. These might include:

- Relevant Slack conversation excerpts about the March deadline
- Jira task details for tasks on the critical path
- Google Drive documents about project requirements or timelines
- Archived compacted summaries that mention deadline discussions

```
"=== RELEVANT DATA (from Citex semantic search) ===

[Slack #project-alpha, Jan 19]: "Team, I'm worried about the
March deadline. We still have the payment integration and the
load testing to complete..."

[Jira ALPHA-189]: "Payment integration - Status: In Progress,
Assignee: Deepak, Sprint: 13, Story Points: 8, Due: Feb 28"

[Jira ALPHA-195]: "Load testing infrastructure - Status: To Do,
Assignee: Unassigned, Story Points: 5, Due: None"

[Archived summary, Jan 14]: "The COO asked about March 20
feasibility. System identified 3 at-risk tasks at current velocity..."
```

#### Component 7: Structured Data Summaries from MongoDB (~1000-2000 tokens)

Pre-computed summaries of structured data — sprint metrics, task rollups, people activity. These are not raw data but pre-aggregated summaries.

```
"=== STRUCTURED DATA SUMMARY ===

Sprint 12 (current): 21/34 story points complete (62%),
5 days remaining. Velocity: 2.8 pts/day.

Tasks remaining for March 20: 14 tasks, 47 story points.
At current velocity (2.8/day), estimated completion: March 28.
At full team velocity (4.2/day), estimated completion: March 14.

Team allocation: 5 active developers, 2 on PTO this week.
Unassigned critical tasks: ALPHA-195 (load testing),
ALPHA-201 (security audit), ALPHA-203 (deployment runbook)."
```

#### Component 8: Current Query (~100-200 tokens)

The COO's current message, with any relevant metadata.

```
"=== CURRENT QUERY ===
Page: Project Alpha Dashboard (Static)
Query: Are we on track for the March 20 deadline?"
```

### Total Token Budget

| Component | Token Range | Source |
|-----------|------------|--------|
| System prompt | ~800 | Static |
| Project hard facts | ~300-500 | MongoDB |
| Global hard facts | ~200-300 | MongoDB |
| Compacted summary | ~1500-2000 | MongoDB |
| Last 10 raw turns | ~3000-5000 | MongoDB |
| Citex retrieved chunks | ~3000-6000 | Citex |
| Structured data summaries | ~1000-2000 | MongoDB (pre-computed) |
| Current query | ~100-200 | User input |
| **Total** | **~10,000-15,000** | |

This fits comfortably within the context windows of modern LLMs (Claude: 200K tokens, GPT-4: 128K tokens). We use only ~10-15K tokens, leaving ample room for the AI response and any additional context if needed. The system is designed to be efficient, not to fill the context window.

### Assembly Timing

The context assembly must happen in real time for every COO query. Target latency:

| Step | Operation | Target Latency |
|------|-----------|---------------|
| 1 | Load facts from MongoDB | < 50ms |
| 2 | Load active summary from MongoDB | < 50ms |
| 3 | Load last 10 turns from MongoDB | < 50ms |
| 4 | Query Citex for relevant chunks | < 500ms |
| 5 | Load structured data summaries | < 100ms |
| 6 | Assemble prompt | < 50ms |
| **Total assembly** | | **< 800ms** |

The Citex query is the slowest step. Steps 1-3 and 5 can run in parallel. The assembly adds less than 1 second to the total response time.

---

## 10. Nothing Is Truly Lost

The memory system is designed around one principle: **no information is ever permanently lost**. Even as summaries are compacted and older context is archived, every piece of information remains retrievable through at least one mechanism.

### Retrieval Guarantees

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NOTHING IS TRULY LOST                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Was it a CORRECTION or DECISION?                           │    │
│  │  → It's in HARD FACTS (Layer 1)                             │    │
│  │  → ALWAYS in every prompt                                   │    │
│  │  → Never compacted, never archived, never lost              │    │
│  │  Example: "Raj = Lead Architect" is in every single         │    │
│  │           AI request, forever.                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Was it in a SESSION SUMMARY?                               │    │
│  │  → It's INDEXED IN CITEX                                    │    │
│  │  → Retrieved when semantically relevant to the query        │    │
│  │  → Example: COO asks "What did we discuss about hiring?"    │    │
│  │    Citex retrieves the session summary from Jan 21 that     │    │
│  │    mentioned the COO considering adding a developer.        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Was it a RAW CONVERSATION TURN?                            │    │
│  │  → It's in MONGODB conversation_turns collection            │    │
│  │  → Queryable by project, date, keyword                      │    │
│  │  → The system can look up specific past turns if needed     │    │
│  │  → Example: "What exactly did I say about Raj on Jan 15?"   │    │
│  │    System retrieves the specific turn from MongoDB.         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Was it a SLACK MESSAGE?                                    │    │
│  │  → Raw messages are in MongoDB slack_messages collection    │    │
│  │  → Slack summaries are indexed in Citex                     │    │
│  │  → Key decisions are extracted as Hard Facts                │    │
│  │  → Example: "What did Raj say about the DB migration?"      │    │
│  │    Citex retrieves the Slack summary; if more detail        │    │
│  │    needed, raw messages are queried from MongoDB.           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Was it COMPACTED OUT of the active summary?                │    │
│  │  → The pre-compaction version is archived in Citex          │    │
│  │  → Weekly and monthly summaries are also in Citex           │    │
│  │  → The compacted-out detail is semantically searchable      │    │
│  │  → Example: Detailed discussion from 2 months ago about     │    │
│  │    API design decisions — no longer in active summary,       │    │
│  │    but Citex retrieves the archived weekly summary when     │    │
│  │    the COO asks about API design.                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Three Layers + Citex = Comprehensive Memory

| Information Type | Primary Storage | Prompt Inclusion | Retrieval Method |
|-----------------|----------------|-----------------|-----------------|
| Hard facts (corrections, decisions) | MongoDB `conversation_facts` | Always in prompt (Layer 1) | Automatic — always present |
| Recent conversation detail | MongoDB `conversation_turns` | Always in prompt (Layer 3, last 10) | Automatic — always present |
| Historical narrative context | MongoDB `compacted_summaries` | Active summary in prompt (Layer 2) | Automatic — always present |
| Older session details | Citex index | Retrieved when query is semantically relevant | Semantic search — on demand |
| Archived monthly summaries | Citex index | Retrieved when query is semantically relevant | Semantic search — on demand |
| Raw Slack messages | MongoDB `slack_messages` | Not in prompt directly | Direct MongoDB query if needed |
| Raw conversation turns (older than 10) | MongoDB `conversation_turns` | Not in prompt directly | Direct MongoDB query if needed |
| Slack weekly summaries | Citex index | Retrieved when relevant | Semantic search — on demand |

### Worst Case: How Far Back Can We Go?

Scenario: The COO asks about something discussed 6 months ago.

1. **If it was a decision or correction** → It is in Hard Facts. The AI knows it immediately. No retrieval needed.

2. **If it was a discussion topic** → It was in a session summary → which was compacted into a weekly summary → which was compacted into a monthly summary → which may or may not be in the active summary. But ALL of these summaries are indexed in Citex. The semantic search retrieves the most relevant ones.

3. **If it was a specific Slack message** → The raw message is in MongoDB. The Slack summary that included it is in Citex. The AI can retrieve both.

4. **If it was a specific COO conversation turn** → The raw turn is in MongoDB `conversation_turns`. The session summary that included it is in Citex.

The system gracefully degrades from "always in the prompt" to "retrieved when relevant" to "queryable from storage." Nothing is ever deleted.

---

## 11. Implementation Notes

### AI Adapter Usage

All AI-powered operations in the memory system use the same AI adapter pattern described in [AI Layer](./06-AI-LAYER.md). This means:

| Operation | AI Adapter Call | Model Preference |
|-----------|----------------|-----------------|
| Fact extraction (per turn) | `ai_adapter.extract_facts(turn)` | Fast model (low latency, small prompt) |
| Session summary generation | `ai_adapter.generate_session_summary(turns)` | Standard model (medium prompt) |
| Progressive compaction | `ai_adapter.compact_summary(summary, facts)` | Standard model (medium prompt) |
| Slack message summarization | `ai_adapter.summarize_slack(messages)` | Standard model (medium-large prompt) |
| Slack fact extraction | `ai_adapter.extract_slack_facts(messages)` | Fast model (small prompt) |
| Summary merging (Slack into project) | `ai_adapter.merge_summaries(existing, new)` | Standard model (medium prompt) |
| Deep compaction (monthly) | `ai_adapter.deep_compact(summaries)` | Standard model (medium prompt) |
| Conversation routing (ambiguous) | `ai_adapter.detect_project(query)` | Fast model (very small prompt) |

In development, these use CLI-based AI (Claude CLI, Codex CLI). In production, they use Open Router. The adapter pattern ensures zero code changes when switching providers.

### MongoDB Collections

The memory system uses four primary MongoDB collections (schemas defined in [Data Models](./03-DATA-MODELS.md)):

| Collection | Purpose | Indexed Fields |
|-----------|---------|---------------|
| `conversation_facts` | Layer 1 hard facts | `project_id`, `active`, `category`, `created_at` |
| `compacted_summaries` | Layer 2 summaries (active, session, weekly, monthly, archived) | `project_id`, `summary_type`, `covers_period`, `created_at` |
| `conversation_turns` | Layer 3 raw turns | `project_id`, `turn_number`, `source`, `created_at` |
| `slack_messages` | Raw Slack messages (for reference) | `project_id`, `channel`, `author`, `timestamp` |

### Citex Integration

Every summary document (session, weekly, monthly, archived) is stored in Citex alongside the raw data chunks. This means Citex contains:

1. **Raw data chunks** — Slack messages, Jira tasks, Drive documents (standard RAG)
2. **Memory summaries** — session summaries, weekly compacted summaries, monthly summaries, archived summaries

When the system queries Citex, it retrieves both raw data and relevant historical summaries. The query does not distinguish between them — semantic relevance determines what comes back.

**Citex document metadata for memory summaries:**

```json
{
  "document_type": "memory_summary",
  "summary_type": "session",           // "session" | "weekly" | "monthly" | "archived"
  "project_id": "project_alpha",
  "covers_period_from": "2025-01-15",
  "covers_period_to": "2025-01-21",
  "source_types": ["coo_conversation", "slack"],
  "compaction_generation": 2
}
```

This metadata allows filtering Citex results if needed — for example, the system can prioritize recent summaries over older ones, or filter for only Slack-sourced summaries.

### Concurrency and Consistency

The compaction pipeline runs asynchronously. It does not block COO interactions.

| Concern | Handling |
|---------|---------|
| COO sends message during compaction | The message uses the pre-compaction active summary. After compaction completes, the next message uses the new summary. |
| Two compaction triggers fire simultaneously | A lock (Redis-based) ensures only one compaction runs per project stream at a time. The second trigger is queued. |
| Fact extraction finds a contradiction | The old fact is marked `active: false` atomically with the new fact creation (MongoDB transaction). |
| Citex indexing lags behind MongoDB writes | The system uses MongoDB as the source of truth for the active prompt. Citex is eventually consistent — a brief lag in indexing does not affect the active prompt. |

### Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| Fact extraction latency | < 1 second | Fast model, small prompt (~500 tokens) |
| Session summary generation | < 3 seconds | Standard model, medium prompt (~3000 tokens) |
| Progressive compaction | < 5 seconds | Standard model, medium prompt (~3000 tokens) |
| Context assembly | < 800ms | Parallel MongoDB + Citex queries |
| Slack batch summarization (100 messages) | < 10 seconds | Standard model, larger prompt |
| Weekly compaction | < 5 seconds | Standard model, merging 3-5 session summaries |
| Monthly deep compaction | < 5 seconds | Standard model, merging 4-5 weekly summaries |

### Error Handling

| Failure | Impact | Recovery |
|---------|--------|----------|
| Fact extraction fails | Turn proceeds normally; fact extraction retried in background | Background retry queue |
| Session summary fails | Active summary is stale but functional; retried at next trigger | Accumulates turns and generates summary at next trigger |
| Compaction fails | Active summary grows beyond 2000 tokens; retried at next trigger | The system works with a larger-than-ideal summary until compaction succeeds |
| Citex unavailable | Historical summaries not retrievable; active prompt still works (MongoDB-backed layers are unaffected) | Graceful degradation — system notes reduced context in response |
| MongoDB unavailable | System cannot function — all three layers depend on MongoDB | Critical failure — system displays error to COO |

### Testing Strategy

| Test Type | What Is Tested |
|-----------|---------------|
| Unit tests | Fact extraction accuracy, summary generation quality, compaction preservation |
| Integration tests | Full pipeline: turn → fact extraction → session summary → compaction → context assembly |
| Regression tests | Corrections persist across compaction cycles; no fact loss after deep compaction |
| Load tests | Memory system performance with 1000+ turns and 5000+ Slack messages per project |
| Quality tests | AI-judged: does the compacted summary preserve key information? Does fact extraction catch all corrections? |

---

## Related Documents

- **System Design:** [Architecture](./02-ARCHITECTURE.md), [Data Models](./03-DATA-MODELS.md)
- **AI Integration:** [AI Layer](./06-AI-LAYER.md), [Citex Integration](./05-CITEX-INTEGRATION.md)
- **Data Sources:** [File Ingestion](./08-FILE-INGESTION.md)
- **Features:** [People Intelligence](./09-PEOPLE-INTELLIGENCE.md), [Report Generation](./07-REPORT-GENERATION.md), [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md)
- **Execution:** [Implementation Plan](./11-IMPLEMENTATION-PLAN.md), [UI/UX Design](./12-UI-UX-DESIGN.md)
