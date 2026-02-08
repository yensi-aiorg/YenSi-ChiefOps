# People Intelligence: ChiefOps — Step Zero

> **Navigation:** [README](./00-README.md) | [PRD](./01-PRD.md) | [Architecture](./02-ARCHITECTURE.md) | [Data Models](./03-DATA-MODELS.md) | [Memory System](./04-MEMORY-SYSTEM.md) | [Citex Integration](./05-CITEX-INTEGRATION.md) | [AI Layer](./06-AI-LAYER.md) | [Report Generation](./07-REPORT-GENERATION.md) | [File Ingestion](./08-FILE-INGESTION.md) | **People Intelligence** | [Dashboard & Widgets](./10-DASHBOARD-AND-WIDGETS.md) | [Implementation Plan](./11-IMPLEMENTATION-PLAN.md) | [UI/UX Design](./12-UI-UX-DESIGN.md)

---

## 1. Why This Is Different

Most project management tools show you who is assigned to a task. You open Jira, click on a ticket, and see "Assignee: Raj Kumar." Simple. Clean. And completely insufficient for understanding what is actually happening in a startup.

Here is why:

**Jira tasks often have NO assignee.** In a fast-moving startup, tickets get created in bulk during sprint planning. Half of them never get a formal assignee because the team "knows" who is doing what. The COO looking at Jira sees 40% of tasks with no owner and has zero visibility into who is actually responsible.

**People get work assigned in Slack.** The real assignment happens in a message: "Hey Raj, can you look at the authentication flow? It's blocking the iOS team." That message is the actual assignment. It never makes it to Jira. The COO never sees it unless she happens to be in that channel at that moment.

**One task involves multiple people informally.** A single Jira ticket — say "Implement payment gateway" — might have three people working on it: one writing the backend, one handling the frontend integration, one testing edge cases. Jira shows one assignee (or none). The real picture is hidden in Slack threads.

**People wear multiple hats.** In a 50-person startup, a developer might also do DevOps. A designer might also do product management. A PM might also handle QA. Role detection is not a database lookup — it requires understanding what someone actually does day to day.

**Engagement levels vary.** Some people are active contributors who drive discussions, complete tasks early, and unblock others. Some are passively observing — present in channels but rarely contributing. Knowing who is truly engaged versus who has quietly checked out is critical for a COO.

ChiefOps uses AI to understand ALL of this from unstructured data. Not through rules. Not through keyword matching. Through genuine comprehension of human communication patterns, cross-referenced across every data source available.

This is the hardest capability in ChiefOps. It is also the most valuable.

---

## 2. People Identification Pipeline

The People Intelligence pipeline runs in five sequential steps. Each step builds on the previous one, and the AI is involved at every stage where ambiguity exists.

### Step 1: Build Initial Directory

The first step is assembling a raw list of every person mentioned across all data sources. This is a data extraction step — no AI needed yet, just thorough parsing.

**From Slack:**
- Parse `users.json` from the Slack export to get: display name, real name, username, email (if present), profile image URL, timezone, account status (active/deactivated)
- Parse every message across all channels to extract unique message authors
- Extract usernames mentioned via `@mentions` in messages
- Extract display names referenced in natural language ("Raj said...", "talked to Priya about...")

**From Jira CSV:**
- Extract all unique values from the `Assignee` column
- Extract all unique values from the `Reporter` column
- Extract names from `Comments` column if present in the export
- Extract names from custom fields (reviewer, QA tester, etc.) if present

**From Google Drive:**
- Extract file owner names from metadata
- Extract last-modified-by names
- Extract names from sharing permissions if visible
- Extract names from document content (e.g., "Author: Raj Kumar" in a doc header)

**Raw Directory Output:**

Each extracted person record contains:

```
{
  slack_user_id: "U04ABC123",
  slack_username: "raj.k",
  slack_display_name: "Raj K.",
  slack_real_name: "Raj Kumar",
  slack_email: "raj.kumar@company.com",
  jira_name: "Raj Kumar",
  jira_username: "rkumar",
  drive_name: "Raj Kumar",
  drive_email: "raj.kumar@company.com",
  sources: ["slack", "jira", "drive"],
  extracted_at: "2025-02-15T10:30:00Z"
}
```

**Fuzzy Matching Across Sources:**

This is the first place where matching gets tricky. The same person appears differently across systems:

| Slack | Jira | Google Drive |
|-------|------|-------------|
| Raj K. | Raj Kumar | raj.kumar@company.com |
| priya_d | Priya Deshpande | Priya D. |
| mikey_frontend | Mike Chen | Michael Chen |
| deepa | Deepa Sharma | deepa.sharma@company.com |

The matching algorithm works in three tiers:

**Tier 1 — Exact Match (Confidence: 100%)**
- Email addresses match exactly across sources
- Full names match exactly (case-insensitive)

**Tier 2 — Fuzzy Match (Confidence: 70-95%)**
- Using `rapidfuzz` library with token_sort_ratio and partial_ratio
- "Raj K." vs "Raj Kumar" → partial_ratio = 85% → likely match
- "mikey_frontend" vs "Mike Chen" → requires AI confirmation
- Threshold: fuzzy score > 80% is flagged as probable match

**Tier 3 — AI-Assisted Match (Confidence: varies)**
- For names that score 60-80% on fuzzy matching
- AI is given the names, their activity patterns, and context to determine if they are the same person
- "Michael Chen" in Drive who edits frontend docs + "mikey_frontend" in Slack who discusses React components → AI determines: same person, confidence 92%

All matches below 90% confidence are flagged for COO confirmation.

### Step 2: Role Detection (AI-Powered)

Once the people directory is built, the AI analyzes each person's communications and task patterns to determine their role in the organization. This is entirely AI-driven because role detection from unstructured data cannot be done with rules.

**Input Signals for Role Detection:**

The AI reads every signal available for each person:

*Slack Message Content Analysis:*
- What topics does this person discuss? Code reviews, API design, database schemas → likely a developer. Design mockups, user flows, Figma links → likely a designer. Sprint planning, deadline tracking, stakeholder updates → likely a PM.
- What vocabulary do they use? Technical terms (endpoints, schema, deployment) vs. process terms (timeline, blocker, stakeholder) vs. design terms (wireframe, prototype, user journey).
- What questions do they ask? "How should we structure the API?" (architect) vs. "When is this due?" (PM) vs. "Does this match the mockup?" (frontend dev).

