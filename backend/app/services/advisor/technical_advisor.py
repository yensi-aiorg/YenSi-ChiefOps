"""
Technical advisor service.

Provides backward planning, missing task detection, and architect
question generation to help the COO understand project technical
readiness and planning gaps.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def generate_backward_plan(
    project_id: str,
    target_date: datetime,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> list[dict[str, Any]]:
    """Generate a backward plan from a target date to present.

    Works backward from the target date, identifying all work items
    that need to be completed and their dependencies.

    Args:
        project_id: Project identifier.
        target_date: The target deadline to plan backward from.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        List of backward plan items with tasks, durations, and dependencies.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return []

    # Gather existing tasks
    jira_keys = project.get("jira_project_keys", [])
    existing_tasks: list[dict[str, Any]] = []
    if jira_keys:
        async for task in db.jira_tasks.find(
            {"project_key": {"$in": jira_keys}},
            {
                "task_key": 1,
                "summary": 1,
                "status": 1,
                "assignee": 1,
                "story_points": 1,
                "due_date": 1,
                "epic_link": 1,
                "_id": 0,
            },
        ):
            existing_tasks.append(task)

    now = datetime.now(UTC)
    days_available = (target_date - now).days

    if ai_adapter is None:
        return _heuristic_backward_plan(existing_tasks, days_available)

    # Build task list for prompt
    task_list = ""
    for task in existing_tasks[:60]:
        task_list += (
            f"- [{task.get('task_key', '')}] {task.get('summary', '')} "
            f"(status: {task.get('status', '')}, assignee: {task.get('assignee', 'unassigned')})\n"
        )

    prompt = (
        f"Create a backward plan for this project.\n\n"
        f"Project: {project.get('name', '')}\n"
        f"Target date: {target_date.strftime('%Y-%m-%d')} ({days_available} days from now)\n"
        f"Total existing tasks: {len(existing_tasks)}\n\n"
        f"Existing tasks:\n{task_list}\n\n"
        "Working backward from the target date, identify the key phases and "
        "milestones needed. For each, provide the task name, estimated days, "
        "dependencies, and priority.\n\n"
        "Respond with a JSON object containing:\n"
        '  "plan": [\n'
        '    {"task": "description", "estimated_days": N, "depends_on": [], "priority": "critical|high|medium|low"}\n'
        "  ]"
    )

    schema = {
        "type": "object",
        "properties": {
            "plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "estimated_days": {"type": "integer", "minimum": 1},
                        "depends_on": {"type": "array", "items": {"type": "string"}},
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                    },
                    "required": ["task", "estimated_days", "priority"],
                },
            },
        },
        "required": ["plan"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a project planning expert. Create realistic backward plans from deadlines.",
        )
        return result.get("plan", [])
    except Exception as exc:
        logger.warning("AI backward plan generation failed: %s", exc)
        return _heuristic_backward_plan(existing_tasks, days_available)


