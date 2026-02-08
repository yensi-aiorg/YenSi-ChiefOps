"""
Project analysis orchestrator.

Coordinates all project sub-analyses (health, gaps, feasibility) and
updates the project document with results. Also provides a function
to analyze all projects after ingestion.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now
from app.models.project import ProjectStatus
from app.services.projects.feasibility import assess_feasibility
from app.services.projects.gaps import detect_gaps
from app.services.projects.health import calculate_health

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def analyze_project(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Run full analysis on a single project.

    Gathers all related data and runs sub-analyses:
    - Sprint health calculation
    - Gap detection
    - Technical feasibility assessment

    Updates the project document with results.

    Args:
        project_id: Project identifier.
        db: Motor database handle.
        ai_adapter: AI adapter instance (can be None).

    Returns:
        The updated project analysis as a dict.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        logger.warning("Project %s not found for analysis", project_id)
        return {}

    logger.info("Analyzing project: %s (%s)", project.get("name", ""), project_id)

    # Run sub-analyses
    health = await calculate_health(project_id, db)
    gap_analysis = await detect_gaps(project_id, db, ai_adapter)
    feasibility = await assess_feasibility(project_id, db, ai_adapter)

    # Update task summary
    task_summary = await _compute_task_summary(project, db)

    # Compute completion percentage
    total = task_summary.get("total", 0)
    completed = task_summary.get("completed", 0)
    completion_pct = (completed / total * 100) if total > 0 else 0.0

    # Determine project status
    status = _determine_status(health.score, gap_analysis, completion_pct)

    # Extract key risks from feasibility
    key_risks = [r.risk for r in feasibility.risk_items if r.severity in ("critical", "high")]

    # Update project document
    update_data: dict[str, Any] = {
        "sprint_health": health.model_dump(),
        "gap_analysis": gap_analysis.model_dump(),
        "technical_feasibility": feasibility.model_dump(),
        "task_summary": task_summary,
        "completion_percentage": round(completion_pct, 1),
        "health_score": health.score,
        "status": status.value,
        "key_risks": key_risks,
        "missing_tasks": gap_analysis.missing_tasks,
        "technical_concerns": [r.risk for r in feasibility.risk_items],
        "last_analyzed_at": utc_now(),
        "updated_at": utc_now(),
    }

    await db.projects.update_one(
        {"project_id": project_id},
        {"$set": update_data},
    )

    logger.info(
        "Project %s analysis complete: health=%d, status=%s, completion=%.1f%%",
        project_id,
        health.score,
        status.value,
        completion_pct,
    )

    return {
        "project_id": project_id,
        "health": health.model_dump(),
        "gap_analysis": gap_analysis.model_dump(),
        "feasibility": feasibility.model_dump(),
        "task_summary": task_summary,
        "completion_percentage": completion_pct,
        "status": status.value,
    }


async def analyze_all_projects(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> list[dict[str, Any]]:
    """Analyze all projects in the database.

    Called after ingestion completes to refresh all project analyses.
    Also discovers new projects from Jira data.

    Args:
        db: Motor database handle.
        ai_adapter: AI adapter instance (can be None).

    Returns:
        List of analysis results for each project.
    """
    # Discover projects from Jira data
    await _discover_projects(db)

    # Analyze each project
    results: list[dict[str, Any]] = []
    async for project in db.projects.find({}, {"project_id": 1}):
        project_id = project.get("project_id", "")
        if not project_id:
            continue

        try:
            result = await analyze_project(project_id, db, ai_adapter)
            results.append(result)
        except Exception as exc:
            logger.exception("Analysis failed for project %s", project_id)
            results.append({"project_id": project_id, "error": str(exc)})

    logger.info("Analyzed %d projects", len(results))
    return results


async def _discover_projects(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Discover new projects from Jira data and create project documents."""
    # Get distinct Jira project keys
    project_keys = await db.jira_tasks.distinct("project_key")

    for key in project_keys:
        if not key:
            continue

        # Check if project already exists
        existing = await db.projects.find_one({"jira_project_keys": key})
        if existing:
            continue

        # Get project name from tasks
        sample_task = await db.jira_tasks.find_one(
            {"project_key": key},
            {"project_name": 1},
        )
        project_name = ""
        if sample_task:
            project_name = sample_task.get("project_name", "")
        if not project_name:
            project_name = key

        # Create project document
        project_doc = {
            "project_id": generate_uuid(),
            "name": project_name,
            "description": f"Auto-discovered project from Jira key: {key}",
            "status": ProjectStatus.ON_TRACK.value,
            "completion_percentage": 0.0,
            "jira_project_keys": [key],
            "slack_channels": [],
            "people_involved": [],
            "milestones": [],
            "task_summary": {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "blocked": 0,
                "to_do": 0,
            },
            "health_score": 50,
            "key_risks": [],
            "missing_tasks": [],
            "technical_concerns": [],
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "last_analyzed_at": utc_now(),
        }
        await db.projects.insert_one(project_doc)
        logger.info("Discovered new project: %s (Jira key: %s)", project_name, key)

    # Also try to link Slack channels to projects
    await _link_slack_channels(db)


