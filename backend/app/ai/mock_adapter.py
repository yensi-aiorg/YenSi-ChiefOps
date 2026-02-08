"""
Mock AI adapter for testing, development, and demo environments.

Returns intelligent pre-structured responses based on pattern-matching
against the system prompt content.  No external calls are made.
"""

from __future__ import annotations

import json
import logging
import re
import time

from .adapter import AIAdapter, AIRequest, AIResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixture responses keyed by pattern found in the system_prompt
# ---------------------------------------------------------------------------

_INTENT_RESPONSE = json.dumps(
    {
        "intent": "query",
        "confidence": 0.92,
        "sub_type": "project_status",
        "extracted_entities": {
            "project_name": "Platform Migration",
            "time_range": "this week",
        },
        "parameters": {
            "include_people": True,
            "include_timeline": True,
        },
        "reasoning": (
            "The user is asking about the current status of a specific project. "
            "This is a read-only data query, not a command or correction."
        ),
    },
    indent=2,
)

_PEOPLE_IDENTIFICATION_RESPONSE = json.dumps(
    {
        "people": [
            {
                "name": "Sarah Chen",
                "role": "Engineering Lead",
                "department": "Platform Engineering",
                "confidence": 0.95,
                "activity_summary": "Led 12 pull requests merged this sprint, reviewed 8 others. "
                "Primary contributor to the authentication service refactor.",
                "risk_indicators": [],
            },
            {
                "name": "Marcus Rivera",
                "role": "Senior Backend Developer",
                "department": "Platform Engineering",
                "confidence": 0.88,
                "activity_summary": "Completed 3 Jira tickets (PLAT-401, PLAT-415, PLAT-422). "
                "Blocked on PLAT-430 pending DevOps approval for staging deploy.",
                "risk_indicators": ["blocked_task"],
            },
        ],
        "unresolved_references": [],
    },
    indent=2,
)

_ROLE_DETECTION_RESPONSE = json.dumps(
    {
        "detected_role": "Engineering Lead",
        "confidence": 0.91,
        "evidence": [
            "Consistently reviews pull requests from multiple team members",
            "Participates in architecture decision records",
            "Tagged as approver on deployment workflows",
            "Mentioned in sprint retrospective notes as tech lead",
        ],
        "alternative_roles": [
            {"role": "Staff Engineer", "confidence": 0.65},
            {"role": "Tech Lead", "confidence": 0.58},
        ],
        "seniority_level": "senior",
    },
    indent=2,
)

_PROJECT_ANALYSIS_RESPONSE = json.dumps(
    {
        "project_name": "Platform Migration",
        "overall_status": "at_risk",
        "health_score": 0.62,
        "summary": (
            "The Platform Migration project is behind schedule by approximately 8 working days. "
            "Phase 2 (data migration) completed on time, but Phase 3 (service cutover) has been "
            "delayed due to unresolved dependency on the new auth service. Two critical path items "
            "remain unassigned."
        ),
        "timeline": {
            "planned_end": "2026-03-15",
            "projected_end": "2026-03-28",
            "variance_days": 13,
        },
        "blockers": [
            {
                "description": "Auth service v2 API contract not finalized",
                "owner": "Sarah Chen",
                "severity": "critical",
                "days_blocked": 5,
            },
            {
                "description": "Staging environment capacity insufficient for load test",
                "owner": "DevOps Team",
                "severity": "high",
                "days_blocked": 3,
            },
        ],
        "risks": [
            {
                "description": "Key engineer (Marcus Rivera) has PTO scheduled during cutover window",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Cross-train backup engineer on migration runbook this week",
            },
        ],
        "recommendations": [
            "Escalate auth service API contract to VP Engineering for resolution by EOW",
            "Request additional staging capacity from cloud ops (estimated 2-day lead time)",
            "Schedule knowledge transfer session for migration runbook before PTO window",
        ],
    },
    indent=2,
)

_GAP_ANALYSIS_RESPONSE = json.dumps(
    {
        "gaps": [
            {
                "type": "missing_task",
                "description": "No rollback plan documented for database schema migration",
                "severity": "critical",
                "recommendation": "Create rollback runbook with tested restore procedure",
                "suggested_owner": "Sarah Chen",
                "estimated_effort_hours": 8,
            },
            {
                "type": "missing_prerequisite",
                "description": "Load testing not scheduled before production cutover",
                "severity": "high",
                "recommendation": "Add load test task as prerequisite to cutover milestone",
                "suggested_owner": "Marcus Rivera",
                "estimated_effort_hours": 16,
            },
            {
                "type": "missing_communication",
                "description": "No customer notification plan for maintenance window",
                "severity": "medium",
                "recommendation": "Draft customer communication with 2-week advance notice",
                "suggested_owner": "Product Manager",
                "estimated_effort_hours": 4,
            },
        ],
        "coverage_score": 0.72,
        "critical_path_complete": False,
    },
    indent=2,
)

