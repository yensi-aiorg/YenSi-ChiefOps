"""
Technical feasibility assessment for projects.

Evaluates project readiness across technical areas, identifies risks,
and generates architect questions for unresolved technical concerns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.ai.adapter import AIRequest
from app.models.project import ReadinessItem, RiskItem, TechnicalFeasibility

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def assess_feasibility(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
    citex_context_text: str = "",
) -> TechnicalFeasibility:
    """Assess the technical feasibility of a project.

    Gathers project data including tasks, team composition, and
    technical discussions to evaluate:
    - Readiness by technical area
    - Risk items with severity and mitigation
    - Unresolved architect questions

    Args:
        project_id: Project identifier.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        A ``TechnicalFeasibility`` instance.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return TechnicalFeasibility()

    context = await _gather_technical_context(project, db)

    if ai_adapter is None:
        return _heuristic_feasibility(project, context)

    return await _ai_feasibility(
        project,
        context,
        ai_adapter,
        citex_context_text=citex_context_text,
    )


async def _gather_technical_context(
    project: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Gather technical context for feasibility assessment."""
    jira_keys = project.get("jira_project_keys", [])
    slack_channels = project.get("slack_channels", [])

    context: dict[str, Any] = {
        "project_name": project.get("name", ""),
        "description": project.get("description", ""),
    }

    # Gather tasks with technical focus
    tasks: list[dict[str, Any]] = []
    if jira_keys:
        async for task in db.jira_tasks.find(
            {"project_key": {"$in": jira_keys}},
            {
                "_id": 0,
                "task_key": 1,
                "summary": 1,
                "description": 1,
                "status": 1,
                "issue_type": 1,
                "labels": 1,
                "components": 1,
            },
        ).limit(100):
            tasks.append(task)

    context["tasks"] = tasks

    # Gather technical discussions from Slack
    tech_messages: list[str] = []
    if slack_channels:
        async for msg in (
            db.slack_messages.find(
                {"channel": {"$in": slack_channels}},
                {"text": 1, "_id": 0},
            )
            .sort("timestamp", -1)
            .limit(50)
        ):
            text = msg.get("text", "")
            if text:
                tech_messages.append(text)

    context["tech_messages"] = tech_messages

    # Team composition
    people = project.get("people_involved", [])
    context["team"] = people
    context["team_size"] = len(people)

    # Component and label analysis
    components: set[str] = set()
    labels: set[str] = set()
    for task in tasks:
        for comp in task.get("components", []):
            components.add(comp)
        for label in task.get("labels", []):
            labels.add(label)

    context["components"] = list(components)
    context["labels"] = list(labels)

    return context


async def _ai_feasibility(
    project: dict[str, Any],
    context: dict[str, Any],
    ai_adapter: Any,
    citex_context_text: str = "",
) -> TechnicalFeasibility:
    """Use AI to assess technical feasibility."""
    # Build tasks summary
    tasks_text = ""
    for task in context.get("tasks", [])[:40]:
        desc = task.get("description", "")
        desc_preview = desc[:200] if desc else ""
        tasks_text += (
            f"- [{task.get('task_key', '')}] {task.get('summary', '')} "
            f"(type: {task.get('issue_type', '')}, status: {task.get('status', '')})\n"
        )
        if desc_preview:
            tasks_text += f"  Description: {desc_preview}\n"

    # Build messages sample
    messages_text = ""
    for msg in context.get("tech_messages", [])[:20]:
        messages_text += f"- {msg[:300]}\n"

    prompt = (
        f"Assess the technical feasibility of this project.\n\n"
        f"Project: {context.get('project_name', 'Unknown')}\n"
        f"Description: {context.get('description', 'N/A')}\n"
        f"Team size: {context.get('team_size', 0)}\n"
        f"Components: {', '.join(context.get('components', [])) or 'None'}\n"
        f"Labels: {', '.join(context.get('labels', [])) or 'None'}\n\n"
        f"Tasks:\n{tasks_text or 'No tasks'}\n\n"
        f"Recent technical discussions:\n{messages_text or 'None available'}\n\n"
        f"Retrieved Citex context:\n{citex_context_text or 'None available'}\n\n"
        "Evaluate:\n"
        "1. Technical readiness by area (infrastructure, API design, data model, "
        "testing, deployment, security, performance, documentation)\n"
        "2. Risk items with severity and mitigation strategies\n"
        "3. Unresolved questions for the architecture team\n\n"
        "Respond with a JSON object containing:\n"
        '  "readiness_items": [{area, status (ready|partial|not_ready|unknown), details}]\n'
        '  "risk_items": [{risk, severity (critical|high|medium|low), mitigation}]\n'
        '  "architect_questions": [list of question strings]'
    )

    schema = {
        "type": "object",
        "properties": {
            "readiness_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "area": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["ready", "partial", "not_ready", "unknown"],
                        },
                        "details": {"type": "string"},
                    },
                    "required": ["area", "status", "details"],
                },
            },
            "risk_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                        "mitigation": {"type": "string"},
                    },
                    "required": ["risk", "severity", "mitigation"],
                },
            },
            "architect_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["readiness_items", "risk_items", "architect_questions"],
    }

    try:
        request = AIRequest(
            system_prompt="You are a technical architect reviewing project feasibility. Be thorough and practical.",
            user_prompt=prompt,
            response_schema=schema,
        )
        response = await ai_adapter.generate_structured(request)
        result = response.parse_json()

        readiness = [
            ReadinessItem(
                area=item.get("area", ""),
                status=item.get("status", "unknown"),
                details=item.get("details", ""),
            )
            for item in result.get("readiness_items", [])
        ]

        risks = [
            RiskItem(
                risk=item.get("risk", ""),
                severity=item.get("severity", "medium"),
                mitigation=item.get("mitigation", ""),
            )
            for item in result.get("risk_items", [])
        ]

        return TechnicalFeasibility(
            readiness_items=readiness,
            risk_items=risks,
            architect_questions=result.get("architect_questions", []),
        )

    except Exception as exc:
        logger.warning("AI feasibility assessment failed: %s", exc)
        return _heuristic_feasibility(project, context)


def _heuristic_feasibility(
    project: dict[str, Any],
    context: dict[str, Any],
) -> TechnicalFeasibility:
    """Fallback heuristic feasibility assessment."""
    readiness_items: list[ReadinessItem] = []
    risk_items: list[RiskItem] = []
    architect_questions: list[str] = []

    tasks = context.get("tasks", [])
    components = context.get("components", [])
    team_size = context.get("team_size", 0)

    # Check common readiness areas
    standard_areas = [
        "infrastructure",
        "api_design",
        "data_model",
        "testing",
        "deployment",
        "security",
    ]

    task_summaries_lower = " ".join(
        t.get("summary", "").lower() + " " + " ".join(t.get("labels", [])) for t in tasks
    )

    for area in standard_areas:
        area_keywords = {
            "infrastructure": ["infra", "server", "cloud", "aws", "gcp", "azure", "docker", "k8s"],
            "api_design": ["api", "endpoint", "rest", "graphql", "grpc", "swagger"],
            "data_model": ["database", "schema", "migration", "model", "data"],
            "testing": ["test", "qa", "automation", "e2e", "unit test", "integration"],
            "deployment": ["deploy", "ci/cd", "pipeline", "release", "staging"],
            "security": ["security", "auth", "permission", "encryption", "ssl", "oauth"],
        }

        keywords = area_keywords.get(area, [])
        has_coverage = any(kw in task_summaries_lower for kw in keywords)
        has_component = any(area.replace("_", "") in c.lower().replace("_", "") for c in components)

        if has_coverage or has_component:
            readiness_items.append(
                ReadinessItem(
                    area=area,
                    status="partial",
                    details=f"Some tasks and components reference {area}",
                )
            )
        else:
            readiness_items.append(
                ReadinessItem(
                    area=area,
                    status="unknown",
                    details=f"No explicit {area} tasks or components found",
                )
            )
            architect_questions.append(
                f"What is the {area.replace('_', ' ')} plan for this project?"
            )

    # Team size risk
    if team_size == 0:
        risk_items.append(
            RiskItem(
                risk="No team members assigned to the project",
                severity="critical",
                mitigation="Assign team members with appropriate skills",
            )
        )
    elif team_size == 1:
        risk_items.append(
            RiskItem(
                risk="Single person dependency -- bus factor of 1",
                severity="high",
                mitigation="Assign at least one additional team member for knowledge sharing",
            )
        )

    # Task coverage risks
    if len(tasks) == 0:
        risk_items.append(
            RiskItem(
                risk="No tasks created for the project",
                severity="critical",
                mitigation="Create and prioritize project tasks in Jira",
            )
        )

    unassigned = sum(1 for t in tasks if not t.get("assignee"))
    if unassigned > len(tasks) * 0.5 and len(tasks) > 5:
        risk_items.append(
            RiskItem(
                risk=f"{unassigned} out of {len(tasks)} tasks are unassigned",
                severity="high",
                mitigation="Assign owners to all priority tasks",
            )
        )

    return TechnicalFeasibility(
        readiness_items=readiness_items,
        risk_items=risk_items,
        architect_questions=architect_questions,
    )