async def _link_slack_channels(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Attempt to link Slack channels to projects by name matching."""
    async for project in db.projects.find({}):
        project_name = project.get("name", "").lower()
        jira_keys = [k.lower() for k in project.get("jira_project_keys", [])]
        current_channels = project.get("slack_channels", [])

        if current_channels:
            continue  # Already has channels linked

        # Search for matching channel names
        matching_channels: list[str] = []
        async for channel in db.slack_channels.find({}):
            channel_name = channel.get("name", "").lower()
            # Match by project name or Jira key
            if any(key in channel_name for key in jira_keys) or (
                project_name and len(project_name) > 3 and project_name in channel_name
            ):
                matching_channels.append(channel.get("name", ""))

        if matching_channels:
            await db.projects.update_one(
                {"project_id": project["project_id"]},
                {
                    "$set": {
                        "slack_channels": matching_channels,
                        "updated_at": utc_now(),
                    }
                },
            )
            logger.info(
                "Linked channels %s to project %s",
                matching_channels,
                project.get("name", ""),
            )


async def _compute_task_summary(
    project: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, int]:
    """Compute aggregated task counts for a project."""
    jira_keys = project.get("jira_project_keys", [])
    if not jira_keys:
        return {"total": 0, "completed": 0, "in_progress": 0, "blocked": 0, "to_do": 0}

    query = {"project_key": {"$in": jira_keys}}
    total = await db.jira_tasks.count_documents(query)

    completed = await db.jira_tasks.count_documents(
        {
            **query,
            "status": {"$in": ["done", "closed", "resolved"]},
        }
    )

    in_progress = await db.jira_tasks.count_documents(
        {
            **query,
            "status": {
                "$in": ["in_progress", "in_development", "in_review", "in_testing", "code_review"]
            },
        }
    )

    blocked = await db.jira_tasks.count_documents(
        {
            **query,
            "status": {"$in": ["blocked", "impediment", "on_hold"]},
        }
    )

    to_do = total - completed - in_progress - blocked

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "blocked": blocked,
        "to_do": max(0, to_do),
    }


def _determine_status(
    health_score: int,
    gap_analysis: Any,
    completion_pct: float,
) -> ProjectStatus:
    """Determine overall project status from metrics."""
    if completion_pct >= 95:
        return ProjectStatus.COMPLETED

    # Count critical issues
    critical_issues = 0
    if gap_analysis.missing_tasks:
        critical_issues += len(gap_analysis.missing_tasks)
    if gap_analysis.missing_prerequisites:
        critical_issues += len(gap_analysis.missing_prerequisites)

    if health_score >= 70 and critical_issues <= 2:
        return ProjectStatus.ON_TRACK
    if health_score >= 40 or critical_issues <= 5:
        return ProjectStatus.AT_RISK
    return ProjectStatus.BEHIND
