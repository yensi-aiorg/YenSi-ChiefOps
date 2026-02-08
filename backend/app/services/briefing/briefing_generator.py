"""
Morning briefing generator.

Compiles a daily briefing for the COO that summarises project health,
active blockers, team activity, overnight changes, and upcoming
deadlines across all projects.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def generate_briefing(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Generate a morning briefing for the COO.

    Compiles data from all projects, people, and recent activity
    into a structured briefing document.

    Args:
        db: Motor database handle.
        ai_adapter: AI adapter instance (can be None for data-only briefing).

    Returns:
        The generated briefing document.
    """
    now = datetime.now(UTC)
    yesterday = now - timedelta(hours=24)

    # Gather briefing data
    data = await _gather_briefing_data(db, yesterday, now)

    # Generate briefing content
    if ai_adapter is not None:
        briefing_content = await _ai_generate_briefing(data, ai_adapter)
    else:
        briefing_content = _heuristic_generate_briefing(data)

    # Build briefing document
    briefing_doc: dict[str, Any] = {
        "briefing_id": generate_uuid(),
        "date": now.strftime("%Y-%m-%d"),
        "title": f"Morning Briefing - {now.strftime('%B %d, %Y')}",
        "summary": briefing_content.get("summary", ""),
        "sections": briefing_content.get("sections", []),
        "action_items": briefing_content.get("action_items", []),
        "metrics": briefing_content.get("metrics", {}),
        "data": data,
        "created_at": utc_now(),
    }

    await db.briefings.insert_one(briefing_doc)

    logger.info("Generated morning briefing for %s", now.strftime("%Y-%m-%d"))
    return briefing_doc


async def _gather_briefing_data(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    since: datetime,
    now: datetime,
) -> dict[str, Any]:
    """Gather all data needed for the briefing."""
    data: dict[str, Any] = {}

    # Project health overview
    projects: list[dict[str, Any]] = []
    async for project in db.projects.find(
        {},
        {
            "project_id": 1,
            "name": 1,
            "status": 1,
            "health_score": 1,
            "completion_percentage": 1,
            "deadline": 1,
            "key_risks": 1,
            "task_summary": 1,
            "_id": 0,
        },
    ):
        projects.append(project)
    data["projects"] = projects
    data["project_count"] = len(projects)

    # Projects at risk
    data["at_risk_projects"] = [
        p
        for p in projects
        if p.get("status") in ("at_risk", "behind") or (p.get("health_score", 100) < 50)
    ]

    # Active blockers across all projects
    blocked_count = await db.jira_tasks.count_documents(
        {"status": {"$in": ["blocked", "impediment", "on_hold"]}}
    )
    data["total_blocked"] = blocked_count

    blocked_tasks: list[dict[str, Any]] = []
    async for task in db.jira_tasks.find(
        {"status": {"$in": ["blocked", "impediment", "on_hold"]}},
        {"task_key": 1, "summary": 1, "assignee": 1, "project_key": 1, "_id": 0},
    ).limit(20):
        blocked_tasks.append(task)
    data["blocked_tasks"] = blocked_tasks

    # Overnight activity (tasks completed since yesterday)
    completed_since = await db.jira_tasks.count_documents(
        {
            "status": {"$in": ["done", "closed", "resolved"]},
            "resolved_date": {"$gte": since},
        }
    )
    data["tasks_completed_overnight"] = completed_since

    # New tasks created since yesterday
    new_tasks = await db.jira_tasks.count_documents(
        {
            "created_date": {"$gte": since},
        }
    )
    data["new_tasks_overnight"] = new_tasks

    # Slack activity overnight
    messages_overnight = await db.slack_messages.count_documents(
        {
            "timestamp": {"$gte": since},
        }
    )
    data["messages_overnight"] = messages_overnight

    # Upcoming deadlines (next 7 days)
    seven_days_out = now + timedelta(days=7)
    upcoming_deadlines: list[dict[str, Any]] = []
    for project in projects:
        deadline = project.get("deadline")
        if deadline and isinstance(deadline, datetime) and now <= deadline <= seven_days_out:
            days_until = (deadline - now).days
            upcoming_deadlines.append(
                {
                    "project": project.get("name", ""),
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                }
            )
    data["upcoming_deadlines"] = upcoming_deadlines

    # Overdue tasks
    overdue_count = await db.jira_tasks.count_documents(
        {
            "due_date": {"$lt": now},
            "status": {"$nin": ["done", "closed", "resolved"]},
        }
    )
    data["overdue_tasks"] = overdue_count

    # Active alerts
    active_alerts: list[dict[str, Any]] = []
    async for alert in db.alerts.find(
        {"active": True, "triggered": True},
        {"name": 1, "condition_description": 1, "last_triggered": 1, "_id": 0},
    ):
        active_alerts.append(alert)
    data["active_alerts"] = active_alerts

    # Team size
    team_size = await db.people.count_documents({})
    data["team_size"] = team_size

    # Active team members (activity in last 7 days)
    active_members = await db.people.count_documents(
        {
            "activity_level": {"$in": ["very_active", "active"]},
        }
    )
    data["active_members"] = active_members

    return data