_REPORT_GENERATION_RESPONSE = json.dumps(
    {
        "report_spec": {
            "title": "Weekly Engineering Status Report",
            "description": "Comprehensive status update covering all active engineering projects, team velocity, and blockers.",
            "report_type": "status",
            "frequency": "weekly",
            "sections": [
                {
                    "title": "Executive Summary",
                    "content_type": "narrative",
                    "data_sources": ["projects", "alerts"],
                    "instructions": "Summarize overall engineering health in 3-5 sentences. Highlight any items requiring executive attention.",
                },
                {
                    "title": "Project Status Overview",
                    "content_type": "table",
                    "data_sources": ["projects"],
                    "columns": [
                        "project_name",
                        "status",
                        "health_score",
                        "owner",
                        "next_milestone",
                    ],
                    "sort_by": "health_score",
                    "sort_order": "ascending",
                },
                {
                    "title": "Active Blockers",
                    "content_type": "list",
                    "data_sources": ["projects", "alerts"],
                    "filter": {"severity": ["critical", "high"]},
                    "instructions": "List all blockers with owner and days blocked.",
                },
                {
                    "title": "Team Velocity",
                    "content_type": "chart",
                    "chart_type": "line",
                    "data_sources": ["people"],
                    "metrics": ["tasks_completed", "story_points"],
                    "time_range": "last_4_weeks",
                },
                {
                    "title": "Upcoming Milestones",
                    "content_type": "timeline",
                    "data_sources": ["projects"],
                    "time_range": "next_2_weeks",
                },
            ],
            "recipients": ["engineering_leadership"],
            "delivery_day": "Monday",
            "delivery_time": "09:00",
        }
    },
    indent=2,
)

_WIDGET_GENERATION_RESPONSE = json.dumps(
    {
        "widget_spec": {
            "title": "Project Health Overview",
            "widget_type": "scorecard",
            "description": "At-a-glance health indicators for all active projects.",
            "data_source": "projects",
            "layout": {
                "columns": 3,
                "rows": "auto",
                "card_style": "compact",
            },
            "metrics": [
                {
                    "label": "On Track",
                    "query": {"status": "on_track"},
                    "aggregation": "count",
                    "color": "#22c55e",
                    "icon": "check-circle",
                },
                {
                    "label": "At Risk",
                    "query": {"status": "at_risk"},
                    "aggregation": "count",
                    "color": "#f59e0b",
                    "icon": "alert-triangle",
                },
                {
                    "label": "Blocked",
                    "query": {"status": "blocked"},
                    "aggregation": "count",
                    "color": "#ef4444",
                    "icon": "x-circle",
                },
            ],
            "refresh_interval_seconds": 300,
            "click_action": "navigate_to_project_detail",
        }
    },
    indent=2,
)

_FACT_EXTRACTION_RESPONSE = json.dumps(
    {
        "facts": [
            {
                "subject": "Platform Migration",
                "predicate": "deadline",
                "object": "2026-03-15",
                "confidence": 0.95,
                "source_snippet": "The platform migration must be completed by March 15th.",
            },
            {
                "subject": "Sarah Chen",
                "predicate": "leads",
                "object": "Platform Engineering",
                "confidence": 0.92,
                "source_snippet": "Sarah Chen, who leads the Platform Engineering team...",
            },
            {
                "subject": "Auth Service v2",
                "predicate": "blocks",
                "object": "Service Cutover Phase",
                "confidence": 0.88,
                "source_snippet": "...cutover cannot proceed until auth service v2 contract is finalized.",
            },
        ],
        "entity_count": 5,
        "relation_count": 3,
    },
    indent=2,
)

_CONVERSATION_RESPONSE = (
    "Based on the data I have access to, here is what I can tell you:\n\n"
    "The engineering team has been making steady progress this week. Three projects "
    "are currently on track, one is flagged as at-risk due to a dependency delay, "
    "and no projects are fully blocked.\n\n"
    "The at-risk project is the Platform Migration, which is waiting on the auth "
    "service v2 API contract. Sarah Chen has been working to resolve this and "
    "expects a decision by end of week.\n\n"
    "Team velocity is slightly above the rolling 4-week average, with 47 story "
    "points completed versus the 43-point average. No PTO conflicts are expected "
    "for the next two weeks.\n\n"
    "Would you like me to drill into any specific project or person?"
)

