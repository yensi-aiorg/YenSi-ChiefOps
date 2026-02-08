"""
Data query engine for widget data retrieval.

Translates ``DataQuery`` JSON specifications into MongoDB aggregation
pipelines and executes them. Supports multiple query types: count,
group_count, time_series, top_n, and aggregate.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Valid query types
QUERY_TYPES = {"count", "group_count", "time_series", "top_n", "aggregate"}

# Valid collections that can be queried
QUERYABLE_COLLECTIONS = {
    "jira_tasks",
    "slack_messages",
    "people",
    "projects",
    "drive_files",
    "slack_channels",
    "alerts",
    "alerts_triggered",
    "health_scores",
}


async def execute_query(
    data_query: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Execute a data query and return results.

    The ``data_query`` dict must contain:
    - ``collection``: MongoDB collection name
    - ``query_type``: One of count, group_count, time_series, top_n, aggregate
    - ``filters``: Optional filter conditions
    - ``group_by``: Field to group by (for group_count, time_series)
    - ``metric``: Field to aggregate (for aggregate)
    - ``operation``: Aggregation operation (sum, avg, min, max)
    - ``limit``: Result limit (for top_n)
    - ``time_field``: Field for time bucketing (for time_series)
    - ``time_interval``: Bucket interval (day, week, month)

    Args:
        data_query: Query specification dict.
        db: Motor database handle.

    Returns:
        Dict with ``data`` key containing query results and ``metadata``.
    """
    collection_name = data_query.get("collection", "")
    query_type = data_query.get("query_type", "")
    filters = data_query.get("filters", {})

    if collection_name not in QUERYABLE_COLLECTIONS:
        return {
            "data": [],
            "metadata": {"error": f"Invalid collection: {collection_name}"},
        }

    if query_type not in QUERY_TYPES:
        return {
            "data": [],
            "metadata": {"error": f"Invalid query type: {query_type}"},
        }

    # Build filter pipeline stage
    match_stage = _build_match_stage(filters)
    collection = db[collection_name]

    try:
        if query_type == "count":
            return await _execute_count(collection, match_stage)
        if query_type == "group_count":
            return await _execute_group_count(collection, match_stage, data_query)
        if query_type == "time_series":
            return await _execute_time_series(collection, match_stage, data_query)
        if query_type == "top_n":
            return await _execute_top_n(collection, match_stage, data_query)
        if query_type == "aggregate":
            return await _execute_aggregate(collection, match_stage, data_query)
        return {"data": [], "metadata": {"error": f"Unhandled query type: {query_type}"}}
    except Exception as exc:
        logger.exception("Query execution failed")
        return {"data": [], "metadata": {"error": str(exc)}}


def _build_match_stage(filters: dict[str, Any]) -> dict[str, Any]:
    """Build a MongoDB $match stage from filter conditions.

    Supports:
    - Simple equality: {"field": "value"}
    - Comparison operators: {"field": {"$gt": 5}}
    - Array membership: {"field": {"$in": [...]}}
    - Date ranges: {"field": {"$gte": "2024-01-01", "$lte": "2024-12-31"}}
    """
    if not filters:
        return {}

    match: dict[str, Any] = {}
    for key, value in filters.items():
        if isinstance(value, dict):
            # Handle operator expressions
            processed: dict[str, Any] = {}
            for op, op_val in value.items():
                if op in ("$gt", "$gte", "$lt", "$lte", "$ne", "$eq"):
                    # Try to parse date strings
                    if isinstance(op_val, str):
                        parsed_date = _try_parse_date(op_val)
                        processed[op] = parsed_date if parsed_date else op_val
                    else:
                        processed[op] = op_val
                elif op in ("$in", "$nin"):
                    processed[op] = op_val if isinstance(op_val, list) else [op_val]
                elif op == "$regex":
                    processed[op] = op_val
                    processed["$options"] = value.get("$options", "i")
                else:
                    processed[op] = op_val
            match[key] = processed
        else:
            match[key] = value

    return match


def _try_parse_date(value: str) -> datetime | None:
    """Try to parse a string as a date."""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


async def _execute_count(
    collection: Any,
    match_stage: dict[str, Any],
) -> dict[str, Any]:
    """Execute a count query."""
    if match_stage:
        count = await collection.count_documents(match_stage)
    else:
        count = await collection.estimated_document_count()

    return {
        "data": {"count": count},
        "metadata": {"query_type": "count"},
    }


