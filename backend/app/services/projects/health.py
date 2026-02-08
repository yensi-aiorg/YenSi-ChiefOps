"""
Sprint health calculation for projects.

Computes a composite health score from completion rate, velocity
trend, blocker count, and other metrics derived from Jira task data.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.models.base import utc_now
from app.models.project import SprintHealth

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def calculate_health(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> SprintHealth:
    """Calculate sprint health metrics for a project.

    Gathers task data from the ``jira_tasks`` collection and computes:
    - Completion rate: percentage of tasks in done/closed status
    - Velocity trend: comparing recent completion to historical
    - Blocker count: tasks in blocked status
    - Composite score: weighted combination of all metrics

    Args:
        project_id: Project identifier.
        db: Motor database handle.

    Returns:
        A ``SprintHealth`` instance with computed metrics.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return SprintHealth()

    jira_keys = project.get("jira_project_keys", [])
    if not jira_keys:
        return SprintHealth()

    # Gather all tasks for this project
    task_query = {"project_key": {"$in": jira_keys}}
    total_tasks = await db.jira_tasks.count_documents(task_query)

    if total_tasks == 0:
        return SprintHealth()

    # Status breakdown
    done_count = await db.jira_tasks.count_documents(
        {
            **task_query,
            "status": {"$in": ["done", "closed", "resolved"]},
        }
    )
    blocked_count = await db.jira_tasks.count_documents(
        {
            **task_query,
            "status": {"$in": ["blocked", "impediment", "on_hold"]},
        }
    )
    in_progress_count = await db.jira_tasks.count_documents(
        {
            **task_query,
            "status": {"$in": ["in_progress", "in_development", "in_review", "in_testing"]},
        }
    )

    # Completion rate
    completion_rate = (done_count / total_tasks) * 100 if total_tasks > 0 else 0.0

    # Velocity trend
    velocity_trend = await _calculate_velocity_trend(jira_keys, db)

    # Composite score (0-100)
    score = _calculate_composite_score(
        completion_rate=completion_rate,
        blocker_count=blocked_count,
        total_tasks=total_tasks,
        in_progress_count=in_progress_count,
        velocity_trend=velocity_trend,
    )

    health = SprintHealth(
        completion_rate=round(completion_rate, 1),
        velocity_trend=velocity_trend,
        blocker_count=blocked_count,
        score=score,
    )

    # Store health score history
    await db.health_scores.insert_one(
        {
            "project_id": project_id,
            "score": score,
            "completion_rate": completion_rate,
            "blocker_count": blocked_count,
            "velocity_trend": velocity_trend,
            "total_tasks": total_tasks,
            "done_count": done_count,
            "created_at": utc_now(),
        }
    )

    return health


async def _calculate_velocity_trend(
    jira_keys: list[str],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Calculate velocity trend by comparing recent completion rates."""
    now = datetime.now(UTC)
    two_weeks_ago = now - timedelta(days=14)
    four_weeks_ago = now - timedelta(days=28)

    task_query = {"project_key": {"$in": jira_keys}}

    # Recent period completions (last 2 weeks)
    recent_completed = await db.jira_tasks.count_documents(
        {
            **task_query,
            "status": {"$in": ["done", "closed", "resolved"]},
            "resolved_date": {"$gte": two_weeks_ago},
        }
    )

    # Previous period completions (2-4 weeks ago)
    previous_completed = await db.jira_tasks.count_documents(
        {
            **task_query,
            "status": {"$in": ["done", "closed", "resolved"]},
            "resolved_date": {"$gte": four_weeks_ago, "$lt": two_weeks_ago},
        }
    )

    if previous_completed == 0 and recent_completed == 0:
        return "stable"
    if previous_completed == 0:
        return "increasing"

    ratio = recent_completed / previous_completed
    if ratio > 1.15:
        return "increasing"
    if ratio < 0.85:
        return "decreasing"
    return "stable"


def _calculate_composite_score(
    completion_rate: float,
    blocker_count: int,
    total_tasks: int,
    in_progress_count: int,
    velocity_trend: str,
) -> int:
    """Calculate composite health score (0-100).

    Weights:
    - Completion rate: 40%
    - Blocker impact: 25% (inverse)
    - Work in progress ratio: 15%
    - Velocity trend: 20%
    """
    # Completion score (0-100)
    completion_score = min(completion_rate, 100.0)

    # Blocker score (inverse -- more blockers = lower score)
    if total_tasks > 0:
        blocker_ratio = blocker_count / total_tasks
        blocker_score = max(0, 100 - (blocker_ratio * 500))  # Each 1% blockers costs 5 points
    else:
        blocker_score = 50.0

    # WIP ratio (healthy is 20-40% of total)
    if total_tasks > 0:
        wip_ratio = in_progress_count / total_tasks
        if 0.15 <= wip_ratio <= 0.45:
            wip_score = 100.0
        elif wip_ratio < 0.15:
            wip_score = max(0, wip_ratio / 0.15 * 100)
        else:
            wip_score = max(0, 100 - ((wip_ratio - 0.45) * 200))
    else:
        wip_score = 50.0

    # Velocity trend score
    velocity_scores = {"increasing": 100, "stable": 70, "decreasing": 30}
    velocity_score = velocity_scores.get(velocity_trend, 50)

    # Weighted composite
    composite = (
        completion_score * 0.40 + blocker_score * 0.25 + wip_score * 0.15 + velocity_score * 0.20
    )

    return max(0, min(100, int(round(composite))))