async def _ai_generate_briefing(
    data: dict[str, Any],
    ai_adapter: Any,
) -> dict[str, Any]:
    """Use AI to generate a natural language briefing."""
    # Build context for AI
    context_parts = [
        f"Total projects: {data.get('project_count', 0)}",
        f"Projects at risk: {len(data.get('at_risk_projects', []))}",
        f"Total blocked tasks: {data.get('total_blocked', 0)}",
        f"Tasks completed overnight: {data.get('tasks_completed_overnight', 0)}",
        f"New tasks created overnight: {data.get('new_tasks_overnight', 0)}",
        f"Slack messages overnight: {data.get('messages_overnight', 0)}",
        f"Overdue tasks: {data.get('overdue_tasks', 0)}",
        f"Active alerts: {len(data.get('active_alerts', []))}",
        f"Team size: {data.get('team_size', 0)} (active: {data.get('active_members', 0)})",
    ]

    if data.get("at_risk_projects"):
        context_parts.append("\nAt-risk projects:")
        for p in data["at_risk_projects"]:
            context_parts.append(
                f"  - {p.get('name', '')}: health={p.get('health_score', 'N/A')}, "
                f"status={p.get('status', '')}"
            )

    if data.get("upcoming_deadlines"):
        context_parts.append("\nUpcoming deadlines:")
        for d in data["upcoming_deadlines"]:
            context_parts.append(f"  - {d['project']}: {d['deadline']} ({d['days_until']} days)")

    if data.get("blocked_tasks"):
        context_parts.append("\nTop blocked tasks:")
        for t in data["blocked_tasks"][:5]:
            context_parts.append(
                f"  - [{t.get('task_key', '')}] {t.get('summary', '')} "
                f"(assignee: {t.get('assignee', 'unassigned')})"
            )

    context = "\n".join(context_parts)

    prompt = (
        "Generate a morning briefing for a COO based on this data.\n\n"
        f"{context}\n\n"
        "Create a briefing with:\n"
        '  "summary": A 2-3 sentence executive summary of the most important things\n'
        '  "sections": [{heading, content}] covering: project health, blockers, '
        "overnight activity, upcoming deadlines, team status\n"
        '  "action_items": specific things the COO should address today'
    )

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["heading", "content"],
                },
            },
            "action_items": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "sections", "action_items"],
    }

    try:
        return await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a Chief of Staff AI. Write concise, actionable morning briefings.",
        )
    except Exception as exc:
        logger.warning("AI briefing generation failed: %s", exc)
        return _heuristic_generate_briefing(data)


def _heuristic_generate_briefing(data: dict[str, Any]) -> dict[str, Any]:
    """Generate a data-driven briefing without AI."""
    sections: list[dict[str, str]] = []

    # Project health overview
    projects = data.get("projects", [])
    at_risk = data.get("at_risk_projects", [])

    health_content = f"Total projects: {len(projects)}\n"
    if at_risk:
        health_content += f"Projects at risk: {len(at_risk)}\n"
        for p in at_risk:
            health_content += (
                f"- {p.get('name', '')}: health score {p.get('health_score', 'N/A')}\n"
            )
    else:
        health_content += "All projects are on track."

    sections.append({"heading": "Project Health", "content": health_content})

    # Blockers
    blocked = data.get("total_blocked", 0)
    if blocked > 0:
        blocker_content = f"{blocked} tasks are currently blocked.\n"
        for t in data.get("blocked_tasks", [])[:5]:
            blocker_content += f"- [{t.get('task_key', '')}] {t.get('summary', '')}\n"
        sections.append({"heading": "Active Blockers", "content": blocker_content})

    # Overnight activity
    activity_content = (
        f"Tasks completed: {data.get('tasks_completed_overnight', 0)}\n"
        f"New tasks created: {data.get('new_tasks_overnight', 0)}\n"
        f"Slack messages: {data.get('messages_overnight', 0)}"
    )
    sections.append({"heading": "Overnight Activity", "content": activity_content})

    # Upcoming deadlines
    deadlines = data.get("upcoming_deadlines", [])
    if deadlines:
        deadline_content = ""
        for d in deadlines:
            deadline_content += f"- {d['project']}: {d['deadline']} ({d['days_until']} days)\n"
        sections.append({"heading": "Upcoming Deadlines", "content": deadline_content})

    # Summary
    summary_parts = []
    if at_risk:
        summary_parts.append(f"{len(at_risk)} project(s) need attention")
    if blocked > 0:
        summary_parts.append(f"{blocked} blocked tasks require resolution")
    if data.get("overdue_tasks", 0) > 0:
        summary_parts.append(f"{data['overdue_tasks']} overdue tasks")

    summary = ". ".join(summary_parts) + "." if summary_parts else "All systems nominal."

    # Action items
    action_items: list[str] = []
    if at_risk:
        action_items.append(f"Review {len(at_risk)} at-risk project(s)")
    if blocked > 0:
        action_items.append(f"Address {blocked} blocked tasks")
    if data.get("overdue_tasks", 0) > 0:
        action_items.append(f"Follow up on {data['overdue_tasks']} overdue tasks")
    if deadlines:
        action_items.append(f"Check in on {len(deadlines)} upcoming deadline(s)")

    return {
        "summary": summary,
        "sections": sections,
        "action_items": action_items,
        "metrics": {
            "project_count": len(projects),
            "at_risk_count": len(at_risk),
            "blocked_count": blocked,
            "overdue_count": data.get("overdue_tasks", 0),
            "team_size": data.get("team_size", 0),
        },
    }