_ALERT_PARSING_RESPONSE = json.dumps(
    {
        "alerts": [
            {
                "alert_type": "deadline_risk",
                "severity": "high",
                "title": "Platform Migration cutover at risk",
                "description": (
                    "The service cutover milestone for Platform Migration is projected "
                    "to slip by 13 days based on current velocity and unresolved blockers."
                ),
                "affected_project": "Platform Migration",
                "affected_people": ["Sarah Chen", "Marcus Rivera"],
                "recommended_action": "Escalate auth service dependency to VP Engineering",
                "deadline": "2026-03-15",
            },
            {
                "alert_type": "resource_conflict",
                "severity": "medium",
                "title": "Key engineer PTO during critical window",
                "description": (
                    "Marcus Rivera has approved PTO from March 10-14, which overlaps "
                    "with the planned cutover window for Platform Migration."
                ),
                "affected_project": "Platform Migration",
                "affected_people": ["Marcus Rivera"],
                "recommended_action": "Conduct knowledge transfer session this week",
                "deadline": "2026-03-07",
            },
        ],
        "total_alerts": 2,
        "critical_count": 0,
        "high_count": 1,
        "medium_count": 1,
    },
    indent=2,
)

_BRIEFING_GENERATION_RESPONSE = json.dumps(
    {
        "briefing": {
            "title": "Morning Briefing - Engineering Operations",
            "generated_at": "2026-02-08T09:00:00Z",
            "priority_items": [
                {
                    "priority": 1,
                    "category": "blocker",
                    "summary": "Auth service v2 API contract still unresolved (day 5)",
                    "impact": "Blocks Platform Migration Phase 3 cutover",
                    "action_needed": "Decision required from VP Engineering today",
                },
                {
                    "priority": 2,
                    "category": "deadline",
                    "summary": "Data Pipeline Upgrade demo scheduled for Thursday",
                    "impact": "Client presentation depends on staging environment stability",
                    "action_needed": "Verify staging deployment by end of day Tuesday",
                },
            ],
            "metrics_snapshot": {
                "active_projects": 4,
                "on_track": 3,
                "at_risk": 1,
                "blocked": 0,
                "team_velocity_trend": "stable",
                "open_blockers": 2,
            },
            "people_notes": [
                "Sarah Chen: high output this week, 12 PRs merged. Monitor workload.",
                "Marcus Rivera: blocked on PLAT-430. PTO starts March 10.",
                "New hire Aisha Patel starts Monday -- onboarding buddy: Sarah Chen.",
            ],
            "upcoming_deadlines": [
                {"date": "2026-02-12", "item": "Data Pipeline demo (staging)"},
                {"date": "2026-02-14", "item": "Sprint 14 retrospective"},
                {"date": "2026-03-15", "item": "Platform Migration cutover (at risk)"},
            ],
        }
    },
    indent=2,
)

_ENTITY_RESOLUTION_RESPONSE = json.dumps(
    {
        "resolution": {
            "query": "Sarah",
            "matches": [
                {
                    "name": "Sarah Chen",
                    "confidence": 0.94,
                    "department": "Platform Engineering",
                    "role": "Engineering Lead",
                    "match_reason": "First name match + high activity in current context",
                },
                {
                    "name": "Sarah Thompson",
                    "confidence": 0.35,
                    "department": "Product Management",
                    "role": "Product Manager",
                    "match_reason": "First name match only, low contextual relevance",
                },
            ],
            "best_match": "Sarah Chen",
            "ambiguous": False,
        }
    },
    indent=2,
)

_CORRECTION_INTERPRETATION_RESPONSE = json.dumps(
    {
        "correction": {
            "type": "attribute_update",
            "entity_type": "person",
            "entity_identifier": "Marcus Rivera",
            "field": "role",
            "old_value": "Senior Backend Developer",
            "new_value": "Staff Engineer",
            "confidence": 0.89,
            "reasoning": (
                "The COO stated 'Marcus is actually a Staff Engineer, not Senior Backend'. "
                "This is a direct role correction with explicit old and new values."
            ),
            "requires_confirmation": True,
        }
    },
    indent=2,
)