async def detect_missing_tasks(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> list[str]:
    """Detect tasks that are likely missing from the project.

    Analyses the existing task set and identifies gaps based on
    common software development patterns.

    Args:
        project_id: Project identifier.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        List of missing task descriptions.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return []

    jira_keys = project.get("jira_project_keys", [])
    tasks: list[dict[str, Any]] = []
    if jira_keys:
        async for task in db.jira_tasks.find(
            {"project_key": {"$in": jira_keys}},
            {"summary": 1, "issue_type": 1, "labels": 1, "components": 1, "_id": 0},
        ).limit(100):
            tasks.append(task)

    if ai_adapter is None:
        return _heuristic_missing_tasks(tasks)

    task_list = "\n".join(
        f"- {t.get('summary', '')} (type: {t.get('issue_type', '')}, labels: {t.get('labels', [])})"
        for t in tasks
    )

    prompt = (
        f"Review these project tasks and identify what is likely missing.\n\n"
        f"Project: {project.get('name', '')}\n"
        f"Description: {project.get('description', '')}\n\n"
        f"Current tasks:\n{task_list}\n\n"
        "Identify missing tasks that a well-planned project should have. "
        "Consider: testing, documentation, deployment, security, monitoring, "
        "performance, CI/CD, code review processes, etc.\n\n"
        "Respond with a JSON object containing:\n"
        '  "missing_tasks": ["task description 1", "task description 2", ...]'
    )

    schema = {
        "type": "object",
        "properties": {
            "missing_tasks": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["missing_tasks"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a project management expert. Identify missing tasks in software projects.",
        )
        return result.get("missing_tasks", [])
    except Exception as exc:
        logger.warning("AI missing task detection failed: %s", exc)
        return _heuristic_missing_tasks(tasks)


async def generate_architect_questions(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> list[str]:
    """Generate unresolved architect questions for the project.

    Analyses the project context and identifies technical questions
    that should be answered before proceeding.

    Args:
        project_id: Project identifier.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        List of architect questions.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return []

    if ai_adapter is None:
        return _default_architect_questions(project)

    jira_keys = project.get("jira_project_keys", [])
    tasks: list[str] = []
    if jira_keys:
        async for task in db.jira_tasks.find(
            {"project_key": {"$in": jira_keys}},
            {"summary": 1, "description": 1, "_id": 0},
        ).limit(50):
            tasks.append(
                f"{task.get('summary', '')} -- {(task.get('description', '') or '')[:200]}"
            )

    prompt = (
        f"Generate architect questions for this project.\n\n"
        f"Project: {project.get('name', '')}\n"
        f"Description: {project.get('description', '')}\n\n"
        f"Sample tasks:\n" + "\n".join(f"- {t}" for t in tasks[:20]) + "\n\n"
        "Generate questions about architecture, scalability, security, "
        "data flow, integrations, and technical decisions that should be "
        "resolved.\n\n"
        "Respond with a JSON object containing:\n"
        '  "questions": ["question 1", "question 2", ...]'
    )

    schema = {
        "type": "object",
        "properties": {
            "questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["questions"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a solutions architect. Generate insightful technical questions.",
        )
        return result.get("questions", [])
    except Exception as exc:
        logger.warning("AI architect questions generation failed: %s", exc)
        return _default_architect_questions(project)


def _heuristic_backward_plan(
    tasks: list[dict[str, Any]],
    days_available: int,
) -> list[dict[str, Any]]:
    """Generate a basic backward plan without AI."""
    plan: list[dict[str, Any]] = []

    incomplete = [t for t in tasks if t.get("status") not in ("done", "closed", "resolved")]
    total_incomplete = len(incomplete)

    if days_available <= 0:
        plan.append(
            {
                "task": "Deadline has passed -- conduct retrospective and reset timeline",
                "estimated_days": 1,
                "depends_on": [],
                "priority": "critical",
            }
        )
        return plan

    # Allocate time proportionally
    dev_days = max(1, int(days_available * 0.6))
    test_days = max(1, int(days_available * 0.2))
    deploy_days = max(1, int(days_available * 0.1))
    buffer_days = max(1, days_available - dev_days - test_days - deploy_days)

    plan.append(
        {
            "task": f"Complete {total_incomplete} remaining development tasks",
            "estimated_days": dev_days,
            "depends_on": [],
            "priority": "high",
        }
    )
    plan.append(
        {
            "task": "Integration testing and QA",
            "estimated_days": test_days,
            "depends_on": [f"Complete {total_incomplete} remaining development tasks"],
            "priority": "high",
        }
    )
    plan.append(
        {
            "task": "Staging deployment and validation",
            "estimated_days": deploy_days,
            "depends_on": ["Integration testing and QA"],
            "priority": "critical",
        }
    )
    plan.append(
        {
            "task": "Production release and monitoring",
            "estimated_days": buffer_days,
            "depends_on": ["Staging deployment and validation"],
            "priority": "critical",
        }
    )

    return plan


def _heuristic_missing_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    """Detect missing tasks using heuristics."""
    missing: list[str] = []
    summaries_lower = " ".join(t.get("summary", "").lower() for t in tasks)
    {t.get("issue_type", "").lower() for t in tasks}
    labels = set()
    for t in tasks:
        for l in t.get("labels", []):
            labels.add(l.lower())

    if "test" not in summaries_lower and "qa" not in summaries_lower:
        missing.append("Add testing tasks (unit tests, integration tests, E2E tests)")

    if "deploy" not in summaries_lower and "release" not in summaries_lower:
        missing.append("Add deployment and release tasks")

    if "doc" not in summaries_lower and "documentation" not in summaries_lower:
        missing.append("Add documentation tasks (API docs, README, user guides)")

    if "monitor" not in summaries_lower and "observability" not in summaries_lower:
        missing.append("Add monitoring and observability setup tasks")

    if "security" not in summaries_lower and "audit" not in summaries_lower:
        missing.append("Add security review and audit tasks")

    if "performance" not in summaries_lower and "load test" not in summaries_lower:
        missing.append("Add performance testing tasks")

    return missing


def _default_architect_questions(project: dict[str, Any]) -> list[str]:
    """Generate default architect questions."""
    return [
        f"What is the target scale and expected load for {project.get('name', 'this project')}?",
        "What is the data persistence strategy and expected data volume?",
        "How will the service handle failures and provide resilience?",
        "What authentication and authorization mechanism will be used?",
        "What is the API versioning and backward compatibility strategy?",
        "How will the deployment pipeline and rollback process work?",
    ]
