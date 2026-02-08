"""
Project analysis prompts for status assessment, gap detection,
backward planning, and feasibility analysis.
"""

from __future__ import annotations

from .base import PromptTemplate

# ---------------------------------------------------------------------------
# Comprehensive project status assessment
# ---------------------------------------------------------------------------

PROJECT_ANALYSIS_PROMPT = PromptTemplate(
    name="project_analysis",
    template="""\
You are performing a comprehensive status assessment of a project for the COO.

Analyse ALL of the provided project data and produce a structured assessment \
covering:

1. **Overall status**: Classify as "on_track", "at_risk", or "blocked".
2. **Health score**: A float from 0.0 (critical) to 1.0 (perfect health). Consider:
   - Schedule adherence (planned vs actual progress)
   - Resource availability and utilisation
   - Blocker count and severity
   - Dependency health
   - Team velocity trends
3. **Summary**: A 3-5 sentence narrative summary suitable for an executive audience. \
Lead with the most important finding.
4. **Timeline**: Planned end date, projected end date based on current velocity, and \
the variance in working days.
5. **Blockers**: Every active blocker with owner, severity (critical/high/medium/low), \
and days blocked.
6. **Risks**: Identified risks with probability (low/medium/high), impact \
(low/medium/high), and a concrete mitigation action.
7. **Recommendations**: 3-5 prioritised, actionable recommendations. Each should be \
a single sentence starting with an action verb.

Project name: {project_name}
Project deadline: {project_deadline}
Current date: {current_date}

Project data:
{project_data}

Team members and their recent activity:
{team_data}

Related alerts and notifications:
{alert_data}

You MUST respond with valid JSON matching this schema:
{{
  "project_name": "<string>",
  "overall_status": "<string: on_track|at_risk|blocked>",
  "health_score": <float: 0.0-1.0>,
  "summary": "<string: 3-5 sentence executive summary>",
  "timeline": {{
    "planned_end": "<string: ISO date>",
    "projected_end": "<string: ISO date>",
    "variance_days": <integer>
  }},
  "blockers": [
    {{
      "description": "<string>",
      "owner": "<string>",
      "severity": "<string: critical|high|medium|low>",
      "days_blocked": <integer>
    }}
  ],
  "risks": [
    {{
      "description": "<string>",
      "probability": "<string: low|medium|high>",
      "impact": "<string: low|medium|high>",
      "mitigation": "<string>"
    }}
  ],
  "recommendations": ["<string: actionable recommendation>", ...]
}}
""",
)

# ---------------------------------------------------------------------------
# Gap detection: identify missing tasks and prerequisites
# ---------------------------------------------------------------------------

GAP_DETECTION_PROMPT = PromptTemplate(
    name="gap_detection",
    template="""\
You are performing a gap analysis on a project plan to identify missing tasks, \
prerequisites, and communication steps that are needed but not present.

For each gap you identify, categorise it as:
- "missing_task": A work item that should exist but does not.
- "missing_prerequisite": A dependency or precondition that is not tracked.
- "missing_communication": A stakeholder notification, approval, or handoff that \
is not planned.
- "missing_test": A validation, QA, or acceptance step that is absent.
- "missing_documentation": A required document, runbook, or knowledge article that \
has not been created.

For each gap, provide:
1. A clear description of what is missing.
2. Severity: "critical" (project cannot succeed without it), "high" (significant \
risk if omitted), "medium" (best practice), "low" (nice to have).
3. A concrete recommendation for addressing it.
4. A suggested owner based on team roles.
5. Estimated effort in hours.

Also provide:
- A coverage score (0.0 to 1.0) representing how complete the current plan is.
- Whether the critical path appears complete (boolean).

Project name: {project_name}
Project deadline: {project_deadline}
Current date: {current_date}

Project plan (milestones and tasks):
{project_plan}

Team members and roles:
{team_data}

Industry best practices for this type of project:
{best_practices}

You MUST respond with valid JSON matching this schema:
{{
  "gaps": [
    {{
      "type": "<string: missing_task|missing_prerequisite|missing_communication|missing_test|missing_documentation>",
      "description": "<string>",
      "severity": "<string: critical|high|medium|low>",
      "recommendation": "<string>",
      "suggested_owner": "<string>",
      "estimated_effort_hours": <number>
    }}
  ],
  "coverage_score": <float: 0.0-1.0>,
  "critical_path_complete": <boolean>
}}
""",
)

# ---------------------------------------------------------------------------
# Backward planning: work backward from a deadline
# ---------------------------------------------------------------------------