# ---------------------------------------------------------------------------
# Pattern-to-response map
# ---------------------------------------------------------------------------

RESPONSE_MAP: list[tuple[str, str]] = [
    (r"intent\s*detect", _INTENT_RESPONSE),
    (r"classify.*(?:user|input|message)", _INTENT_RESPONSE),
    (r"people\s*identif", _PEOPLE_IDENTIFICATION_RESPONSE),
    (r"role\s*detect", _ROLE_DETECTION_RESPONSE),
    (r"project\s*analy", _PROJECT_ANALYSIS_RESPONSE),
    (r"project\s*status", _PROJECT_ANALYSIS_RESPONSE),
    (r"report\s*generat", _REPORT_GENERATION_RESPONSE),
    (r"report\s*spec", _REPORT_GENERATION_RESPONSE),
    (r"widget\s*generat", _WIDGET_GENERATION_RESPONSE),
    (r"widget\s*spec", _WIDGET_GENERATION_RESPONSE),
    (r"widget\s*creat", _WIDGET_GENERATION_RESPONSE),
    (r"fact\s*extract", _FACT_EXTRACTION_RESPONSE),
    (r"entity\s*resolut", _ENTITY_RESOLUTION_RESPONSE),
    (r"disambiguat", _ENTITY_RESOLUTION_RESPONSE),
    (r"fuzzy\s*match", _ENTITY_RESOLUTION_RESPONSE),
    (r"correction\s*interpret", _CORRECTION_INTERPRETATION_RESPONSE),
    (r"parse.*correction", _CORRECTION_INTERPRETATION_RESPONSE),
    (r"gap\s*(?:detect|analy)", _GAP_ANALYSIS_RESPONSE),
    (r"missing\s*task", _GAP_ANALYSIS_RESPONSE),
    (r"alert\s*pars", _ALERT_PARSING_RESPONSE),
    (r"alert\s*detect", _ALERT_PARSING_RESPONSE),
    (r"briefing\s*generat", _BRIEFING_GENERATION_RESPONSE),
    (r"morning\s*briefing", _BRIEFING_GENERATION_RESPONSE),
    (r"daily\s*briefing", _BRIEFING_GENERATION_RESPONSE),
    (r"backward\s*plan", _PROJECT_ANALYSIS_RESPONSE),
    (r"feasibility", _PROJECT_ANALYSIS_RESPONSE),
]


def _match_response(system_prompt: str, user_prompt: str) -> str:
    """Find the best matching fixture response based on prompt content."""
    combined = (system_prompt + " " + user_prompt).lower()
    for pattern, response in RESPONSE_MAP:
        if re.search(pattern, combined):
            return response
    return _CONVERSATION_RESPONSE


class MockAIAdapter(AIAdapter):
    """Mock adapter that returns realistic fixture responses for testing.

    Pattern-matches against the system prompt to determine which category
    of response to return.  Useful for development, demos, and tests
    where no live AI backend is available.
    """

    async def generate(self, request: AIRequest) -> AIResponse:
        """Return a fixture response based on prompt content."""
        start = time.perf_counter()

        content = _match_response(request.system_prompt, request.user_prompt)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "MockAIAdapter returning %d-char response for prompt: %s",
            len(content),
            request.system_prompt[:80],
        )

        return AIResponse(
            content=content,
            model="mock",
            input_tokens=len(request.system_prompt.split()) + len(request.user_prompt.split()),
            output_tokens=len(content.split()),
            adapter="mock",
            latency_ms=elapsed_ms,
        )

    async def generate_structured(self, request: AIRequest) -> AIResponse:
        """Return a structured JSON fixture response.

        Ensures the returned content is always valid JSON, even for
        patterns that normally return plain text.
        """
        start = time.perf_counter()

        content = _match_response(request.system_prompt, request.user_prompt)

        # If the matched content is not JSON, wrap it
        try:
            json.loads(content)
        except (json.JSONDecodeError, ValueError):
            content = json.dumps(
                {"response": content, "status": "success"},
                indent=2,
            )

        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "MockAIAdapter returning structured response for prompt: %s",
            request.system_prompt[:80],
        )

        return AIResponse(
            content=content,
            model="mock",
            input_tokens=len(request.system_prompt.split()) + len(request.user_prompt.split()),
            output_tokens=len(content.split()),
            adapter="mock",
            latency_ms=elapsed_ms,
        )

    async def health_check(self) -> bool:
        """Mock adapter is always healthy."""
        logger.debug("MockAIAdapter health check: OK")
        return True