async def _execute_group_count(
    collection: Any,
    match_stage: dict[str, Any],
    query: dict[str, Any],
) -> dict[str, Any]:
    """Execute a group_count query (e.g., tasks by status)."""
    group_by = query.get("group_by", "status")

    pipeline: list[dict[str, Any]] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend(
        [
            {
                "$group": {
                    "_id": f"${group_by}",
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
    )

    limit = query.get("limit")
    if limit and isinstance(limit, int):
        pipeline.append({"$limit": limit})

    results: list[dict[str, Any]] = []
    async for doc in collection.aggregate(pipeline):
        results.append(
            {
                "label": str(doc.get("_id", "Unknown")),
                "value": doc.get("count", 0),
            }
        )

    return {
        "data": results,
        "metadata": {"query_type": "group_count", "group_by": group_by},
    }


async def _execute_time_series(
    collection: Any,
    match_stage: dict[str, Any],
    query: dict[str, Any],
) -> dict[str, Any]:
    """Execute a time_series query (e.g., messages per day)."""
    time_field = query.get("time_field", "created_at")
    interval = query.get("time_interval", "day")
    metric = query.get("metric")
    operation = query.get("operation", "count")

    # Build date truncation expression
    date_trunc: dict[str, Any]
    if interval == "day":
        date_trunc = {"$dateToString": {"format": "%Y-%m-%d", "date": f"${time_field}"}}
    elif interval == "week":
        date_trunc = {"$dateToString": {"format": "%Y-W%V", "date": f"${time_field}"}}
    elif interval == "month":
        date_trunc = {"$dateToString": {"format": "%Y-%m", "date": f"${time_field}"}}
    else:
        date_trunc = {"$dateToString": {"format": "%Y-%m-%d", "date": f"${time_field}"}}

    pipeline: list[dict[str, Any]] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    # Filter out documents where the time field is null
    pipeline.append({"$match": {time_field: {"$ne": None}}})

    # Group by time bucket
    group_stage: dict[str, Any] = {
        "_id": date_trunc,
    }

    if metric and operation != "count":
        op_map = {"sum": "$sum", "avg": "$avg", "min": "$min", "max": "$max"}
        mongo_op = op_map.get(operation, "$sum")
        group_stage["value"] = {mongo_op: f"${metric}"}
    else:
        group_stage["value"] = {"$sum": 1}

    pipeline.extend(
        [
            {"$group": group_stage},
            {"$sort": {"_id": 1}},
        ]
    )

    results: list[dict[str, Any]] = []
    async for doc in collection.aggregate(pipeline):
        results.append(
            {
                "date": doc.get("_id", ""),
                "value": doc.get("value", 0),
            }
        )

    return {
        "data": results,
        "metadata": {
            "query_type": "time_series",
            "time_field": time_field,
            "interval": interval,
        },
    }


async def _execute_top_n(
    collection: Any,
    match_stage: dict[str, Any],
    query: dict[str, Any],
) -> dict[str, Any]:
    """Execute a top_n query (e.g., top 10 contributors)."""
    group_by = query.get("group_by", "assignee")
    metric = query.get("metric")
    operation = query.get("operation", "count")
    limit = query.get("limit", 10)

    pipeline: list[dict[str, Any]] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    group_stage: dict[str, Any] = {"_id": f"${group_by}"}

    if metric and operation != "count":
        op_map = {"sum": "$sum", "avg": "$avg", "min": "$min", "max": "$max"}
        mongo_op = op_map.get(operation, "$sum")
        group_stage["value"] = {mongo_op: f"${metric}"}
    else:
        group_stage["value"] = {"$sum": 1}

    pipeline.extend(
        [
            {"$group": group_stage},
            {"$sort": {"value": -1}},
            {"$limit": limit},
        ]
    )

    results: list[dict[str, Any]] = []
    async for doc in collection.aggregate(pipeline):
        label = doc.get("_id", "Unknown")
        if label is None:
            label = "Unassigned"
        results.append(
            {
                "label": str(label),
                "value": doc.get("value", 0),
            }
        )

    return {
        "data": results,
        "metadata": {"query_type": "top_n", "group_by": group_by, "limit": limit},
    }


async def _execute_aggregate(
    collection: Any,
    match_stage: dict[str, Any],
    query: dict[str, Any],
) -> dict[str, Any]:
    """Execute a generic aggregation query."""
    metric = query.get("metric", "")
    operation = query.get("operation", "sum")

    if not metric:
        return {"data": {}, "metadata": {"error": "No metric field specified"}}

    pipeline: list[dict[str, Any]] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    op_map = {"sum": "$sum", "avg": "$avg", "min": "$min", "max": "$max"}
    mongo_op = op_map.get(operation, "$sum")

    pipeline.append(
        {
            "$group": {
                "_id": None,
                "result": {mongo_op: f"${metric}"},
                "count": {"$sum": 1},
            },
        }
    )

    result: dict[str, Any] = {}
    async for doc in collection.aggregate(pipeline):
        result = {
            "value": doc.get("result", 0),
            "count": doc.get("count", 0),
        }

    return {
        "data": result,
        "metadata": {
            "query_type": "aggregate",
            "metric": metric,
            "operation": operation,
        },
    }
