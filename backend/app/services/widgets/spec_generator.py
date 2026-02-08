"""
Natural language to WidgetSpec generator.

Converts natural language descriptions from the COO into structured
widget specifications using AI. The generated spec includes chart type,
data query, layout, and styling parameters.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Available chart types
CHART_TYPES = [
    "metric",  # Single number KPI
    "bar",  # Bar chart
    "line",  # Line chart / time series
    "pie",  # Pie / donut chart
    "stacked_bar",  # Stacked bar chart
    "table",  # Data table
    "heatmap",  # Heatmap grid
    "gauge",  # Gauge / progress indicator
    "list",  # Ranked list
]

# Available data collections for widgets
WIDGET_COLLECTIONS = [
    "jira_tasks",
    "slack_messages",
    "people",
    "projects",
    "health_scores",
]


async def generate_widget_spec(
    description: str,
    dashboard_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Generate a widget specification from a natural language description.

    Uses AI to interpret the COO's request and create a structured
    widget spec that the frontend can render.

    Args:
        description: Natural language description of the desired widget.
        dashboard_id: ID of the dashboard to add the widget to.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        The created widget spec document.
    """
    # Get available data context
    data_context = await _get_data_context(db)

    if ai_adapter is not None:
        spec = await _ai_generate_spec(description, data_context, ai_adapter)
    else:
        spec = _heuristic_generate_spec(description)

    # Enrich with metadata
    widget_doc: dict[str, Any] = {
        "widget_id": generate_uuid(),
        "dashboard_id": dashboard_id,
        "title": spec.get("title", "Widget"),
        "description": description,
        "chart_type": spec.get("chart_type", "metric"),
        "data_query": spec.get("data_query", {}),
        "layout": spec.get("layout", {"w": 4, "h": 3, "x": 0, "y": 0}),
        "style": spec.get("style", {}),
        "refresh_interval": spec.get("refresh_interval", 300),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    # Store in widgets collection
    await db.widgets.insert_one(widget_doc)

    # Add widget reference to dashboard
    await db.dashboards.update_one(
        {"_id": dashboard_id}
        if not isinstance(dashboard_id, str)
        else {"dashboard_id": dashboard_id},
        {"$push": {"widgets": widget_doc["widget_id"]}},
    )

    logger.info("Created widget '%s' (type: %s)", widget_doc["title"], widget_doc["chart_type"])
    return widget_doc


async def _get_data_context(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Get context about available data for widget generation."""
    context: dict[str, Any] = {}

    # Get sample field names from each collection
    for coll_name in WIDGET_COLLECTIONS:
        sample = await db[coll_name].find_one()
        if sample:
            fields = [k for k in sample if k != "_id"]
            context[coll_name] = {
                "fields": fields[:20],
                "count": await db[coll_name].estimated_document_count(),
            }

    # Get distinct statuses from jira_tasks
    statuses = await db.jira_tasks.distinct("status")
    context["jira_statuses"] = statuses

    # Get distinct activity levels from people
    levels = await db.people.distinct("activity_level")
    context["activity_levels"] = levels

    return context


async def _ai_generate_spec(
    description: str,
    data_context: dict[str, Any],
    ai_adapter: Any,
) -> dict[str, Any]:
    """Use AI to generate a widget specification."""
    context_str = ""
    for coll, info in data_context.items():
        if isinstance(info, dict) and "fields" in info:
            context_str += f"\n{coll} ({info.get('count', 0)} docs): {', '.join(info['fields'])}"

    prompt = (
        "Generate a widget specification for a project management dashboard.\n\n"
        f"Request: {description}\n\n"
        f"Available chart types: {', '.join(CHART_TYPES)}\n\n"
        f"Available data:\n{context_str}\n\n"
        f"Available statuses: {data_context.get('jira_statuses', [])}\n"
        f"Activity levels: {data_context.get('activity_levels', [])}\n\n"
        "Generate a JSON specification with:\n"
        '  "title": short descriptive title\n'
        '  "chart_type": one of the available chart types\n'
        '  "data_query": {\n'
        '    "collection": data collection to query,\n'
        '    "query_type": "count" | "group_count" | "time_series" | "top_n" | "aggregate",\n'
        '    "filters": optional filter conditions,\n'
        '    "group_by": field to group by (if applicable),\n'
        '    "metric": field to aggregate (if applicable),\n'
        '    "operation": "sum" | "avg" | "count" | "min" | "max",\n'
        '    "time_field": date field for time series,\n'
        '    "time_interval": "day" | "week" | "month",\n'
        '    "limit": max results\n'
        "  }\n"
        '  "layout": {"w": width 1-12, "h": height 1-6, "x": 0, "y": 0}\n'
        '  "style": {"color_scheme": "default"}\n'
        '  "refresh_interval": seconds between refreshes (60-3600)'
    )

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "chart_type": {"type": "string", "enum": CHART_TYPES},
            "data_query": {
                "type": "object",
                "properties": {
                    "collection": {"type": "string"},
                    "query_type": {"type": "string"},
                    "filters": {"type": "object"},
                    "group_by": {"type": "string"},
                    "metric": {"type": "string"},
                    "operation": {"type": "string"},
                    "time_field": {"type": "string"},
                    "time_interval": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["collection", "query_type"],
            },
            "layout": {
                "type": "object",
                "properties": {
                    "w": {"type": "integer"},
                    "h": {"type": "integer"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                },
            },
            "style": {"type": "object"},
            "refresh_interval": {"type": "integer"},
        },
        "required": ["title", "chart_type", "data_query"],
    }

    try:
        return await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a dashboard widget designer. Create practical, useful widget specs for project management.",
        )
    except Exception as exc:
        logger.warning("AI widget spec generation failed: %s", exc)
        return _heuristic_generate_spec(description)


def _heuristic_generate_spec(description: str) -> dict[str, Any]:
    """Generate a basic widget spec from heuristic analysis."""
    desc_lower = description.lower()

    # Default spec
    spec: dict[str, Any] = {
        "title": "Widget",
        "chart_type": "metric",
        "data_query": {
            "collection": "jira_tasks",
            "query_type": "count",
        },
        "layout": {"w": 4, "h": 3, "x": 0, "y": 0},
        "style": {"color_scheme": "default"},
        "refresh_interval": 300,
    }

    # Detect chart type from description
    if any(
        kw in desc_lower
        for kw in ("over time", "trend", "timeline", "per day", "per week", "per month")
    ):
        spec["chart_type"] = "line"
        spec["data_query"]["query_type"] = "time_series"
        spec["data_query"]["time_field"] = "created_at"
        spec["data_query"]["time_interval"] = "day"
        spec["layout"] = {"w": 8, "h": 4, "x": 0, "y": 0}

    elif any(kw in desc_lower for kw in ("by status", "breakdown", "distribution", "by type")):
        spec["chart_type"] = "bar"
        spec["data_query"]["query_type"] = "group_count"
        if "status" in desc_lower:
            spec["data_query"]["group_by"] = "status"
        elif "type" in desc_lower:
            spec["data_query"]["group_by"] = "issue_type"
        elif "priority" in desc_lower:
            spec["data_query"]["group_by"] = "priority"
        else:
            spec["data_query"]["group_by"] = "status"
        spec["layout"] = {"w": 6, "h": 4, "x": 0, "y": 0}

    elif any(kw in desc_lower for kw in ("top", "most", "highest", "leaderboard", "ranking")):
        spec["chart_type"] = "list"
        spec["data_query"]["query_type"] = "top_n"
        spec["data_query"]["group_by"] = "assignee"
        spec["data_query"]["limit"] = 10
        spec["layout"] = {"w": 4, "h": 4, "x": 0, "y": 0}

    elif any(kw in desc_lower for kw in ("pie", "donut", "proportion", "share")):
        spec["chart_type"] = "pie"
        spec["data_query"]["query_type"] = "group_count"
        spec["data_query"]["group_by"] = "status"

    elif any(kw in desc_lower for kw in ("gauge", "progress", "completion")):
        spec["chart_type"] = "gauge"
        spec["data_query"]["query_type"] = "count"

    # Detect collection from description
    if any(kw in desc_lower for kw in ("message", "slack", "conversation", "channel")):
        spec["data_query"]["collection"] = "slack_messages"
    elif any(kw in desc_lower for kw in ("people", "team", "member", "person")):
        spec["data_query"]["collection"] = "people"
    elif any(kw in desc_lower for kw in ("project", "health")):
        spec["data_query"]["collection"] = "projects"

    # Generate title from description
    spec["title"] = description[:60].strip()
    if len(description) > 60:
        spec["title"] = spec["title"].rsplit(" ", 1)[0] + "..."

    return spec
