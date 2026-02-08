"""
Report generation service.

Assembles data context from project metrics, team status, and task
data, then uses AI to generate a structured report specification
that the frontend can render and export.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Report types
REPORT_TYPES = [
    "weekly_status",
    "sprint_review",
    "project_health",
    "team_performance",
    "risk_assessment",
    "executive_summary",
    "custom",
]


async def generate_report(
    message: str,
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Generate a report specification from a natural language request.

    Assembles project data context, sends to AI for report generation,
    and stores the result in MongoDB.

    Args:
        message: Natural language description of the desired report.
        project_id: Project scope for the report.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        The generated report specification document.
    """
    # Gather data context
    data_context = await _gather_report_context(project_id, db)

    # Detect report type
    report_type = _detect_report_type(message)

    # Generate report spec
    if ai_adapter is not None:
        report_spec = await _ai_generate_report(message, data_context, report_type, ai_adapter)
    else:
        report_spec = _heuristic_generate_report(message, data_context, report_type)

    # Store report
    report_doc: dict[str, Any] = {
        "report_id": generate_uuid(),
        "project_id": project_id,
        "report_type": report_type,
        "title": report_spec.get("title", "Report"),
        "description": message,
        "sections": report_spec.get("sections", []),
        "summary": report_spec.get("summary", ""),
        "key_metrics": report_spec.get("key_metrics", []),
        "recommendations": report_spec.get("recommendations", []),
        "generated_at": utc_now(),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    await db.reports.insert_one(report_doc)

    logger.info("Generated report '%s' (type: %s)", report_doc["title"], report_type)
    return report_doc


async def _gather_report_context(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Gather all data needed for report generation."""
    context: dict[str, Any] = {}

    # Project info
    project = await db.projects.find_one({"project_id": project_id})
    if project:
        context["project"] = {
            "name": project.get("name", ""),
            "description": project.get("description", ""),
            "status": project.get("status", ""),
            "completion_percentage": project.get("completion_percentage", 0),
            "health_score": project.get("health_score", 50),
            "deadline": project.get("deadline"),
            "key_risks": project.get("key_risks", []),
            "missing_tasks": project.get("missing_tasks", []),
            "technical_concerns": project.get("technical_concerns", []),
        }

        # Task summary
        context["task_summary"] = project.get("task_summary", {})

        # Sprint health
        context["sprint_health"] = project.get("sprint_health", {})

        # People
        context["team"] = project.get("people_involved", [])

        # Gather detailed task data
        jira_keys = project.get("jira_project_keys", [])
        if jira_keys:
            # Task status breakdown
            pipeline = [
                {"$match": {"project_key": {"$in": jira_keys}}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            status_breakdown: dict[str, int] = {}
            async for doc in db.jira_tasks.aggregate(pipeline):
                status_breakdown[doc["_id"]] = doc["count"]
            context["status_breakdown"] = status_breakdown

            # Assignee workload
            pipeline = [
                {"$match": {"project_key": {"$in": jira_keys}}},
                {
                    "$group": {
                        "_id": "$assignee",
                        "total": {"$sum": 1},
                        "completed": {
                            "$sum": {
                                "$cond": [
                                    {"$in": ["$status", ["done", "closed", "resolved"]]},
                                    1,
                                    0,
                                ]
                            }
                        },
                    }
                },
                {"$sort": {"total": -1}},
                {"$limit": 20},
            ]
            workload: list[dict[str, Any]] = []
            async for doc in db.jira_tasks.aggregate(pipeline):
                workload.append(
                    {
                        "assignee": doc["_id"] or "Unassigned",
                        "total": doc["total"],
                        "completed": doc["completed"],
                    }
                )
            context["workload"] = workload

            # Recently completed tasks
            recent_completed: list[dict[str, Any]] = []
            async for task in (
                db.jira_tasks.find(
                    {
                        "project_key": {"$in": jira_keys},
                        "status": {"$in": ["done", "closed", "resolved"]},
                    },
                    {"task_key": 1, "summary": 1, "assignee": 1, "resolved_date": 1, "_id": 0},
                )
                .sort("resolved_date", -1)
                .limit(10)
            ):
                recent_completed.append(task)
            context["recent_completed"] = recent_completed

            # Blocked tasks
            blocked: list[dict[str, Any]] = []
            async for task in db.jira_tasks.find(
                {
                    "project_key": {"$in": jira_keys},
                    "status": {"$in": ["blocked", "impediment", "on_hold"]},
                },
                {"task_key": 1, "summary": 1, "assignee": 1, "_id": 0},
            ):
                blocked.append(task)
            context["blocked_tasks"] = blocked

    return context


def _detect_report_type(message: str) -> str:
    """Detect the report type from the message."""
    msg_lower = message.lower()

    type_keywords: dict[str, list[str]] = {
        "weekly_status": ["weekly", "week", "status update", "weekly status"],
        "sprint_review": ["sprint", "sprint review", "sprint summary", "iteration"],
        "project_health": ["health", "health report", "project health"],
        "team_performance": ["team", "performance", "team performance", "contributor"],
        "risk_assessment": ["risk", "risk assessment", "risk report", "risks"],
        "executive_summary": ["executive", "exec", "summary", "overview", "board"],
    }

    for report_type, keywords in type_keywords.items():
        if any(kw in msg_lower for kw in keywords):
            return report_type

    return "custom"


async def _ai_generate_report(
    message: str,
    context: dict[str, Any],
    report_type: str,
    ai_adapter: Any,
) -> dict[str, Any]:
    """Use AI to generate a report specification."""
    # Build context string
    project_info = context.get("project", {})
    task_summary = context.get("task_summary", {})
    sprint_health = context.get("sprint_health", {})

    context_text = (
        f"Project: {project_info.get('name', 'Unknown')}\n"
        f"Status: {project_info.get('status', 'N/A')}\n"
        f"Completion: {project_info.get('completion_percentage', 0)}%\n"
        f"Health Score: {project_info.get('health_score', 'N/A')}\n\n"
        f"Task Summary: {task_summary}\n"
        f"Sprint Health: {sprint_health}\n"
        f"Status Breakdown: {context.get('status_breakdown', {})}\n\n"
        f"Key Risks: {project_info.get('key_risks', [])}\n"
        f"Blocked Tasks: {len(context.get('blocked_tasks', []))}\n"
        f"Team Size: {len(context.get('team', []))}\n\n"
        f"Workload Distribution: {context.get('workload', [])}\n"
        f"Recently Completed: {[t.get('summary', '') for t in context.get('recent_completed', [])[:5]]}\n"
    )

    prompt = (
        f"Generate a {report_type.replace('_', ' ')} report based on this data.\n\n"
        f"Request: {message}\n\n"
        f"Data:\n{context_text}\n\n"
        "Generate a JSON report specification with:\n"
        '  "title": Report title\n'
        '  "summary": Executive summary paragraph\n'
        '  "sections": [\n'
        '    {"heading": "Section Title", "content": "Section content text", '
        '"type": "text" | "metric" | "table" | "list"}\n'
        "  ]\n"
        '  "key_metrics": [{"label": "Metric Name", "value": "Value", "trend": "up|down|stable"}]\n'
        '  "recommendations": ["Action item 1", "Action item 2"]'
    )

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"},
                        "type": {"type": "string", "enum": ["text", "metric", "table", "list"]},
                    },
                    "required": ["heading", "content"],
                },
            },
            "key_metrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                        "trend": {"type": "string"},
                    },
                    "required": ["label", "value"],
                },
            },
            "recommendations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "summary", "sections"],
    }

    try:
        return await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a report writer for a technology company COO. Write clear, data-driven reports.",
        )
    except Exception as exc:
        logger.warning("AI report generation failed: %s", exc)
        return _heuristic_generate_report(message, context, report_type)


def _heuristic_generate_report(
    message: str,
    context: dict[str, Any],
    report_type: str,
) -> dict[str, Any]:
    """Generate a basic report without AI."""
    project_info = context.get("project", {})
    task_summary = context.get("task_summary", {})

    title = f"{report_type.replace('_', ' ').title()} Report"
    if project_info.get("name"):
        title += f": {project_info['name']}"

    sections: list[dict[str, str]] = []

    # Overview section
    sections.append(
        {
            "heading": "Project Overview",
            "content": (
                f"Project: {project_info.get('name', 'N/A')}\n"
                f"Status: {project_info.get('status', 'N/A')}\n"
                f"Completion: {project_info.get('completion_percentage', 0):.1f}%\n"
                f"Health Score: {project_info.get('health_score', 'N/A')}/100"
            ),
            "type": "text",
        }
    )

    # Task summary section
    if task_summary:
        sections.append(
            {
                "heading": "Task Summary",
                "content": (
                    f"Total: {task_summary.get('total', 0)}\n"
                    f"Completed: {task_summary.get('completed', 0)}\n"
                    f"In Progress: {task_summary.get('in_progress', 0)}\n"
                    f"Blocked: {task_summary.get('blocked', 0)}\n"
                    f"To Do: {task_summary.get('to_do', 0)}"
                ),
                "type": "metric",
            }
        )

    # Risks section
    risks = project_info.get("key_risks", [])
    if risks:
        sections.append(
            {
                "heading": "Key Risks",
                "content": "\n".join(f"- {r}" for r in risks),
                "type": "list",
            }
        )

    # Blocked tasks
    blocked = context.get("blocked_tasks", [])
    if blocked:
        sections.append(
            {
                "heading": "Blocked Items",
                "content": "\n".join(
                    f"- [{t.get('task_key', '')}] {t.get('summary', '')} (Assignee: {t.get('assignee', 'N/A')})"
                    for t in blocked
                ),
                "type": "list",
            }
        )

    # Key metrics
    key_metrics: list[dict[str, str]] = []
    if task_summary:
        total = task_summary.get("total", 0)
        completed = task_summary.get("completed", 0)
        key_metrics.append({"label": "Total Tasks", "value": str(total), "trend": "stable"})
        key_metrics.append({"label": "Completed", "value": str(completed), "trend": "up"})
        key_metrics.append(
            {"label": "Blocked", "value": str(task_summary.get("blocked", 0)), "trend": "stable"}
        )

    key_metrics.append(
        {
            "label": "Health Score",
            "value": str(project_info.get("health_score", "N/A")),
            "trend": "stable",
        }
    )

    return {
        "title": title,
        "summary": f"This report covers the current state of {project_info.get('name', 'the project')}.",
        "sections": sections,
        "key_metrics": key_metrics,
        "recommendations": [],
    }
