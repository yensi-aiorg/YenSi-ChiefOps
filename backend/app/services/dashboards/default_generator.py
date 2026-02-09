"""
Default COO dashboard generator.

Creates a comprehensive "COO Command Center" dashboard with 20 widgets
across 6 sections after data ingestion and analysis completes.

The dashboard uses a well-known ``dashboard_id`` for idempotency.
Calling with ``force=True`` deletes and recreates everything;
calling with ``force=False`` skips if the dashboard already exists.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

DASHBOARD_ID = "default_coo_dashboard"
DASHBOARD_NAME = "COO Command Center"
DASHBOARD_DESC = (
    "Auto-generated executive dashboard with project health, risks, gaps, "
    "team capacity, and forward planning."
)


# ---------------------------------------------------------------------------
# Widget definitions (20 widgets in 6 sections)
# ---------------------------------------------------------------------------

def _widget_defs() -> list[dict[str, Any]]:
    """Return the default dashboard widget definition dicts."""
    return [
        # ==================================================================
        # Section A: Executive Summary (Row 0, 4 KPI cards)
        # ==================================================================
        {
            "title": "Total Projects",
            "widget_type": "metric_card",
            "position": {"x": 0, "y": 0, "w": 3, "h": 2},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$facet": {
                        "total": [{"$count": "count"}],
                        "active": [
                            {"$match": {"status": {"$nin": ["completed", "cancelled"]}}},
                            {"$count": "count"},
                        ],
                    }},
                    {"$project": {
                        "value": {"$ifNull": [{"$arrayElemAt": ["$total.count", 0]}, 0]},
                        "label": "Total Projects",
                        "change": {
                            "$concat": [
                                {"$toString": {"$ifNull": [{"$arrayElemAt": ["$active.count", 0]}, 0]}},
                                " active",
                            ]
                        },
                    }},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Avg Health Score",
            "widget_type": "metric_card",
            "position": {"x": 3, "y": 0, "w": 3, "h": 2},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {"status": {"$nin": ["completed", "cancelled"]}}},
                    {"$addFields": {
                        "_hs": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$health_score", "healthy"]}, "then": 80},
                                    {"case": {"$eq": ["$health_score", "at_risk"]}, "then": 45},
                                    {"case": {"$eq": ["$health_score", "critical"]}, "then": 20},
                                    {"case": {"$isNumber": "$health_score"}, "then": "$health_score"},
                                ],
                                "default": None,
                            }
                        }
                    }},
                    {"$match": {"_hs": {"$ne": None}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$_hs"}, "count": {"$sum": 1}}},
                    {"$project": {
                        "_id": 0,
                        "value": {"$round": ["$avg", 0]},
                        "label": "Avg Health / 100",
                        "change": {"$concat": [{"$toString": "$count"}, " projects scored"]},
                    }},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Open Tasks",
            "widget_type": "metric_card",
            "position": {"x": 6, "y": 0, "w": 3, "h": 2},
            "data_query": {
                "collection": "jira_tasks",
                "pipeline": [
                    {"$facet": {
                        "open": [
                            {"$match": {"status": {"$nin": ["Done", "Closed", "Resolved", "done", "closed", "resolved"]}}},
                            {"$count": "count"},
                        ],
                        "blocked": [
                            {"$match": {"status": {"$regex": "block", "$options": "i"}}},
                            {"$count": "count"},
                        ],
                    }},
                    {"$project": {
                        "value": {"$ifNull": [{"$arrayElemAt": ["$open.count", 0]}, 0]},
                        "label": "Open Tasks",
                        "change": {
                            "$concat": [
                                {"$toString": {"$ifNull": [{"$arrayElemAt": ["$blocked.count", 0]}, 0]}},
                                " blocked",
                            ]
                        },
                    }},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Team Members",
            "widget_type": "metric_card",
            "position": {"x": 9, "y": 0, "w": 3, "h": 2},
            "data_query": {
                "collection": "people",
                "pipeline": [
                    {"$facet": {
                        "total": [{"$count": "count"}],
                        "active": [
                            {"$match": {"activity_level": {"$in": ["very_active", "active", "moderate"]}}},
                            {"$count": "count"},
                        ],
                    }},
                    {"$project": {
                        "value": {"$ifNull": [{"$arrayElemAt": ["$total.count", 0]}, 0]},
                        "label": "Team Members",
                        "change": {
                            "$concat": [
                                {"$toString": {"$ifNull": [{"$arrayElemAt": ["$active.count", 0]}, 0]}},
                                " active",
                            ]
                        },
                    }},
                ],
                "refresh_interval_seconds": 300,
            },
        },

        # ==================================================================
        # Section B: Project Health & Status (Row 2)
        # ==================================================================
        {
            "title": "Status Distribution",
            "widget_type": "pie_chart",
            "position": {"x": 0, "y": 2, "w": 4, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                    {"$project": {"_id": 0, "name": "$_id", "value": "$count"}},
                    {"$sort": {"value": -1}},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Health by Project",
            "widget_type": "bar_chart",
            "position": {"x": 4, "y": 2, "w": 8, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {"status": {"$nin": ["completed", "cancelled"]}}},
                    {"$addFields": {
                        "_hs": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$health_score", "healthy"]}, "then": 80},
                                    {"case": {"$eq": ["$health_score", "at_risk"]}, "then": 45},
                                    {"case": {"$eq": ["$health_score", "critical"]}, "then": 20},
                                    {"case": {"$isNumber": "$health_score"}, "then": "$health_score"},
                                ],
                                "default": 0,
                            }
                        }
                    }},
                    {"$project": {"_id": 0, "name": "$name", "health": "$_hs"}},
                    {"$sort": {"health": 1}},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Project Overview",
            "widget_type": "table",
            "position": {"x": 0, "y": 6, "w": 12, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$addFields": {
                        "_hs": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$health_score", "healthy"]}, "then": 80},
                                    {"case": {"$eq": ["$health_score", "at_risk"]}, "then": 45},
                                    {"case": {"$eq": ["$health_score", "critical"]}, "then": 20},
                                    {"case": {"$isNumber": "$health_score"}, "then": "$health_score"},
                                ],
                                "default": None,
                            }
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Status": "$status",
                        "Health": "$_hs",
                        "Completion %": {"$ifNull": ["$completion_percentage", 0]},
                        "Open Tasks": {"$ifNull": ["$open_tasks", 0]},
                        "Blocked": {"$ifNull": [
                            "$task_summary.blocked",
                            {"$size": {"$ifNull": ["$blocked_tasks", []]}},
                        ]},
                        "Team Size": {"$ifNull": ["$team_size", 0]},
                        "Key Risks": {"$size": {"$ifNull": ["$key_risks", []]}},
                    }},
                    {"$sort": {"Health": 1}},
                ],
                "refresh_interval_seconds": 300,
            },
        },

        # ==================================================================
        # Section C: Execution & Delivery (Row 10)
        # ==================================================================
        {
            "title": "Task Pipeline by Project",
            "widget_type": "bar_chart",
            "position": {"x": 0, "y": 10, "w": 6, "h": 4},
            "data_query": {
                "collection": "jira_tasks",
                "pipeline": [
                    {"$addFields": {
                        "_bucket": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$regexMatch": {"input": "$status", "regex": "block", "options": "i"}}, "then": "Blocked"},
                                    {"case": {"$regexMatch": {"input": "$status", "regex": "progress|review", "options": "i"}}, "then": "In Progress"},
                                    {"case": {"$regexMatch": {"input": "$status", "regex": "done|closed|resolved|complete", "options": "i"}}, "then": "Completed"},
                                ],
                                "default": "To Do",
                            }
                        }
                    }},
                    {"$group": {
                        "_id": {"project": {"$ifNull": ["$project_name", "Unassigned"]}, "status": "$_bucket"},
                        "count": {"$sum": 1},
                    }},
                    {"$project": {"_id": 0, "project": "$_id.project", "status": "$_id.status", "count": 1}},
                    {"$sort": {"project": 1}},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Blocked Tasks",
            "widget_type": "table",
            "position": {"x": 6, "y": 10, "w": 6, "h": 4},
            "data_query": {
                "collection": "jira_tasks",
                "pipeline": [
                    {"$match": {"status": {"$regex": "block", "$options": "i"}}},
                    {"$project": {
                        "_id": 0,
                        "Key": "$key",
                        "Summary": "$summary",
                        "Assignee": {"$ifNull": ["$assignee", "Unassigned"]},
                        "Priority": {"$ifNull": ["$priority", "None"]},
                        "Project": {"$ifNull": ["$project_name", "—"]},
                    }},
                    {"$limit": 20},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Priority Distribution",
            "widget_type": "pie_chart",
            "position": {"x": 0, "y": 14, "w": 4, "h": 4},
            "data_query": {
                "collection": "jira_tasks",
                "pipeline": [
                    {"$group": {"_id": {"$ifNull": ["$priority", "None"]}, "count": {"$sum": 1}}},
                    {"$project": {"_id": 0, "name": "$_id", "value": "$count"}},
                    {"$sort": {"value": -1}},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Upcoming Deadlines",
            "widget_type": "table",
            "position": {"x": 4, "y": 14, "w": 8, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {
                        "deadline": {"$ne": None},
                        "status": {"$nin": ["completed", "cancelled"]},
                    }},
                    {"$addFields": {
                        "_deadline": {
                            "$cond": {
                                "if": {"$isNumber": "$deadline"},
                                "then": {"$toDate": "$deadline"},
                                "else": {
                                    "$cond": {
                                        "if": {"$gt": [{"$type": "$deadline"}, "missing"]},
                                        "then": "$deadline",
                                        "else": None,
                                    }
                                },
                            }
                        }
                    }},
                    {"$match": {"_deadline": {"$ne": None}}},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Deadline": {"$dateToString": {"format": "%Y-%m-%d", "date": "$_deadline", "onNull": "—"}},
                        "Status": "$status",
                        "Health": "$health_score",
                    }},
                    {"$sort": {"Deadline": 1}},
                    {"$limit": 10},
                ],
                "refresh_interval_seconds": 300,
            },
        },

        # ==================================================================
        # Section D: Team & Capacity (Row 18)
        # ==================================================================
        {
            "title": "Task Load by Person",
            "widget_type": "bar_chart",
            "position": {"x": 0, "y": 18, "w": 6, "h": 4},
            "data_query": {
                "collection": "jira_tasks",
                "pipeline": [
                    {"$match": {"assignee": {"$ne": None}}},
                    {"$addFields": {
                        "_done": {
                            "$cond": {
                                "if": {"$regexMatch": {"input": "$status", "regex": "done|closed|resolved|complete", "options": "i"}},
                                "then": 1,
                                "else": 0,
                            }
                        }
                    }},
                    {"$group": {
                        "_id": "$assignee",
                        "assigned": {"$sum": 1},
                        "completed": {"$sum": "$_done"},
                    }},
                    {"$project": {"_id": 0, "name": "$_id", "assigned": 1, "completed": 1}},
                    {"$sort": {"assigned": -1}},
                    {"$limit": 15},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Activity Levels",
            "widget_type": "pie_chart",
            "position": {"x": 6, "y": 18, "w": 3, "h": 4},
            "data_query": {
                "collection": "people",
                "pipeline": [
                    {"$group": {"_id": {"$ifNull": ["$activity_level", "unknown"]}, "count": {"$sum": 1}}},
                    {"$project": {"_id": 0, "name": "$_id", "value": "$count"}},
                    {"$sort": {"value": -1}},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Top Contributors",
            "widget_type": "table",
            "position": {"x": 9, "y": 18, "w": 3, "h": 4},
            "data_query": {
                "collection": "people",
                "pipeline": [
                    {"$project": {
                        "_id": 0,
                        "Name": "$name",
                        "Completed": {"$ifNull": ["$tasks_completed", 0]},
                        "Activity": {"$ifNull": ["$activity_level", "unknown"]},
                    }},
                    {"$sort": {"Completed": -1}},
                    {"$limit": 5},
                ],
                "refresh_interval_seconds": 300,
            },
        },

        # ==================================================================
        # Section E: Risk & Gap Analysis (Row 22)
        # ==================================================================
        {
            "title": "Key Risks",
            "widget_type": "table",
            "position": {"x": 0, "y": 22, "w": 6, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {"key_risks": {"$exists": True, "$ne": []}}},
                    {"$unwind": "$key_risks"},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Risk": "$key_risks",
                        "Health": "$health_score",
                    }},
                    {"$limit": 20},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Missing Tasks (AI-Detected)",
            "widget_type": "table",
            "position": {"x": 6, "y": 22, "w": 6, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {"gap_analysis.missing_tasks": {"$exists": True, "$ne": []}}},
                    {"$unwind": "$gap_analysis.missing_tasks"},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Missing Task": "$gap_analysis.missing_tasks",
                    }},
                    {"$limit": 20},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Technical Concerns",
            "widget_type": "table",
            "position": {"x": 0, "y": 26, "w": 6, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {
                        "$or": [
                            {"technical_feasibility.concerns": {"$exists": True, "$ne": []}},
                            {"technical_feasibility.architect_questions": {"$exists": True, "$ne": []}},
                        ]
                    }},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Concerns": {"$ifNull": ["$technical_feasibility.concerns", []]},
                        "Questions": {"$ifNull": ["$technical_feasibility.architect_questions", []]},
                    }},
                    {"$limit": 10},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Active Alerts",
            "widget_type": "table",
            "position": {"x": 6, "y": 26, "w": 6, "h": 4},
            "data_query": {
                "collection": "alerts_triggered",
                "pipeline": [
                    {"$match": {"acknowledged": {"$ne": True}}},
                    {"$project": {
                        "_id": 0,
                        "Alert": "$message",
                        "Severity": "$severity",
                        "Triggered": {"$dateToString": {
                            "format": "%Y-%m-%d %H:%M",
                            "date": {"$ifNull": [
                                {"$toDate": "$triggered_at"},
                                {"$toDate": "$created_at"},
                            ]},
                            "onNull": "—",
                        }},
                    }},
                    {"$sort": {"Triggered": -1}},
                    {"$limit": 10},
                ],
                "refresh_interval_seconds": 300,
            },
        },

        # ==================================================================
        # Section F: Forward Planning (Row 30)
        # ==================================================================
        {
            "title": "Upcoming Milestones",
            "widget_type": "table",
            "position": {"x": 0, "y": 30, "w": 6, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {"milestones": {"$exists": True, "$ne": []}}},
                    {"$unwind": "$milestones"},
                    {"$match": {"milestones.status": {"$in": ["pending", "in_progress", "not_started"]}}},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Milestone": "$milestones.name",
                        "Status": "$milestones.status",
                        "Due": {"$ifNull": ["$milestones.due_date", "—"]},
                    }},
                    {"$sort": {"Due": 1}},
                    {"$limit": 15},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        {
            "title": "Backward Plan (Critical Path)",
            "widget_type": "table",
            "position": {"x": 6, "y": 30, "w": 6, "h": 4},
            "data_query": {
                "collection": "projects",
                "pipeline": [
                    {"$match": {"gap_analysis.backward_plan": {"$exists": True, "$ne": []}}},
                    {"$unwind": "$gap_analysis.backward_plan"},
                    {"$project": {
                        "_id": 0,
                        "Project": "$name",
                        "Step": "$gap_analysis.backward_plan.step",
                        "Target Date": {"$ifNull": ["$gap_analysis.backward_plan.target_date", "—"]},
                        "Owner": {"$ifNull": ["$gap_analysis.backward_plan.owner", "TBD"]},
                    }},
                    {"$limit": 20},
                ],
                "refresh_interval_seconds": 300,
            },
        },
        # ==================================================================
        # Section G: Narrative Intelligence (Row 34)
        # ==================================================================
        {
            "title": "Executive Snapshot",
            "widget_type": "text",
            "position": {"x": 0, "y": 34, "w": 12, "h": 3},
            "data_query": {
                "collection": "project_snapshots",
                "pipeline": [
                    {"$sort": {"updated_at": -1}},
                    {"$limit": 1},
                    {
                        "$project": {
                            "_id": 0,
                            "Executive Summary": {
                                "$ifNull": ["$executive_summary", "No snapshot available yet."]
                            },
                        }
                    },
                ],
                "refresh_interval_seconds": 120,
            },
        },
        {
            "title": "Critical Narrative Signals",
            "widget_type": "table",
            "position": {"x": 0, "y": 37, "w": 8, "h": 4},
            "data_query": {
                "collection": "operational_insights",
                "pipeline": [
                    {"$match": {"severity": {"$in": ["critical", "high"]}, "active": True}},
                    {"$sort": {"created_at": -1}},
                    {
                        "$project": {
                            "_id": 0,
                            "Type": "$insight_type",
                            "Severity": "$severity",
                            "Summary": "$summary",
                            "Source": "$source_type",
                        }
                    },
                    {"$limit": 20},
                ],
                "refresh_interval_seconds": 120,
            },
        },
        {
            "title": "Signal Severity Mix",
            "widget_type": "pie_chart",
            "position": {"x": 8, "y": 37, "w": 4, "h": 4},
            "data_query": {
                "collection": "operational_insights",
                "pipeline": [
                    {"$match": {"active": True}},
                    {"$group": {"_id": {"$ifNull": ["$severity", "unknown"]}, "count": {"$sum": 1}}},
                    {"$project": {"_id": 0, "name": "$_id", "value": "$count"}},
                    {"$sort": {"value": -1}},
                ],
                "refresh_interval_seconds": 120,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

async def generate_default_dashboard(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Create or recreate the default COO dashboard.

    Args:
        db: Motor database handle.
        force: If True, delete and recreate even if it already exists.

    Returns:
        Dict with ``dashboard_id`` and ``widget_ids``.
    """
    dashboards_col = db["dashboards"]
    widgets_col = db["widgets"]

    existing = await dashboards_col.find_one({"dashboard_id": DASHBOARD_ID})

    if existing and not force:
        logger.info("Default dashboard already exists, skipping generation.")
        return {
            "dashboard_id": DASHBOARD_ID,
            "widget_ids": existing.get("widget_ids", []),
            "created": False,
        }

    # Delete old dashboard + widgets if forcing regeneration
    if existing:
        old_widget_ids = existing.get("widget_ids", [])
        if old_widget_ids:
            await widgets_col.delete_many({"widget_id": {"$in": old_widget_ids}})
        await dashboards_col.delete_one({"dashboard_id": DASHBOARD_ID})
        logger.info("Deleted existing default dashboard and %d widgets.", len(old_widget_ids))

    now = utc_now()
    widget_ids: list[str] = []
    layout: list[dict[str, Any]] = []
    widget_docs: list[dict[str, Any]] = []

    for defn in _widget_defs():
        widget_id = generate_uuid()
        widget_ids.append(widget_id)

        pos = defn["position"]
        layout.append({
            "widget_id": widget_id,
            "x": pos["x"],
            "y": pos["y"],
            "w": pos["w"],
            "h": pos["h"],
        })

        widget_docs.append({
            "widget_id": widget_id,
            "title": defn["title"],
            "description": "",
            "widget_type": defn["widget_type"],
            "data_query": defn["data_query"],
            "config": {},
            "dashboard_id": DASHBOARD_ID,
            "position": pos,
            "created_at": now,
            "updated_at": now,
        })

    # Bulk insert widgets
    if widget_docs:
        await widgets_col.insert_many(widget_docs)

    # Create dashboard document
    dashboard_doc = {
        "dashboard_id": DASHBOARD_ID,
        "name": DASHBOARD_NAME,
        "description": DASHBOARD_DESC,
        "project_id": None,
        "layout": layout,
        "widget_ids": widget_ids,
        "created_at": now,
        "updated_at": now,
    }
    await dashboards_col.insert_one(dashboard_doc)

    logger.info(
        "Generated default COO dashboard with %d widgets.", len(widget_ids)
    )
    return {
        "dashboard_id": DASHBOARD_ID,
        "widget_ids": widget_ids,
        "created": True,
    }