BACKWARD_PLANNING_PROMPT = PromptTemplate(
    name="backward_planning",
    template="""\
You are creating a backward plan from a fixed deadline. The COO has specified a \
hard deadline and you need to work backward to determine when each phase and \
milestone must start and complete.

Rules for backward planning:
1. Start from the deadline and work backward through each required phase.
2. Include buffer time (typically 10-15% of phase duration) for each phase.
3. Account for dependencies between phases -- a phase cannot start until its \
prerequisites are complete.
4. Flag any phase whose required start date is in the past (meaning the deadline \
is infeasible at current pace).
5. Consider team capacity: if the team is also working on other projects, account \
for reduced availability.
6. Include non-working days (weekends, known holidays) in the timeline.

Project name: {project_name}
Hard deadline: {deadline}
Current date: {current_date}

Deliverables and requirements:
{deliverables}

Team members and their current allocation:
{team_data}

Known constraints (holidays, freezes, dependencies):
{constraints}

You MUST respond with valid JSON matching this schema:
{{
  "project_name": "<string>",
  "deadline": "<string: ISO date>",
  "feasible": <boolean>,
  "phases": [
    {{
      "name": "<string>",
      "description": "<string>",
      "duration_days": <integer>,
      "buffer_days": <integer>,
      "start_date": "<string: ISO date>",
      "end_date": "<string: ISO date>",
      "dependencies": ["<string: phase name>", ...],
      "assigned_to": ["<string: person name>", ...],
      "is_past_due": <boolean>
    }}
  ],
  "critical_path": ["<string: phase name in order>", ...],
  "earliest_feasible_start": "<string: ISO date>",
  "warnings": ["<string: any feasibility concerns>", ...]
}}
""",
)

# ---------------------------------------------------------------------------
# Feasibility analysis: technical feasibility and architect questions
# ---------------------------------------------------------------------------

FEASIBILITY_PROMPT = PromptTemplate(
    name="feasibility_analysis",
    template="""\
You are evaluating the technical feasibility of a proposed project or feature. \
The COO wants to understand whether this is achievable with the current team, \
technology stack, and timeline.

Evaluate along these dimensions:
1. **Technical complexity**: How hard is this to build? Are there known solutions \
or is this novel?
2. **Team capability**: Does the current team have the skills and experience to \
deliver this? What skill gaps exist?
3. **Timeline realism**: Can this be delivered in the proposed timeframe given the \
team size and complexity?
4. **Infrastructure readiness**: Are the required systems, environments, and tools \
in place?
5. **Risk factors**: What could go wrong technically? What are the unknowns?
6. **Architect questions**: What questions should be answered before committing to \
this project? List specific technical questions that need investigation.

For the overall assessment, provide:
- A feasibility rating: "highly_feasible", "feasible_with_caveats", \
"challenging", or "infeasible".
- A confidence level (0.0 to 1.0) in your assessment.

Proposed project or feature:
{proposal}

Current technology stack:
{tech_stack}

Team skills and experience:
{team_capabilities}

Proposed timeline:
{timeline}

Existing systems and infrastructure:
{infrastructure}

You MUST respond with valid JSON matching this schema:
{{
  "feasibility_rating": "<string: highly_feasible|feasible_with_caveats|challenging|infeasible>",
  "confidence": <float: 0.0-1.0>,
  "summary": "<string: 2-3 sentence executive summary>",
  "dimensions": {{
    "technical_complexity": {{
      "rating": "<string: low|medium|high|very_high>",
      "notes": "<string>"
    }},
    "team_capability": {{
      "rating": "<string: strong|adequate|gaps_exist|insufficient>",
      "skill_gaps": ["<string>", ...],
      "notes": "<string>"
    }},
    "timeline_realism": {{
      "rating": "<string: comfortable|tight|aggressive|unrealistic>",
      "recommended_duration": "<string: e.g. '12 weeks'>",
      "notes": "<string>"
    }},
    "infrastructure_readiness": {{
      "rating": "<string: ready|mostly_ready|needs_work|not_ready>",
      "missing_components": ["<string>", ...],
      "notes": "<string>"
    }}
  }},
  "risks": [
    {{
      "description": "<string>",
      "probability": "<string: low|medium|high>",
      "impact": "<string: low|medium|high>",
      "mitigation": "<string>"
    }}
  ],
  "architect_questions": [
    "<string: specific technical question that needs investigation>"
  ],
  "recommendations": ["<string: actionable recommendation>", ...]
}}
""",
)
