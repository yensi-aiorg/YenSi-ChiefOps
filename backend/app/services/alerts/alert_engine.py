"""
Alert engine for threshold-based monitoring.

Parses natural language alert definitions into structured thresholds,
evaluates them against current data, and manages alert lifecycle
(creation, evaluation, triggering, acknowledgment).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Supported alert types
ALERT_TYPES = [
    "task_blocker_count",
    "completion_rate",
    "health_score",
    "velocity_change",
    "unassigned_tasks",
    "overdue_tasks",
    "team_activity",
    "narrative_signal",
    "custom",
]

# Comparison operators
OPERATORS = {
    "greater_than": lambda a, b: a > b,
    "less_than": lambda a, b: a < b,
    "equals": lambda a, b: a == b,
    "greater_equal": lambda a, b: a >= b,
    "less_equal": lambda a, b: a <= b,
    "not_equals": lambda a, b: a != b,
}


async def create_alert_from_nl(
    description: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Create an alert from a natural language description.

    Parses the description to extract the metric, threshold,
    comparison operator, and creates a structured alert document.

    Args:
        description: Natural language alert description.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        The created alert document.
    """
    if ai_adapter is not None:
        alert_spec = await _ai_parse_alert(description, ai_adapter)
    else:
        alert_spec = _heuristic_parse_alert(description)

    alert_doc: dict[str, Any] = {
        "alert_id": generate_uuid(),
        "name": alert_spec.get("name", "Alert"),
        "description": description,
        "alert_type": alert_spec.get("alert_type", "custom"),
        "condition": {
            "metric": alert_spec.get("metric", ""),
            "operator": alert_spec.get("operator", "greater_than"),
            "threshold": alert_spec.get("threshold", 0),
            "collection": alert_spec.get("collection", "jira_tasks"),
            "filters": alert_spec.get("filters", {}),
        },
        "condition_description": alert_spec.get("condition_description", description),
        "active": True,
        "triggered": False,
        "last_evaluated": None,
        "last_triggered": None,
        "trigger_count": 0,
        "acknowledged": False,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    await db.alerts.insert_one(alert_doc)
    logger.info("Created alert '%s' (type: %s)", alert_doc["name"], alert_doc["alert_type"])
    return alert_doc


async def evaluate_alerts(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[dict[str, Any]]:
    """Evaluate all active alerts against current data.

    Checks each active alert's condition against the database and
    triggers alerts whose thresholds are exceeded.

    Args:
        db: Motor database handle.

    Returns:
        List of triggered alert documents.
    """
    triggered: list[dict[str, Any]] = []

    async for alert in db.alerts.find({"active": True}):
        try:
            is_triggered = await _evaluate_single_alert(alert, db)

            update: dict[str, Any] = {
                "last_evaluated": utc_now(),
                "updated_at": utc_now(),
            }

            if is_triggered and not alert.get("triggered"):
                update["triggered"] = True
                update["last_triggered"] = utc_now()
                update["trigger_count"] = alert.get("trigger_count", 0) + 1
                update["acknowledged"] = False
                triggered.append(alert)
                logger.info("Alert triggered: %s", alert.get("name", ""))

            elif not is_triggered and alert.get("triggered"):
                update["triggered"] = False

            await db.alerts.update_one(
                {"alert_id": alert["alert_id"]},
                {"$set": update},
            )

        except Exception as exc:
            logger.warning(
                "Error evaluating alert %s: %s",
                alert.get("alert_id", ""),
                exc,
            )

    if triggered:
        logger.info("%d alerts triggered", len(triggered))
    return triggered


async def acknowledge_alert(
    alert_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Acknowledge a triggered alert.

    Args:
        alert_id: UUID of the alert to acknowledge.
        db: Motor database handle.

    Returns:
        The updated alert document.
    """
    await db.alerts.update_one(
        {"alert_id": alert_id},
        {
            "$set": {
                "acknowledged": True,
                "acknowledged_at": utc_now(),
                "updated_at": utc_now(),
            }
        },
    )

    alert = await db.alerts.find_one({"alert_id": alert_id})
    if alert and "_id" in alert:
        alert["_id"] = str(alert["_id"])
    return alert or {}


async def deactivate_alert(
    alert_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Deactivate an alert.

    Args:
        alert_id: UUID of the alert to deactivate.
        db: Motor database handle.
    """
    await db.alerts.update_one(
        {"alert_id": alert_id},
        {"$set": {"active": False, "updated_at": utc_now()}},
    )
    logger.info("Alert %s deactivated", alert_id)


async def _evaluate_single_alert(
    alert: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> bool:
    """Evaluate a single alert's condition against current data."""
    condition = alert.get("condition", {})
    metric = condition.get("metric", "")
    operator = condition.get("operator", "greater_than")
    threshold = condition.get("threshold", 0)
    collection = condition.get("collection", "jira_tasks")
    filters = condition.get("filters", {})

    # Get the current metric value
    current_value = await _get_metric_value(metric, collection, filters, db)
    if current_value is None:
        return False

    # Apply comparison
    op_func = OPERATORS.get(operator)
    if op_func is None:
        logger.warning("Unknown operator: %s", operator)
        return False

    return op_func(current_value, threshold)


async def _get_metric_value(
    metric: str,
    collection: str,
    filters: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> float | None:
    """Get the current value of a metric from the database."""

    if metric == "count":
        return float(await db[collection].count_documents(filters))

    if metric == "blocked_count":
        query = {**filters, "status": {"$in": ["blocked", "impediment", "on_hold"]}}
        return float(await db.jira_tasks.count_documents(query))

    if metric == "completion_rate":
        total = await db.jira_tasks.count_documents(filters)
        if total == 0:
            return 0.0
        done = await db.jira_tasks.count_documents(
            {
                **filters,
                "status": {"$in": ["done", "closed", "resolved"]},
            }
        )
        return (done / total) * 100

    if metric == "health_score":
        project = await db.projects.find_one(filters, {"health_score": 1})
        if project:
            return float(project.get("health_score", 50))
        return None

    if metric == "unassigned_count":
        query = {**filters, "assignee": {"$in": [None, ""]}}
        return float(await db.jira_tasks.count_documents(query))

    if metric == "overdue_count":
        now = datetime.now(UTC)
        query = {
            **filters,
            "due_date": {"$lt": now},
            "status": {"$nin": ["done", "closed", "resolved"]},
        }
        return float(await db.jira_tasks.count_documents(query))

    if metric == "narrative_critical_count":
        query = {
            **filters,
            "active": True,
            "severity": {"$in": ["critical", "high"]},
        }
        return float(await db.operational_insights.count_documents(query))

    # Generic count
    return float(await db[collection].count_documents(filters))


async def _ai_parse_alert(
    description: str,
    ai_adapter: Any,
) -> dict[str, Any]:
    """Use AI to parse an alert description into a structured spec."""
    prompt = (
        "Parse this alert description into a structured specification.\n\n"
        f'Description: "{description}"\n\n'
        f"Available alert types: {ALERT_TYPES}\n"
        "Available metrics: count, blocked_count, completion_rate, "
        "health_score, unassigned_count, overdue_count, narrative_critical_count\n"
        "Available operators: greater_than, less_than, equals, "
        "greater_equal, less_equal, not_equals\n\n"
        "Respond with a JSON object containing:\n"
        '  "name": short alert name\n'
        '  "alert_type": one of the available types\n'
        '  "metric": metric to monitor\n'
        '  "operator": comparison operator\n'
        '  "threshold": numeric threshold value\n'
        '  "collection": MongoDB collection to query\n'
        '  "filters": optional query filters\n'
        '  "condition_description": human-readable condition'
    )

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "alert_type": {"type": "string"},
            "metric": {"type": "string"},
            "operator": {"type": "string"},
            "threshold": {"type": "number"},
            "collection": {"type": "string"},
            "filters": {"type": "object"},
            "condition_description": {"type": "string"},
        },
        "required": ["name", "metric", "operator", "threshold"],
    }

    try:
        return await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are an alert configuration parser. Extract structured alert parameters from natural language.",
        )
    except Exception as exc:
        logger.warning("AI alert parsing failed: %s", exc)
        return _heuristic_parse_alert(description)


def _heuristic_parse_alert(description: str) -> dict[str, Any]:
    """Parse an alert description using regex heuristics."""
    desc_lower = description.lower()
    spec: dict[str, Any] = {
        "name": description[:50],
        "alert_type": "custom",
        "metric": "count",
        "operator": "greater_than",
        "threshold": 0,
        "collection": "jira_tasks",
        "filters": {},
        "condition_description": description,
    }

    # Detect blocker alerts
    if "block" in desc_lower:
        spec["alert_type"] = "task_blocker_count"
        spec["metric"] = "blocked_count"
        spec["name"] = "Blocker Count Alert"

    # Detect health score alerts
    elif "health" in desc_lower:
        spec["alert_type"] = "health_score"
        spec["metric"] = "health_score"
        spec["operator"] = "less_than"
        spec["collection"] = "projects"
        spec["name"] = "Health Score Alert"

    # Detect completion rate alerts
    elif "completion" in desc_lower or "complete" in desc_lower:
        spec["alert_type"] = "completion_rate"
        spec["metric"] = "completion_rate"
        spec["name"] = "Completion Rate Alert"

    # Detect unassigned task alerts
    elif "unassigned" in desc_lower:
        spec["alert_type"] = "unassigned_tasks"
        spec["metric"] = "unassigned_count"
        spec["name"] = "Unassigned Tasks Alert"

    # Detect overdue alerts
    elif "overdue" in desc_lower or "past due" in desc_lower:
        spec["alert_type"] = "overdue_tasks"
        spec["metric"] = "overdue_count"
        spec["name"] = "Overdue Tasks Alert"

    # Extract numeric threshold
    numbers = re.findall(r"\d+(?:\.\d+)?", description)
    if numbers:
        spec["threshold"] = float(numbers[0])

    # Detect comparison direction
    if any(
        kw in desc_lower for kw in ("below", "under", "less than", "drops below", "falls below")
    ):
        spec["operator"] = "less_than"
    elif any(kw in desc_lower for kw in ("above", "over", "more than", "exceeds", "greater than")):
        spec["operator"] = "greater_than"

    return spec
