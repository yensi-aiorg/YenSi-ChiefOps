"""
Gap detection for project planning and execution.

Uses AI analysis to identify missing tasks, missing prerequisites,
and generates backward plans from deadlines to current state.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.project import BackwardPlanItem, GapAnalysis

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def detect_gaps(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> GapAnalysis:
    """Detect gaps in project planning and execution.

    Gathers all task data, milestone information, and team allocation
    for the project, then uses AI to identify:
    - Missing tasks that should exist
    - Missing prerequisites for existing tasks
    - A backward plan from deadline to present

    Args:
        project_id: Project identifier.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        A ``GapAnalysis`` instance with detected gaps.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return GapAnalysis()

    # Gather project data
    project_context = await _gather_project_context(project, db)

    if ai_adapter is None:
        return _heuristic_gap_detection(project, project_context)

    # Use AI for gap detection
    return await _ai_gap_detection(project, project_context, ai_adapter)


async def _gather_project_context(
    project: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Gather all relevant data for gap analysis."""
    jira_keys = project.get("jira_project_keys", [])
    context: dict[str, Any] = {
        "project_name": project.get("name", ""),
        "description": project.get("description", ""),
        "deadline": project.get("deadline"),
        "milestones": project.get("milestones", []),
        "status": project.get("status", ""),
    }

    # Gather tasks
    tasks: list[dict[str, Any]] = []
    if jira_keys:
        async for task in db.jira_tasks.find(
            {"project_key": {"$in": jira_keys}},
            {
                "_id": 0,
                "task_key": 1,
                "summary": 1,
                "status": 1,
                "assignee": 1,
                "issue_type": 1,
                "priority": 1,
                "story_points": 1,
                "epic_link": 1,
                "labels": 1,
                "due_date": 1,
                "created_date": 1,
            },
        ):
            tasks.append(task)

    context["tasks"] = tasks
    context["task_count"] = len(tasks)

    # Status breakdown
    status_counts: dict[str, int] = {}
    for task in tasks:
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    context["status_breakdown"] = status_counts

    # Epic breakdown
    epic_counts: dict[str, int] = {}
    for task in tasks:
        epic = task.get("epic_link", "No Epic")
        epic_counts[epic] = epic_counts.get(epic, 0) + 1
    context["epic_breakdown"] = epic_counts

    # People involved
    context["people"] = project.get("people_involved", [])

    return context


async def _ai_gap_detection(
    project: dict[str, Any],
    context: dict[str, Any],
    ai_adapter: Any,
) -> GapAnalysis:
    """Use AI to detect gaps in the project."""
    # Build the analysis prompt
    tasks_summary = ""
    for task in context.get("tasks", [])[:50]:  # Limit to 50 tasks for prompt size
        tasks_summary += (
            f"- [{task.get('task_key', 'N/A')}] {task.get('summary', '')} "
            f"(status: {task.get('status', 'unknown')}, "
            f"assignee: {task.get('assignee', 'unassigned')}, "
            f"type: {task.get('issue_type', 'task')})\n"
        )

    deadline_str = ""
    if context.get("deadline"):
        deadline = context["deadline"]
        if isinstance(deadline, datetime):
            deadline_str = deadline.strftime("%Y-%m-%d")
            days_until = (deadline - datetime.now(UTC)).days
            deadline_str += f" ({days_until} days from now)"

    milestones_str = ""
    for m in context.get("milestones", []):
        name = m.get("name", "") if isinstance(m, dict) else str(m)
        status = m.get("status", "pending") if isinstance(m, dict) else "pending"
        milestones_str += f"- {name} (status: {status})\n"

    prompt = (
        f"Analyze the following project for gaps in planning and execution.\n\n"
        f"Project: {context.get('project_name', 'Unknown')}\n"
        f"Description: {context.get('description', 'N/A')}\n"
        f"Deadline: {deadline_str or 'Not set'}\n"
        f"Total tasks: {context.get('task_count', 0)}\n"
        f"Status breakdown: {context.get('status_breakdown', {})}\n\n"
        f"Milestones:\n{milestones_str or 'None defined'}\n\n"
        f"Current tasks:\n{tasks_summary or 'No tasks found'}\n\n"
        "Identify:\n"
        "1. Missing tasks that should exist but don't\n"
        "2. Missing prerequisites for existing tasks\n"
        "3. A backward plan from deadline to present (if deadline exists)\n\n"
        "Respond with a JSON object containing:\n"
        '  "missing_tasks": list of task description strings\n'
        '  "missing_prerequisites": list of prerequisite description strings\n'
        '  "backward_plan": list of objects with {task, estimated_days, depends_on, priority}'
    )

    schema = {
        "type": "object",
        "properties": {
            "missing_tasks": {"type": "array", "items": {"type": "string"}},
            "missing_prerequisites": {"type": "array", "items": {"type": "string"}},
            "backward_plan": {
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
        "required": ["missing_tasks", "missing_prerequisites", "backward_plan"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a project management analyst. Identify gaps and missing items in project plans.",
        )

        backward_plan = [
            BackwardPlanItem(
                task=item.get("task", ""),
                estimated_days=item.get("estimated_days", 1),
                depends_on=item.get("depends_on", []),
                priority=item.get("priority", "medium"),
            )
            for item in result.get("backward_plan", [])
        ]

        return GapAnalysis(
            missing_tasks=result.get("missing_tasks", []),
            missing_prerequisites=result.get("missing_prerequisites", []),
            backward_plan=backward_plan,
        )

    except Exception as exc:
        logger.warning("AI gap detection failed: %s", exc)
        return _heuristic_gap_detection(project, context)


def _heuristic_gap_detection(
    project: dict[str, Any],
    context: dict[str, Any],
) -> GapAnalysis:
    """Fallback heuristic gap detection when AI is unavailable."""
    missing_tasks: list[str] = []
    missing_prerequisites: list[str] = []
    backward_plan: list[BackwardPlanItem] = []

    tasks = context.get("tasks", [])
    status_breakdown = context.get("status_breakdown", {})

    # Check if there are no tasks at all
    if not tasks:
        missing_tasks.append("No tasks have been created for this project")
        return GapAnalysis(
            missing_tasks=missing_tasks,
            missing_prerequisites=missing_prerequisites,
            backward_plan=backward_plan,
        )

    # Check for common missing task patterns
    task_types = {t.get("issue_type", "").lower() for t in tasks}
    task_labels = set()
    for t in tasks:
        for label in t.get("labels", []):
            task_labels.add(label.lower())

    if "bug" not in task_types and len(tasks) > 10:
        missing_tasks.append("No bug tracking tasks found -- consider adding QA/testing tasks")

    if "epic" not in task_types and len(tasks) > 15:
        missing_tasks.append(
            "No epics defined -- consider organizing tasks into epics for better tracking"
        )

    if not any(t.get("due_date") for t in tasks):
        missing_prerequisites.append(
            "No due dates set on any tasks -- add due dates for timeline tracking"
        )

    # Check for unassigned tasks
    unassigned = [t for t in tasks if not t.get("assignee")]
    if len(unassigned) > len(tasks) * 0.3:
        missing_prerequisites.append(
            f"{len(unassigned)} tasks ({int(len(unassigned)/len(tasks)*100)}%) are unassigned"
        )

    # Check blocked ratio
    blocked = status_breakdown.get("blocked", 0) + status_breakdown.get("impediment", 0)
    if blocked > 0:
        missing_prerequisites.append(
            f"{blocked} blocked tasks need resolution before progress can continue"
        )

    # Simple backward plan if deadline exists
    deadline = context.get("deadline")
    if deadline and isinstance(deadline, datetime):
        days_remaining = (deadline - datetime.now(UTC)).days
        done_ratio = sum(
            v for k, v in status_breakdown.items() if k in ("done", "closed", "resolved")
        ) / max(len(tasks), 1)
        remaining_ratio = 1.0 - done_ratio

        if remaining_ratio > 0 and days_remaining > 0:
            backward_plan.append(
                BackwardPlanItem(
                    task="Complete remaining tasks",
                    estimated_days=max(1, int(days_remaining * 0.7)),
                    depends_on=[],
                    priority="high" if remaining_ratio > 0.5 else "medium",
                )
            )
            backward_plan.append(
                BackwardPlanItem(
                    task="Final testing and QA",
                    estimated_days=max(1, int(days_remaining * 0.2)),
                    depends_on=["Complete remaining tasks"],
                    priority="high",
                )
            )
            backward_plan.append(
                BackwardPlanItem(
                    task="Release preparation and deployment",
                    estimated_days=max(1, int(days_remaining * 0.1)),
                    depends_on=["Final testing and QA"],
                    priority="critical",
                )
            )

    return GapAnalysis(
        missing_tasks=missing_tasks,
        missing_prerequisites=missing_prerequisites,
        backward_plan=backward_plan,
    )
