"""
AI-powered role detection for people identification.

Analyses a person's activity across Slack, Jira, and Drive to infer
their organisational role. Uses the AI adapter's structured generation
to produce consistent role labels.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PersonWithRole:
    """A person record enriched with an AI-detected role."""

    person_id: str
    name: str
    role: str
    department: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""


# Standard role labels that the AI should assign
ROLE_LABELS = [
    "engineering_manager",
    "tech_lead",
    "senior_developer",
    "developer",
    "junior_developer",
    "qa_engineer",
    "devops_engineer",
    "product_manager",
    "project_manager",
    "scrum_master",
    "designer",
    "ux_researcher",
    "data_analyst",
    "data_engineer",
    "data_scientist",
    "solutions_architect",
    "cto",
    "vp_engineering",
    "director",
    "team_lead",
    "business_analyst",
    "technical_writer",
    "support_engineer",
    "sales_engineer",
    "marketing",
    "executive",
    "contractor",
    "intern",
    "team_member",
]

DEPARTMENT_LABELS = [
    "Engineering",
    "Product",
    "Design",
    "QA",
    "DevOps",
    "Data",
    "Management",
    "Sales",
    "Marketing",
    "Support",
    "Executive",
    "Unknown",
]


def _build_role_detection_prompt(
    person_name: str,
    activity_data: dict[str, Any],
) -> str:
    """Build a prompt for AI role detection."""
    slack_activity = activity_data.get("slack", {})
    jira_activity = activity_data.get("jira", {})
    channels = activity_data.get("channels", [])

    prompt_parts = [
        "Analyze the following person's activity data and determine their most likely role and department.",
        "",
        f"Person: {person_name}",
        "",
        "Activity Summary:",
    ]

    if slack_activity:
        prompt_parts.append(f"- Slack messages sent: {slack_activity.get('messages_sent', 0)}")
        prompt_parts.append(f"- Threads replied: {slack_activity.get('threads_replied', 0)}")
        prompt_parts.append(f"- Reactions given: {slack_activity.get('reactions_given', 0)}")

    if channels:
        prompt_parts.append(f"- Active in channels: {', '.join(channels[:20])}")

    if jira_activity:
        prompt_parts.append(f"- Tasks assigned: {jira_activity.get('tasks_assigned', 0)}")
        prompt_parts.append(f"- Tasks completed: {jira_activity.get('tasks_completed', 0)}")
        task_types = jira_activity.get("task_types", [])
        if task_types:
            prompt_parts.append(f"- Task types worked on: {', '.join(task_types[:10])}")
        statuses = jira_activity.get("statuses", [])
        if statuses:
            prompt_parts.append(f"- Task statuses: {', '.join(statuses[:10])}")

    sample_messages = activity_data.get("sample_messages", [])
    if sample_messages:
        prompt_parts.append("")
        prompt_parts.append("Recent message samples:")
        for msg in sample_messages[:5]:
            prompt_parts.append(f'  - "{msg}"')

    prompt_parts.extend([
        "",
        f"Available roles: {', '.join(ROLE_LABELS)}",
        f"Available departments: {', '.join(DEPARTMENT_LABELS)}",
        "",
        "Respond with a JSON object containing:",
        '  "role": one of the available roles',
        '  "department": one of the available departments',
        '  "confidence": a float between 0.0 and 1.0',
        '  "reasoning": a brief explanation of why you chose this role',
    ])

    return "\n".join(prompt_parts)


async def detect_roles(
    people: list[dict[str, Any]],
    activity_data: dict[str, dict[str, Any]],
    ai_adapter: Any,
) -> list[PersonWithRole]:
    """Detect roles for a list of people using AI analysis.

    Args:
        people: List of person dicts with at least ``person_id`` and ``name``.
        activity_data: Dict mapping person_id to activity data dicts.
        ai_adapter: AI adapter instance with ``generate_structured`` method.

    Returns:
        A list of ``PersonWithRole`` objects with detected roles.
    """
    results: list[PersonWithRole] = []

    for person in people:
        person_id = person.get("person_id", "")
        name = person.get("name", "Unknown")
        person_activity = activity_data.get(person_id, {})

        role_result = await _detect_single_role(
            person_id=person_id,
            person_name=name,
            activity=person_activity,
            ai_adapter=ai_adapter,
        )
        results.append(role_result)

    logger.info("Role detection completed for %d people", len(results))
    return results


async def _detect_single_role(
    person_id: str,
    person_name: str,
    activity: dict[str, Any],
    ai_adapter: Any,
) -> PersonWithRole:
    """Detect the role for a single person."""

    # If no AI adapter available, use heuristic-based detection
    if ai_adapter is None:
        return _heuristic_role_detection(person_id, person_name, activity)

    prompt = _build_role_detection_prompt(person_name, activity)

    schema = {
        "type": "object",
        "properties": {
            "role": {"type": "string", "enum": ROLE_LABELS},
            "department": {"type": "string", "enum": DEPARTMENT_LABELS},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reasoning": {"type": "string"},
        },
        "required": ["role", "department", "confidence", "reasoning"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are an organizational analyst. Detect the person's role based on their activity patterns across Slack and Jira.",
        )

        return PersonWithRole(
            person_id=person_id,
            name=person_name,
            role=result.get("role", "team_member"),
            department=result.get("department", "Unknown"),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", ""),
        )

    except Exception as exc:
        logger.warning("AI role detection failed for %s: %s", person_name, exc)
        return _heuristic_role_detection(person_id, person_name, activity)


def _heuristic_role_detection(
    person_id: str,
    person_name: str,
    activity: dict[str, Any],
) -> PersonWithRole:
    """Fallback heuristic role detection when AI is unavailable."""
    channels = activity.get("channels", [])
    jira = activity.get("jira", {})
    slack = activity.get("slack", {})

    channel_set = {c.lower() for c in channels}
    task_types = {t.lower() for t in jira.get("task_types", [])}

    # Channel-based heuristics
    if any(kw in ch for ch in channel_set for kw in ("devops", "infra", "deploy", "sre")):
        return PersonWithRole(person_id=person_id, name=person_name, role="devops_engineer", department="DevOps", confidence=0.4, reasoning="Active in DevOps-related channels")

    if any(kw in ch for ch in channel_set for kw in ("design", "ux", "figma", "ui")):
        return PersonWithRole(person_id=person_id, name=person_name, role="designer", department="Design", confidence=0.4, reasoning="Active in design-related channels")

    if any(kw in ch for ch in channel_set for kw in ("qa", "testing", "quality", "automation")):
        return PersonWithRole(person_id=person_id, name=person_name, role="qa_engineer", department="QA", confidence=0.4, reasoning="Active in QA-related channels")

    if any(kw in ch for ch in channel_set for kw in ("product", "roadmap", "prd", "spec")):
        return PersonWithRole(person_id=person_id, name=person_name, role="product_manager", department="Product", confidence=0.4, reasoning="Active in product-related channels")

    if any(kw in ch for ch in channel_set for kw in ("data", "analytics", "ml", "pipeline")):
        return PersonWithRole(person_id=person_id, name=person_name, role="data_analyst", department="Data", confidence=0.4, reasoning="Active in data-related channels")

    # Jira task type heuristics
    if "bug" in task_types:
        tasks_assigned = jira.get("tasks_assigned", 0)
        if tasks_assigned > 10:
            return PersonWithRole(person_id=person_id, name=person_name, role="developer", department="Engineering", confidence=0.5, reasoning="Assigned many tasks including bugs")

    # High message volume heuristic
    messages_sent = slack.get("messages_sent", 0)
    tasks_assigned = jira.get("tasks_assigned", 0)

    if messages_sent > 100 and tasks_assigned == 0:
        return PersonWithRole(person_id=person_id, name=person_name, role="project_manager", department="Management", confidence=0.3, reasoning="High Slack activity with no Jira tasks")

    if tasks_assigned > 0:
        return PersonWithRole(person_id=person_id, name=person_name, role="developer", department="Engineering", confidence=0.3, reasoning="Has Jira tasks assigned")

    return PersonWithRole(
        person_id=person_id,
        name=person_name,
        role="team_member",
        department="Unknown",
        confidence=0.2,
        reasoning="Insufficient data for role detection",
    )