*Slack Behavioral Patterns:*
- Who initiates conversations vs. who responds?
- Who gives code review feedback?
- Who asks for status updates? (likely PM or lead)
- Who provides technical decisions? (likely architect or senior dev)
- Who mediates disagreements? (likely PM or team lead)
- Who shares design files? (likely designer)
- Which channels are they most active in? (#engineering, #design, #product, #general)

*Jira Task Type Analysis:*
- What types of tasks are assigned to them? Backend API tasks → backend dev. UI component tasks → frontend dev. Bug fixes across systems → QA. Architecture documents → architect.
- What labels/components are on their tasks? "ios", "android", "backend", "infra", "design"
- What is the complexity of their tasks? Story points, if available.

*Cross-Source Correlation:*
- Slack discussions about backend + Jira tasks with "API" component + Drive documents about system architecture → strong signal for backend architect role

**AI Role Assessment Output:**

For each person, the AI produces:

```json
{
  "person_id": "person_raj_kumar",
  "name": "Raj Kumar",
  "primary_role": {
    "title": "Backend Architect",
    "confidence": 0.88,
    "evidence": [
      "Leads architecture discussions in #engineering (15 threads initiated)",
      "Assigned Jira tasks with 'architecture' and 'backend' labels (8 tasks)",
      "Provides technical decisions and code review feedback",
      "Authored 3 architecture documents in Google Drive",
      "Other team members defer to his technical judgment"
    ]
  },
  "secondary_roles": [
    {
      "title": "DevOps",
      "confidence": 0.62,
      "evidence": [
        "Discusses deployment pipelines in #devops channel",
        "Has 2 Jira tasks related to CI/CD setup"
      ]
    }
  ],
  "skills_detected": [
    "Node.js", "MongoDB", "System Design", "AWS", "Docker",
    "CI/CD", "API Design", "Code Review"
  ],
  "seniority_assessment": {
    "level": "Senior / Lead",
    "confidence": 0.82,
    "evidence": [
      "Gives approvals on technical decisions",
      "Mentors junior developers in Slack threads",
      "Assigned complex, high-impact tasks"
    ]
  }
}
```

**Role Taxonomy:**

The AI uses the following role categories but is not limited to them. It can identify any role that the data supports.

| Category | Possible Roles |
|----------|---------------|
| Engineering | Frontend Developer, Backend Developer, Full-Stack Developer, Mobile Developer (iOS/Android), DevOps Engineer, QA Engineer, Data Engineer, ML Engineer |
| Architecture | Software Architect, Backend Architect, Frontend Architect, Solution Architect |
| Design | UI Designer, UX Designer, Product Designer, UX Researcher |
| Product | Product Manager, Product Owner, Business Analyst, Scrum Master |
| Leadership | Engineering Manager, Team Lead, Tech Lead, CTO, VP Engineering |
| Operations | Project Manager, Program Manager, Release Manager, Operations Manager |
| Other | Technical Writer, Support Engineer, Security Engineer, Contractor |

### Step 3: Informal Assignment Detection

This is one of the most valuable capabilities in ChiefOps. The AI scans Slack messages for informal task assignments — the ones that never make it to Jira but represent real work commitments.

**Pattern Recognition:**

The AI identifies the following patterns in Slack messages:

*Direct Assignment:*
- "Hey [name], can you pick up [task/ticket]?"
- "@[name] this is yours"
- "@[name] can you take care of [task]?"
- "[name], I need you to handle [task]"
- "Assigning [task] to [name]"

*Self-Assignment:*
- "I'll handle [task]"
- "I'll take [task/ticket]"
- "I'm picking up [task]"
- "Let me work on [task]"
- "I've got [task]"

*Third-Party Reference:*
- "[name] is working on [task]"
- "[name] took over [task]"
- "[name] has been handling [task]"
- "I think [name] is doing [task]"

*Multi-Assignment:*
- "[name] and [name] are pairing on [task]"
- "This is a joint effort between [name] and [name]"
- "[name] will do the backend, [name] will do the frontend for [task]"

*Implicit Assignment (requires deeper AI understanding):*
- "[name] mentioned he'd look into the login bug" (probable self-assignment in a meeting)
- "Can someone from the iOS team check this?" followed by "[name]: on it" (volunteer assignment)
- "[name] fixed the deployment issue yesterday" (past tense implies completed assignment)

**Task Reference Matching:**

When the AI detects an informal assignment, it attempts to link it to an existing Jira task:

1. **Exact ticket reference:** "Hey Raj, can you pick up PROJ-142?" → direct link to PROJ-142
2. **Task description match:** "Raj is working on the payment gateway" → fuzzy match against Jira task titles → finds "PROJ-89: Implement payment gateway integration" (confidence 87%)
3. **New work detection:** "Raj, can you set up the staging environment?" → no matching Jira task found → flag as "untracked work" for COO visibility

**Informal Assignment Record:**

```json
{
  "assignment_id": "ia_001",
  "type": "informal_slack_assignment",
  "assigned_to": "person_raj_kumar",
  "assigned_by": "person_priya_deshpande",
  "task_reference": {
    "jira_key": "PROJ-142",
    "match_confidence": 1.0,
    "match_type": "exact_ticket_reference"
  },
  "source_message": {
    "channel": "#engineering",
    "timestamp": "2025-02-10T14:32:00Z",
    "text": "Hey Raj, can you pick up PROJ-142? It's blocking the iOS release."
  },
  "detection_confidence": 0.95,
  "status": "detected",
  "verified_by_coo": false
}
```

**Informal vs. Formal Assignment Hierarchy:**

When both exist for the same task:

| Scenario | Resolution |
|----------|-----------|
| Jira says Assignee = Raj, Slack says Raj is working on it | Consistent — high confidence |
| Jira says Assignee = None, Slack says Raj is working on it | Informal assignment wins — flag for COO awareness |
| Jira says Assignee = Raj, Slack says Priya is actually doing it | Conflict — flag for COO resolution, show both |
| Jira says Assignee = Raj, Slack says Raj and Anil are pairing | Jira assignee confirmed, additional contributor detected |

### Step 4: Engagement Tracking

For each person identified in the directory, ChiefOps calculates a comprehensive set of engagement metrics. These metrics power activity level classification, workload analysis, and risk detection.

**Raw Metrics Collected:**

For each person, per data extract period:

```json
{
  "person_id": "person_raj_kumar",
  "period": {
    "start": "2025-02-01",
    "end": "2025-02-15"
  },
  "slack_metrics": {
    "total_messages_sent": 187,
    "messages_by_channel": {
      "#engineering": 92,
      "#proj-alpha": 45,
      "#general": 28,
      "#random": 12,
      "#devops": 10
    },
    "threads_started": 23,
    "threads_replied_to": 67,
    "reactions_given": 45,
    "reactions_received": 89,
    "mentions_of_others": 34,
    "mentions_by_others": 56,
    "code_snippets_shared": 8,
    "files_shared": 3,
    "direct_messages_sent": 42,
    "avg_response_time_minutes": 18,
    "active_hours": {
      "earliest": "08:30",
      "latest": "21:15",
      "peak_hour": "14:00"
    },
    "active_days": 13,
    "inactive_days": 2,
    "longest_inactive_streak_days": 1
  },
  "jira_metrics": {
    "tasks_assigned_total": 8,
    "tasks_completed": 5,
    "tasks_in_progress": 2,
    "tasks_not_started": 1,
    "tasks_overdue": 0,
    "avg_days_to_complete": 3.2,
    "story_points_completed": 21,
    "story_points_in_progress": 8,
    "comments_on_tasks": 14,
    "tasks_created": 3
  },
  "drive_metrics": {
    "files_created": 2,
    "files_modified": 7,
    "files_viewed": 15
  },
  "informal_metrics": {
    "tasks_informally_assigned": 3,
    "tasks_informally_completed": 2,
    "times_mentioned_as_working_on_task": 12,
    "times_volunteered_for_work": 4
  }
}
```

**Derived Engagement Scores:**

From raw metrics, the system calculates derived scores:

```
communication_score = weighted_sum(
  messages_sent * 0.3,
  threads_replied_to * 0.25,
  threads_started * 0.2,
  reactions_given * 0.1,
  mentions_by_others * 0.15
) / period_days

task_completion_score = weighted_sum(
  tasks_completed / tasks_assigned * 0.5,
  story_points_completed / story_points_total * 0.3,
  (1 - tasks_overdue / tasks_assigned) * 0.2
)

responsiveness_score = inverse_normalized(avg_response_time_minutes)

collaboration_score = weighted_sum(
  mentions_of_others * 0.3,
  threads_replied_to * 0.3,
  code_snippets_shared * 0.2,
  reactions_given * 0.2
) / period_days

overall_engagement_score = weighted_sum(
  communication_score * 0.30,
  task_completion_score * 0.35,
  responsiveness_score * 0.15,
  collaboration_score * 0.20
)
```

All scores are normalized to a 0-100 scale for comparability.

### Step 5: Cross-Source Correlation

The final step builds a unified person record by correlating all data from all sources into a single coherent profile.

**Identity Resolution Map:**

For each person, the system maintains a mapping:

```json
{
  "person_id": "person_raj_kumar",
  "identities": {
    "slack": {
      "user_id": "U04ABC123",
      "username": "raj.k",
      "display_name": "Raj K.",
      "real_name": "Raj Kumar",
      "email": "raj.kumar@company.com",
      "match_confidence": 1.0
    },
    "jira": {
      "username": "rkumar",
      "display_name": "Raj Kumar",
      "match_confidence": 0.95,
      "match_method": "fuzzy_name + email_confirmation"
    },
    "drive": {
      "email": "raj.kumar@company.com",
      "display_name": "Raj Kumar",
      "match_confidence": 1.0,
      "match_method": "exact_email"
    }
  },
  "canonical_name": "Raj Kumar",
  "canonical_email": "raj.kumar@company.com",
  "correlation_confidence": 0.98
}
```

**Cross-Source Behavior Correlation:**

The AI validates identity matches by checking behavioral consistency:

- Person "raj.k" in Slack discusses backend architecture + Person "rkumar" in Jira is assigned backend architecture tasks → behavioral correlation confirms identity match
- Person "raj.k" in Slack mentions "just finished the API endpoint" + Person "rkumar" in Jira moved task "Build user auth API" to Done on the same day → temporal correlation confirms identity match
- Person "Raj Kumar" in Drive authored "System Architecture v2.docx" + Person "raj.k" shared a link to that document in #engineering → direct correlation confirms identity match

---

## 3. People Directory

The People Intelligence pipeline produces a comprehensive people directory stored in MongoDB. This is the single source of truth for all people-related information in ChiefOps.

### MongoDB Collection: `people`

```json
{
  "_id": "person_raj_kumar",
  "organization_id": "org_yensi",
  "canonical_name": "Raj Kumar",
  "canonical_email": "raj.kumar@company.com",

  "identities": {
    "slack": {
      "user_id": "U04ABC123",
      "username": "raj.k",
      "display_name": "Raj K.",
      "real_name": "Raj Kumar",
      "email": "raj.kumar@company.com",
      "profile_image_url": "https://avatars.slack.com/...",
      "timezone": "Asia/Kolkata",
      "account_status": "active"
    },
    "jira": {
      "username": "rkumar",
      "display_name": "Raj Kumar"
    },
    "drive": {
      "email": "raj.kumar@company.com",
      "display_name": "Raj Kumar"
    }
  },

  "role": {
    "primary": {
      "title": "Backend Architect",
      "source": "ai_identified",
      "confidence": 0.88,
      "identified_at": "2025-02-15T10:30:00Z",
      "evidence_summary": "Leads architecture discussions, assigned architecture tasks, provides technical decisions"
    },
    "secondary": [
      {
        "title": "DevOps",
        "source": "ai_identified",
        "confidence": 0.62,
        "evidence_summary": "Discusses deployment pipelines, has CI/CD tasks"
      }
    ],
    "coo_corrections": [
      {
        "correction": "Raj is the lead architect, not a junior dev",
        "corrected_at": "2025-02-16T09:00:00Z",
        "previous_role": "Backend Developer",
        "new_role": "Backend Architect",
        "source": "coo_corrected"
      }
    ]
  },

  "skills": {
    "detected": ["Node.js", "MongoDB", "System Design", "AWS", "Docker", "CI/CD", "API Design"],
    "confidence_map": {
      "Node.js": 0.92,
      "MongoDB": 0.88,
      "System Design": 0.85,
      "AWS": 0.78,
      "Docker": 0.72,
      "CI/CD": 0.65,
      "API Design": 0.90
    }
  },

  "seniority": {
    "level": "Senior / Lead",
    "confidence": 0.82,
    "source": "ai_identified"
  },

  "projects": [
    {
      "project_id": "proj_alpha",
      "project_name": "Project Alpha",
      "role_in_project": "Technical Lead",
      "involvement_level": "primary",
      "tasks_assigned": 8,
      "tasks_completed": 5,
      "tasks_in_progress": 2,
      "activity_in_project_channels": "very_active"
    },
    {
      "project_id": "proj_beta",
      "project_name": "Project Beta",
      "role_in_project": "Advisor",
      "involvement_level": "secondary",
      "tasks_assigned": 1,
      "tasks_completed": 1,
      "tasks_in_progress": 0,
      "activity_in_project_channels": "moderate"
    }
  ],

  "tasks": {
    "formal_assignments": [
      {
        "jira_key": "PROJ-101",
        "title": "Design API authentication flow",
        "status": "Done",
        "source": "jira_csv"
      },
      {
        "jira_key": "PROJ-142",
        "title": "Implement rate limiting middleware",
        "status": "In Progress",
        "source": "jira_csv"
      }
    ],
    "informal_assignments": [
      {
        "assignment_id": "ia_001",
        "description": "Pick up PROJ-142 (blocking iOS release)",
        "jira_key": "PROJ-142",
        "assigned_by": "person_priya_deshpande",
        "detected_from": "slack_message",
        "channel": "#engineering",
        "timestamp": "2025-02-10T14:32:00Z",
        "confidence": 0.95
      },
      {
        "assignment_id": "ia_007",
        "description": "Set up staging environment for QA",
        "jira_key": null,
        "assigned_by": "self",
        "detected_from": "slack_message",
        "channel": "#devops",
        "timestamp": "2025-02-12T11:15:00Z",
        "confidence": 0.88
      }
    ]
  },

  "engagement": {
    "current_period": {
      "period_start": "2025-02-01",
      "period_end": "2025-02-15",
      "activity_level": "very_active",
      "overall_engagement_score": 87,
      "communication_score": 82,
      "task_completion_score": 91,
      "responsiveness_score": 78,
      "collaboration_score": 85
    },
    "trend": "stable",
    "trend_detail": "Consistently very active over the last 3 periods",
    "historical": [
      {
        "period": "2025-01-15 to 2025-01-31",
        "activity_level": "very_active",
        "overall_engagement_score": 85
      },
      {
        "period": "2025-01-01 to 2025-01-14",
        "activity_level": "active",
        "overall_engagement_score": 74
      }
    ]
  },

  "flags": [],

  "ai_summary": "Raj Kumar is the de facto backend architect for the organization. He is very active across Project Alpha (technical lead) and provides occasional guidance on Project Beta. He drives architecture discussions, provides code review feedback, and mentors junior developers. His task completion rate is strong at 91%. No concerns at this time.",

  "last_activity": {
    "slack": "2025-02-15T18:45:00Z",
    "jira": "2025-02-15T16:30:00Z",
    "drive": "2025-02-14T10:00:00Z"
  },

  "category": "internal",

  "created_at": "2025-02-15T10:30:00Z",
  "updated_at": "2025-02-16T09:00:00Z",
  "last_analysis_at": "2025-02-15T10:30:00Z"
}
```

### Flags System

Flags are automatically computed by the AI based on engagement metrics and task data. They surface potential concerns for the COO.

| Flag | Trigger Condition | Severity |
|------|-------------------|----------|
| `inactive` | No Slack messages for 5+ days AND no Jira updates | High |
| `going_quiet` | 50%+ drop in message volume compared to previous period | Medium |
| `overloaded` | 8+ tasks in progress simultaneously, or engagement score dropping while task count rises | High |
| `unassigned` | Person appears in Slack but has zero Jira tasks | Low |
| `single_point_of_failure` | Only person working on a critical component or project area | High |
| `blocked` | Multiple tasks not progressing despite active Slack presence | Medium |
| `role_uncertain` | AI role detection confidence below 60% | Low |
| `identity_unresolved` | Could not confidently match across data sources | Medium |
| `new_person` | First appearance in data — not seen in previous extracts | Info |
| `possible_departure` | Dramatic activity drop + increased activity in #general/#random but not project channels | High |

Flags are surfaced on the dashboard, in project deep-dives, and in generated reports. The COO can dismiss flags or act on them.

---

## 4. COO Corrections

The COO can correct ANY identification through natural language. This is a fundamental design principle: the AI's assessments are always provisional. The COO's corrections are definitive and override everything.

### Correction Types

| What COO Says | System Action |
|---------------|--------------|
| "Raj is the lead architect, not a junior dev" | Update role to "Lead Architect", set source to "coo_corrected", re-assess project summaries that mention Raj's role, update capacity analysis based on new seniority |
| "Priya handles backend, not frontend" | Update role/skills from frontend to backend, re-categorize her tasks in analysis, update project composition views |
| "Deepa and Raj are the same person" | Merge person records, consolidate all activity metrics, update all task assignments, recalculate engagement scores for merged profile |
| "PROJ-142 is actually assigned to Anil" | Update task assignment from current assignee to Anil, adjust workload views for both people, update project task distribution |
| "Mike is not part of Project Alpha" | Remove Mike from Project Alpha association, update project team composition, recalculate project-level metrics without Mike |
| "Sarah is a contractor, not a full-time employee" | Update category to "external_contractor", adjust expectations in analysis (different availability assumptions), flag in project views |
| "Ignore messages from the staging-bot user" | Add to bot/system user exclusion list, remove from people directory, recalculate metrics without those messages |
| "Anil left the company on Feb 10" | Mark as departed with end date, exclude post-departure activity from analysis, redistribute his open tasks as unassigned, flag for COO attention |

### Correction Cascade

When a correction is made, the system initiates a cascade of updates to ensure consistency across all data:

**Step 1: Update People Collection**
- Modify the person record in MongoDB with the correction
- Add the correction to the `coo_corrections` array with timestamp
- Update the `role.source` to "coo_corrected" where applicable
- Set `updated_at` to current timestamp

**Step 2: Store as Hard Fact in Memory System**
- Create a Hard Fact in the Citex memory system:
  ```json
  {
    "type": "hard_fact",
    "category": "people_correction",
    "content": "Raj Kumar's role is Lead Architect (corrected by COO from AI-identified Backend Developer)",
    "source": "coo_correction",
    "timestamp": "2025-02-16T09:00:00Z",
    "affects": ["person_raj_kumar"],
    "supersedes": ["ai_role_assessment_raj_kumar_20250215"]
  }
  ```
- Hard Facts override all AI-generated assessments in future analysis
- The AI will never re-assess a COO-corrected field unless the COO explicitly asks

**Step 3: Mark Affected Analyses as Stale**
- Identify all project summaries that reference the corrected person
- Identify all health scores that use the corrected data
- Identify all reports that include the corrected person
- Mark each as `stale: true` with `stale_reason: "coo_correction_cascade"`

**Step 4: Re-Run Affected Analyses**
- Regenerate project summaries for all affected projects
- Recalculate capacity analysis with updated role/workload
- Recalculate health scores with corrected data
- Regenerate any queued or draft reports

**Step 5: Update Dashboard Widgets**
- Push updates to any dashboard widgets showing affected data
- People directory widget refreshes
- Project team composition widget refreshes
- Workload distribution widget refreshes
- Activity timeline widget refreshes

**Step 6: AI Acknowledgment**
- The AI acknowledges the correction in the conversation:
  ```
  "Got it. I've updated Raj Kumar's role from Backend Developer to Lead Architect.
  This affects:
  - Project Alpha summary (Raj is now listed as technical lead, not a contributing developer)
  - Capacity analysis (lead architect level workload expectations applied)
  - 2 draft reports that referenced his previous role

  All affected analyses have been regenerated. The dashboard is updated."
  ```

### Correction Conflict Resolution

What happens when a COO correction conflicts with a previous correction:

| Scenario | Resolution |
|----------|-----------|
| COO says "Raj is a PM" then later says "Raj is an architect" | Latest correction wins. Previous correction is archived with `superseded: true`. |
| COO says "Deepa and Raj are the same person" then later says "Actually they are different people" | Reverse the merge. Restore separate records. Re-split activity metrics using AI best-effort assignment. Flag uncertain splits for COO review. |
| COO corrects something that contradicts data (e.g., "Raj is not on Project Alpha" but Raj has 15 tasks in Alpha) | Apply the correction but surface the contradiction: "I've removed Raj from Project Alpha. Note: he has 15 tasks assigned in Alpha in Jira. Should I reassign those or leave them as-is?" |

---

## 5. Activity Level Classification

Activity levels are computed from the engagement scores and raw metrics. They provide a quick, human-readable assessment of each person's engagement.

| Level | Criteria | Score Range | Visual Indicator |
|-------|----------|-------------|-----------------|
| **Very Active** | Multiple messages daily, tasks progressing ahead of schedule, leading discussions, starting threads, mentoring others | 80-100 | Green, solid circle |
| **Active** | Regular messages (most days), tasks moving on schedule, participating in threads, responding promptly | 60-79 | Green, open circle |
| **Moderate** | Occasional messages (few times per week), some task activity but not consistently progressing, responds when mentioned | 40-59 | Yellow, open circle |
| **Quiet** | Rare messages (once a week or less), minimal task updates, not initiating conversations — potential concern flag raised | 20-39 | Orange, warning icon |
| **Inactive** | No messages for 5+ days, no task updates, no file activity — alert raised for COO attention | 0-19 | Red, alert icon |

### Activity Level Transition Alerts

The system monitors transitions between activity levels:

| Transition | Alert Type | Example Message |
|-----------|-----------|-----------------|
| Active → Quiet | Warning | "Anil has gone quiet in the last 5 days. He was previously active with 8+ messages/day. He has 4 open tasks in Project Alpha." |
| Very Active → Moderate | Notice | "Priya's activity has decreased. She dropped from very active to moderate over the last week. Her task completion rate also dropped from 90% to 60%." |
| Inactive → Active | Positive | "Mike is back. He resumed activity yesterday after 8 days of inactivity." |
| Any → Inactive | Alert | "Deepa has been inactive for 7 days. Last seen in #engineering on Feb 8. She has 3 tasks in progress with no updates." |

### Engagement Trend Analysis

Beyond current activity level, the AI tracks trends:

- **Improving:** Score increasing over consecutive periods → no concern
- **Stable:** Score within +/- 10% of previous period → normal
- **Declining:** Score decreasing over 2+ consecutive periods → flag for attention
- **Volatile:** Score swings significantly between periods → investigate (could indicate personal issues, project transitions, or role change)

---

## 6. People in Project Context

When the COO views a project deep-dive, people are shown in the context of that specific project, not their overall organizational profile.

### Project Team View

For each person on a project team:

```json
{
  "person_id": "person_raj_kumar",
  "name": "Raj Kumar",
  "role_in_project": "Technical Lead / Backend Architect",
  "involvement_level": "primary",
  "tasks_in_project": {
    "total": 8,
    "completed": 5,
    "in_progress": 2,
    "not_started": 1,
    "overdue": 0,
    "completion_rate": 0.625
  },
  "activity_in_project_channels": {
    "level": "very_active",
    "messages_in_project_channels": 137,
    "threads_in_project_channels": 45,
    "primary_channels": ["#proj-alpha", "#proj-alpha-backend"]
  },
  "ai_assessment": "Raj is very active and driving architecture decisions for Project Alpha. He is the primary technical authority and has completed 5 of 8 tasks. His 2 in-progress tasks (PROJ-142: rate limiting, PROJ-156: caching layer) are both on track. No concerns.",
  "flags_in_project": []
}
```

### Meeting Expectations Assessment

For each person on each project, the AI assesses whether they are meeting expectations based on:

| Factor | Weight | How It Is Measured |
|--------|--------|--------------------|
| Task completion rate | 35% | Tasks completed / tasks assigned in this project |
| Task progression | 25% | Are in-progress tasks actually moving? (status changes, Slack mentions of progress) |
| Communication | 20% | Active in project channels, responding to threads, providing updates |
| Quality signals | 10% | Code review feedback tone, bug reports filed against their work, rework tasks |
| Deadline adherence | 10% | Tasks completed before/on/after due date |

Assessment levels:
- **Exceeding:** Completing ahead of schedule, high quality, proactive communication
- **Meeting:** On track, regular updates, tasks progressing normally
- **Partially Meeting:** Some delays, less communication than expected, 1-2 tasks slipping
- **Not Meeting:** Significant delays, multiple overdue tasks, minimal communication — flag for COO

### Project Team AI Summary

When the COO asks about a project, the AI generates a team summary:

```
Project Alpha Team Assessment:

- Raj Kumar (Backend Architect, Very Active): Driving architecture decisions.
  5/8 tasks complete, 2 in progress on track. No concerns.

- Priya Deshpande (PM, Active): Managing sprint effectively. All status
  updates on time. Good stakeholder communication.

- Anil Verma (iOS Developer, Quiet — ALERT): Has gone quiet in the last 5 days.
  His 4 remaining tasks are all iOS-specific and blocking the March release.
  Last seen in #proj-alpha on Feb 10. Recommend COO follow-up.

- Deepa Sharma (Frontend Developer, Active): Consistent output. 3/5 tasks
  complete. Frontend components on track for integration testing next week.

- Mike Chen (QA Engineer, Moderate): Fewer messages than usual. 2 test plans
  completed, 3 pending. May need support if iOS tasks are delayed.

Overall: Team is performing well except for Anil's recent inactivity, which
is a risk to the iOS deliverables. Recommend immediate attention.
```

---

## 7. People Queries

The COO can ask natural language questions about people and the system responds with relevant data, visualizations, and AI analysis.

### Supported Query Types

**Team Composition Queries:**
- "Who is working on Project Alpha?"
- "Show me the team for the backend migration"
- "Who are the developers on the iOS project?"
- "List everyone involved in the Q1 launch"

**Workload Queries:**
- "Who is overloaded right now?"
- "Who has the lightest workload?"
- "Show me the task distribution across the engineering team"
- "Who can take on more work?"
- "Give me a person vs. tasks chart for February"

**Individual Deep-Dive Queries:**
- "Show me Raj's task breakdown"
- "What is Priya working on right now?"
- "How has Anil's activity changed over the last month?"
- "What role does Deepa play across projects?"

**Activity & Engagement Queries:**
- "Who hasn't been active this week?"
- "Who are the most active contributors?"
- "Show me the activity levels for the whole team"
- "Has anyone's engagement dropped recently?"
- "Who are the key contributors to the backend work?"

**Risk & Alert Queries:**
- "Are there any people-related risks I should know about?"
- "Who might be a single point of failure?"
- "Are any team members blocked?"
- "Show me all people flagged with concerns"

**Comparison Queries:**
- "Compare Raj and Anil's task completion rates"
- "Who completed the most tasks this sprint?"
- "Show me a contribution breakdown by person for Project Alpha"

### Query Response Format

Every people query returns:
1. **Direct answer** — the specific information requested
2. **Supporting data** — numbers, metrics, task lists
3. **AI analysis** — context and interpretation
4. **Suggested follow-ups** — related questions the COO might want to ask
5. **Visualization** — chart or table if appropriate (rendered via Dashboard Widgets)

**Example Query and Response:**

COO asks: "Who is overloaded right now?"

```
Currently Overloaded Team Members:

1. Anil Verma — 11 tasks in progress across 2 projects
   - Project Alpha: 4 iOS tasks (all blocking March release)
   - Project Beta: 7 tasks (3 overdue)
   - Activity: Quiet (last 5 days)
   - Risk: High — too many tasks + declining activity suggests burnout or blockers

2. Deepa Sharma — 9 tasks in progress, 2 overdue
   - Project Alpha: 5 frontend tasks
   - Project Gamma: 4 tasks
   - Activity: Active, but responsiveness has dropped (avg reply time up from 15min to 2hrs)
   - Risk: Medium — still active but stretched thin

No one else exceeds the overload threshold (8+ concurrent tasks).

Suggested actions:
- Check in with Anil — his quiet period combined with high task count is concerning
- Consider redistributing some of Deepa's Project Gamma tasks
- Raj has capacity (3 tasks, all on track) and could support backend items

Would you like me to generate a workload distribution chart or drill into either person's task list?
```

---

## 8. Technical Implementation

### 8.1 AI Prompt for People Analysis

The core AI prompt for people analysis is structured as a multi-step chain. Here is the primary prompt template:

**Prompt: People Analysis from Data Extract**

```
You are an AI assistant analyzing organizational data to build a people intelligence profile. You have access to the following data sources for the organization.

=== SLACK DATA ===
The following is a set of Slack messages from the organization's channels.
Each message includes: channel name, author (display name and username), timestamp, message text.

{slack_messages_formatted}

=== JIRA DATA ===
The following is extracted from a Jira CSV export.
Each row includes: ticket key, summary, status, assignee, reporter, priority, labels, created date, updated date.

{jira_data_formatted}

=== GOOGLE DRIVE DATA ===
The following is metadata from Google Drive files.
Each entry includes: file name, owner, last modified by, last modified date, file type.

{drive_data_formatted}

=== EXISTING PEOPLE DIRECTORY ===
The following people have already been identified in previous analyses. Use this as a starting point and update/add as needed.

{existing_people_directory}

=== COO CORRECTIONS (HARD FACTS) ===
The following corrections have been made by the COO. These are DEFINITIVE and override any AI assessment. Do not contradict these.

{coo_corrections}

=== INSTRUCTIONS ===

Analyze all the data above and produce a comprehensive people analysis. For each person you can identify:

1. IDENTITY: Determine their canonical name and map their identities across data sources. Use fuzzy matching for names that don't exactly match. Flag any uncertain matches.

2. ROLE: Based on their messages, tasks, and behavior patterns, determine their role(s) in the organization. Provide evidence for your assessment and a confidence level (0.0 to 1.0). Respect any COO corrections — if the COO has specified a role, use that with confidence 1.0.

3. INFORMAL ASSIGNMENTS: Scan Slack messages for informal task assignments — people being asked to pick up work, volunteering for tasks, or being referenced as working on something. Link to Jira tickets where possible.

4. ENGAGEMENT: Assess each person's activity level based on message frequency, task completion, responsiveness, and collaboration patterns. Classify as: very_active, active, moderate, quiet, or inactive.

5. FLAGS: Identify any concerns — inactive team members, overloaded individuals, single points of failure, role uncertainties, identity ambiguities.

6. PROJECT ASSOCIATIONS: Determine which projects each person is involved in, their role in each project, and their level of involvement.

7. AI SUMMARY: Write a 2-3 sentence human-readable summary of each person's current status, contributions, and any concerns.

=== OUTPUT FORMAT ===

Return a JSON array of person objects with the following structure:

[
  {
    "person_id": "person_{first_name}_{last_name}",
    "canonical_name": "Full Name",
    "canonical_email": "email@company.com or null",
    "identities": { ... },
    "role": {
      "primary": {
        "title": "Role Title",
        "confidence": 0.0-1.0,
        "evidence": ["evidence point 1", "evidence point 2"],
        "source": "ai_identified | coo_corrected"
      },
      "secondary": [ ... ]
    },
    "skills_detected": ["skill1", "skill2"],
    "seniority": { "level": "Junior | Mid | Senior | Lead", "confidence": 0.0-1.0 },
    "informal_assignments": [ ... ],
    "engagement": {
      "activity_level": "very_active | active | moderate | quiet | inactive",
      "overall_score": 0-100,
      "communication_score": 0-100,
      "task_completion_score": 0-100,
      "trend": "improving | stable | declining | volatile"
    },
    "projects": [ ... ],
    "flags": ["flag_type_1", "flag_type_2"],
    "ai_summary": "2-3 sentence summary"
  }
]

Be thorough. Identify everyone you can from the data, even if they have minimal activity. If you are uncertain about something, say so with a lower confidence score rather than omitting it.
```

**Prompt: Incremental Update**

For subsequent data extracts (not full re-analysis), a lighter prompt is used:

```
You are updating the people intelligence for this organization. Below is the existing people directory and NEW data that has been added since the last analysis.

=== EXISTING DIRECTORY ===
{existing_people_directory}

=== NEW DATA ===
{new_slack_messages}
{new_jira_data}
{new_drive_data}

=== COO CORRECTIONS SINCE LAST ANALYSIS ===
{new_coo_corrections}

=== INSTRUCTIONS ===

1. Update engagement metrics for all people based on new data
2. Identify any NEW people not in the existing directory
3. Detect any role changes suggested by new data (but do not override COO corrections)
4. Detect new informal assignments from new Slack messages
5. Update flags based on latest activity
6. Update AI summaries where significant changes occurred

Return ONLY the changes — do not repeat unchanged data. Use the following format:

{
  "new_people": [ ... ],
  "updated_people": [
    {
      "person_id": "person_raj_kumar",
      "changes": {
        "engagement": { ... updated fields ... },
        "new_informal_assignments": [ ... ],
        "flags_added": [ ... ],
        "flags_removed": [ ... ],
        "ai_summary": "updated summary if changed"
      }
    }
  ],
  "identity_merge_suggestions": [ ... ],
  "alerts": [ ... ]
}
```

### 8.2 Fuzzy Name Matching

The fuzzy matching system uses a three-stage approach for resolving person identities across data sources.

**Stage 1: Exact Matching**

```python
def exact_match(name_a: str, name_b: str) -> bool:
    """Case-insensitive exact match after normalization."""
    normalized_a = normalize_name(name_a)
    normalized_b = normalize_name(name_b)
    return normalized_a == normalized_b

def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    name = name.strip().lower()
    name = re.sub(r'[._\-]', ' ', name)  # Replace separators with spaces
    name = re.sub(r'\s+', ' ', name)       # Collapse multiple spaces
    return name
```

**Stage 2: Fuzzy String Matching (using rapidfuzz)**

```python
from rapidfuzz import fuzz, process

def fuzzy_match_names(name_a: str, name_b: str) -> dict:
    """
    Returns match scores using multiple fuzzy matching strategies.
    """
    normalized_a = normalize_name(name_a)
    normalized_b = normalize_name(name_b)

    scores = {
        "simple_ratio": fuzz.ratio(normalized_a, normalized_b),
        "partial_ratio": fuzz.partial_ratio(normalized_a, normalized_b),
        "token_sort_ratio": fuzz.token_sort_ratio(normalized_a, normalized_b),
        "token_set_ratio": fuzz.token_set_ratio(normalized_a, normalized_b),
    }

    # Weighted composite score
    scores["composite"] = (
        scores["simple_ratio"] * 0.2 +
        scores["partial_ratio"] * 0.3 +
        scores["token_sort_ratio"] * 0.25 +
        scores["token_set_ratio"] * 0.25
    )

    return scores

# Matching thresholds:
# composite >= 95  → auto-match (very high confidence)
# composite >= 80  → probable match (flag for AI confirmation)
# composite >= 60  → possible match (flag for AI + COO confirmation)
# composite < 60   → no match
```

**Stage 3: AI-Assisted Disambiguation**

For matches in the 60-95% range, the AI is given both names along with their activity context and asked to confirm or deny the match:

```
Are these the same person?

Person A:
- Name: "Raj K." (from Slack)
- Active in: #engineering, #proj-alpha
- Discusses: backend architecture, Node.js, MongoDB
- Messages: 187 in the last 2 weeks

Person B:
- Name: "Raj Kumar" (from Jira)
- Assigned tasks: Backend API development, architecture documentation
- Labels on tasks: backend, architecture, api

Fuzzy match score: 85%

Based on the name similarity AND behavioral/topical overlap, are these the same person?
Respond with: { "same_person": true/false, "confidence": 0.0-1.0, "reasoning": "..." }
```

**Email-Based Matching:**

When email addresses are available, they take priority:

```python
def email_match(email_a: str, email_b: str) -> bool:
    """Email match is definitive."""
    if email_a and email_b:
        return email_a.strip().lower() == email_b.strip().lower()
    return False

def email_username_to_name(email: str) -> str:
    """Extract likely name from email: raj.kumar@company.com -> Raj Kumar"""
    username = email.split('@')[0]
    parts = re.split(r'[._\-]', username)
    return ' '.join(part.capitalize() for part in parts)
```

### 8.3 Activity Scoring

**Raw Metric Collection:**

Activity scoring begins with collecting raw metrics from each data source. The collection functions operate per person per time period.

```python
def collect_slack_metrics(person_id: str, messages: list, period: tuple) -> dict:
    """Collect Slack activity metrics for a person in a time period."""
    person_messages = [m for m in messages
                       if m['author_id'] == person_id
                       and period[0] <= m['timestamp'] <= period[1]]

    return {
        "total_messages": len(person_messages),
        "messages_by_channel": Counter(m['channel'] for m in person_messages),
        "threads_started": count_thread_starts(person_messages),
        "threads_replied_to": count_thread_replies(person_messages),
        "reactions_given": count_reactions_given(person_id, messages, period),
        "reactions_received": count_reactions_received(person_id, messages, period),
        "mentions_of_others": count_outgoing_mentions(person_messages),
        "mentions_by_others": count_incoming_mentions(person_id, messages, period),
        "code_snippets_shared": count_code_blocks(person_messages),
        "files_shared": count_file_shares(person_messages),
        "active_days": count_active_days(person_messages),
        "avg_response_time_minutes": calculate_avg_response_time(
            person_id, messages, period
        ),
    }
```

**Score Normalization:**

All raw metrics are normalized to a 0-100 scale using percentile-based normalization within the organization. This ensures scores are relative to the team, not absolute.

```python
def normalize_score(value: float, all_values: list) -> float:
    """
    Normalize a value to 0-100 based on its percentile in the distribution.
    This means "50" is average for this team, not an absolute measure.
    """
    if not all_values or max(all_values) == min(all_values):
        return 50.0  # Default to middle if no distribution

    sorted_values = sorted(all_values)
    percentile = bisect_left(sorted_values, value) / len(sorted_values)
    return round(percentile * 100, 1)
```

**Activity Level Thresholds:**

After computing the overall engagement score (0-100):

```python
def classify_activity_level(score: float, days_since_last_activity: int) -> str:
    """
    Classify activity level from engagement score.
    days_since_last_activity overrides score-based classification.
    """
    # Inactivity override
    if days_since_last_activity >= 5:
        return "inactive"

    if days_since_last_activity >= 3 and score < 40:
        return "inactive"

    # Score-based classification
    if score >= 80:
        return "very_active"
    elif score >= 60:
        return "active"
    elif score >= 40:
        return "moderate"
    elif score >= 20:
        return "quiet"
    else:
        return "inactive"
```

**Trend Calculation:**

```python
def calculate_trend(current_score: float, historical_scores: list) -> str:
    """
    Determine engagement trend from current and historical scores.
    historical_scores is ordered oldest-first.
    """
    if len(historical_scores) < 2:
        return "stable"  # Not enough data for trend

    recent_scores = historical_scores[-3:] + [current_score]

    # Calculate direction using linear regression slope
    slope = calculate_slope(recent_scores)

    # Calculate volatility
    std_dev = statistics.stdev(recent_scores)

    if std_dev > 20:
        return "volatile"
    elif slope > 5:
        return "improving"
    elif slope < -5:
        return "declining"
    else:
        return "stable"
```

### 8.4 Re-analysis Triggers

The people intelligence data is re-analyzed when any of the following events occur:

| Trigger | What Happens | Scope |
|---------|-------------|-------|
| **New data extract uploaded** | Full pipeline re-run: identity resolution, role detection, engagement scoring, flag computation | All people in the new data |
| **COO correction made** | Targeted update: apply correction, cascade to affected analyses, regenerate summaries | Affected person + affected projects |
| **Manual re-analysis request** | Full pipeline re-run on existing data (useful after multiple corrections or when the COO wants a fresh assessment) | All people |
| **Time-based refresh** | If no new data has been uploaded for 7+ days, the system alerts the COO that data may be stale (no automatic re-analysis without new data) | N/A — alert only |
| **Person merge/split** | When identities are merged or split, re-run engagement scoring and project association for affected records | Affected person(s) |
| **Project scope change** | When project boundaries change (new channels added, tasks re-categorized), re-assess people's project associations | All people on affected project |

**Re-analysis Priority Queue:**

When multiple triggers fire simultaneously, they are prioritized:

1. COO corrections (immediate — within seconds)
2. Person merge/split (immediate — within seconds)
3. New data extract (queued — may take minutes for large extracts)
4. Manual re-analysis (queued — may take minutes)
5. Project scope change (queued — lower priority)

---

## 9. Edge Cases

People intelligence must handle ambiguous, messy, real-world data. The following edge cases are explicitly addressed.

### 9.1 Same Name, Different People (Disambiguation)

**Problem:** Two people named "Raj" appear in the data.

**Detection:**
- Same name appears with different email addresses
- Same name appears in conflicting contexts (one "Raj" discusses iOS in #mobile, another "Raj" discusses backend in #engineering)
- Slack user IDs differ but display names match

**Resolution:**
1. If email addresses are available, use them as the primary disambiguator
2. If only Slack data, use user IDs — each Slack user has a unique ID regardless of display name
3. If Jira has two "Raj Kumar" entries with different task types, the AI separates them based on task domain
4. Create separate person records: `person_raj_kumar_backend` and `person_raj_kumar_ios`
5. Flag both records with `disambiguation_needed` for COO confirmation
6. AI presents the ambiguity: "I found two people who might both be named Raj Kumar. One is active in backend/architecture channels, the other in iOS/mobile channels. Are these different people?"

### 9.2 External Contractors/Vendors in Slack

**Problem:** The Slack workspace includes contractors, vendors, or clients who are not employees.

**Detection:**
- Email domain differs from the company domain (e.g., `@contractor-agency.com` vs `@company.com`)
- Limited channel access (only in 1-2 specific channels)
- Referenced as "contractor" or "vendor" in messages
- No Jira tasks assigned (or assigned under a different system)
- Very specific, narrow discussion topics

**Resolution:**
1. Mark as `category: "external_contractor"` or `category: "vendor"` in the people record
2. Include in people directory but with a visual distinction on the dashboard
3. Engagement metrics are tracked but not compared against internal employee benchmarks
4. Do not include in internal workload distribution or capacity analysis unless COO requests it
5. Flag: "This person appears to be an external contractor based on their email domain and limited channel access. Should I include them in team analysis?"

### 9.3 Bot Messages in Slack

**Problem:** Slack exports include messages from bots (Jira bot, GitHub bot, Slackbot, deployment bots, etc.) which should not be treated as people.

**Detection:**
- Slack user profile has `is_bot: true`
- Username contains "bot" (case-insensitive): `jirabot`, `github-bot`, `deploy-bot`
- Messages follow rigid templates (always the same structure with variable fields)
- No human-like conversation patterns (no replies to threads, no reactions, no natural language)
- Slack subtype fields indicate integration messages

**Resolution:**
1. Exclude bots from the people directory entirely
2. Do NOT count bot messages in any engagement metrics
3. Do NOT attribute bot-posted messages to the person who triggered them (e.g., Jira bot posting a status update should not be counted as a message from the person who changed the Jira ticket)
4. Maintain a bot exclusion list that can be edited by the COO
5. If uncertain whether an account is a bot, flag for COO confirmation: "The account 'deploy-notify' posts only automated deployment messages. Should I treat this as a bot and exclude from people analysis?"

### 9.4 Shared Jira Accounts

**Problem:** Some organizations use shared Jira accounts (e.g., "dev-team" or "qa-team") for certain tasks.

**Detection:**
- A Jira username is assigned an unusually high number of tasks across unrelated domains
- The assignee name is generic (e.g., "Dev Team", "QA", "Support")
- Multiple Slack users reference tasks assigned to the same Jira account as "mine"

**Resolution:**
1. Flag the shared account: "The Jira account 'dev-team' has 34 tasks assigned. This appears to be a shared account. Can you help me understand who actually owns these tasks?"
2. Do not create a person record for the shared account
3. Instead, attempt to resolve actual ownership using Slack context:
   - "I'm working on PROJ-234" from Raj → assign PROJ-234 (currently under "dev-team") to Raj informally
4. Tasks that cannot be resolved to an individual remain flagged as `assignee_ambiguous`
5. Store the shared account info so the AI does not repeatedly try to create a person for it

### 9.5 People Who Left the Company Mid-Period

**Problem:** Someone was active in the first week of the data extract period but then left the company.

**Detection:**
- Sudden complete stop of all activity (messages, tasks, file edits) on a specific date
- Slack account status changed to `deactivated`
- Messages from others referencing their departure: "Since [name] left...", "[name]'s last day was..."
- Tasks reassigned around the same date

**Resolution:**
1. Mark the person with `status: "departed"` and `departure_date` if detectable
2. Include their activity up to the departure date in historical metrics
3. Do NOT flag them as "inactive" — that would be misleading. Instead, flag as "departed"
4. Redistribute their open tasks as `unassigned` in the project view
5. Alert the COO: "[Name] appears to have left the organization around [date]. They have [N] open tasks that are now unassigned. Would you like to review these?"
6. Exclude post-departure dates from engagement trend calculations

### 9.6 Name Changes

**Problem:** A person changes their display name in Slack (e.g., after marriage, or just updating their profile).

**Detection:**
- Same Slack user ID but display name changed between exports
- AI detects the old name and new name have the same user ID and communication patterns

**Resolution:**
1. Update canonical name to the new name
2. Keep old name as an alias for historical reference
3. Do not create a duplicate person record
4. Log the name change with timestamp

### 9.7 People Active in Only One Source

**Problem:** Someone appears in Slack but has no Jira tasks and no Drive activity, or vice versa.

**Detection:**
- Person record has only one source in the `identities` map
- No cross-source matches found

**Resolution:**
1. Create a person record with the available data
2. Flag as `single_source: true`
3. Lower confidence on role detection (fewer signals available)
4. Note in AI summary: "Raj appears only in Slack data. No matching Jira or Drive records found. Role assessment is based solely on Slack messages and has lower confidence."
5. Present to COO for enrichment: "I could only find [name] in Slack. Do they have a different name in Jira or Drive?"

### 9.8 Very Large Teams

**Problem:** An organization with 150+ people generates a massive people directory that is hard to navigate.

**Resolution:**
1. Group people by project, team, or department
2. Default views show only the COO's direct focus areas
3. Provide filtering: "Show me only people on Project Alpha" or "Show me only flagged people"
4. Pagination in the API and dashboard
5. Summary statistics at the top: "152 people identified. 12 flagged. 3 inactive."

### 9.9 Conflicting Role Signals

**Problem:** Data suggests conflicting roles — someone discusses both frontend and backend, or their Jira tasks span multiple disciplines.

**Resolution:**
1. Assign a primary role based on the strongest signal
2. Assign secondary roles for the other signals
3. Lower confidence for both if the conflict is strong
4. Note in AI summary: "Deepa shows strong signals for both frontend and backend work. She may be a full-stack developer, or she may be transitioning between roles. Confidence in primary role (Frontend Developer) is 65%."
5. Flag as `role_uncertain` for COO clarification

### 9.10 Timezone Spread

**Problem:** Team members are in different timezones, which affects how "activity" is measured.

**Resolution:**
1. Normalize all timestamps to UTC for storage
2. Use each person's timezone (from Slack profile) when calculating "active hours" and "active days"
3. Do not penalize someone for being "inactive" during hours outside their timezone's working hours
4. Note timezone in the people directory for COO awareness
5. When comparing engagement across people, account for timezone differences in responsiveness metrics

---

## 10. Data Flow Summary

The complete people intelligence data flow:

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                  │
│  │  Slack    │  │  Jira    │  │ Google Drive │                  │
│  │  Export   │  │  CSV     │  │  Metadata    │                  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘                  │
│       │              │               │                          │
└───────┼──────────────┼───────────────┼──────────────────────────┘
        │              │               │
        ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: BUILD INITIAL DIRECTORY                    │
│  Extract names, usernames, emails from all sources              │
│  Fuzzy match across sources (rapidfuzz + AI confirmation)       │
│  Output: Raw person records with cross-source identity map      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 2: ROLE DETECTION (AI)                        │
│  Analyze message content, task types, behavioral patterns       │
│  Produce role assessment with confidence + evidence             │
│  Detect skills and seniority level                              │
│  Apply COO corrections as overrides                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│         STEP 3: INFORMAL ASSIGNMENT DETECTION (AI)              │
│  Scan Slack for assignment patterns                             │
│  Link informal assignments to Jira tickets where possible       │
│  Detect untracked work (assignments with no Jira match)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 4: ENGAGEMENT TRACKING                        │
│  Collect raw metrics from all sources                           │
│  Calculate derived engagement scores                            │
│  Classify activity levels                                       │
│  Compute trends (improving / stable / declining / volatile)     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│         STEP 5: CROSS-SOURCE CORRELATION                        │
│  Build unified person records                                   │
│  Validate identity matches via behavioral correlation           │
│  Generate AI summaries for each person                          │
│  Compute flags (inactive, overloaded, etc.)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PEOPLE DIRECTORY                              │
│              (MongoDB: people collection)                        │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │ Identity Map│  │ Role + Skills │  │ Engagement Data │        │
│  └─────────────┘  └──────────────┘  └─────────────────┘        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │ Task Assign.│  │ Project Assoc│  │ Flags + Alerts  │        │
│  └─────────────┘  └──────────────┘  └─────────────────┘        │
│  ┌─────────────┐                                                │
│  │ AI Summary  │                                                │
│  └─────────────┘                                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────┐
        │Dashboard │ │  NL Chat │ │   Reports    │
        │ Widgets  │ │ Queries  │ │ (PDF/Export) │
        └──────────┘ └──────────┘ └──────────────┘
              ▲
              │
    ┌─────────┴──────────┐
    │   COO Corrections  │
    │   (Natural Language)│
    │                    │
    │   Triggers cascade:│
    │   Update → Store → │
    │   Stale → Re-run → │
    │   Refresh → Ack    │
    └────────────────────┘
```

---

## 11. Integration Points

People Intelligence connects to every other subsystem in ChiefOps:

| Subsystem | How People Intelligence Integrates |
|-----------|-----------------------------------|
| **File Ingestion** (08) | Receives parsed data from Slack, Jira, Drive ingestion. Triggers people pipeline when new data arrives. |
| **Memory System** (04) | Stores COO corrections as Hard Facts. Reads existing Hard Facts during analysis to respect previous corrections. |
| **Citex Integration** (05) | People data is stored and retrieved via Citex. Semantic search on people summaries. |
| **AI Layer** (06) | Uses AI adapter for role detection, informal assignment detection, fuzzy matching confirmation, and summary generation. |
| **Report Generation** (07) | Provides people data for team composition sections, workload charts, and contributor summaries in reports. |
| **Dashboard & Widgets** (10) | Powers people directory widget, team composition widget, activity level widget, workload distribution widget. |

---

## 12. Performance Considerations

| Operation | Expected Duration | Notes |
|-----------|------------------|-------|
| Initial directory build (150 people) | 5-10 seconds | Pure data extraction, no AI |
| Fuzzy matching (150 people across 3 sources) | 2-5 seconds | rapidfuzz is fast; AI calls only for ambiguous cases |
| Role detection (150 people) | 30-60 seconds | Batched AI calls; 10-15 people per prompt to stay within context limits |
| Informal assignment detection (10,000 messages) | 20-40 seconds | Messages batched by channel; AI scans for patterns |
| Engagement scoring (150 people) | 3-5 seconds | Pure computation, no AI |
| Full pipeline (initial run, 150 people) | 1-2 minutes | All steps sequential |
| Incremental update (new extract, 150 people) | 30-60 seconds | Only processes delta |
| COO correction cascade | 5-15 seconds | Targeted update, not full re-run |

For organizations larger than 200 people, the AI analysis steps are parallelized across multiple batches to keep total pipeline time under 3 minutes.

---

*People Intelligence is the core differentiator of ChiefOps. Every other feature — project health, reports, dashboards — depends on accurate people identification. Getting this right is the foundation for everything else.*
