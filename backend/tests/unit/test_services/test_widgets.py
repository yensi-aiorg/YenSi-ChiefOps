"""
Unit tests for the widget and dashboard data query services.

Tests various query types (count, group_count, time_series, top_n)
and AI-driven widget specification generation.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.ai.adapter import AIRequest
from app.ai.mock_adapter import MockAIAdapter
from app.models.base import generate_uuid, utc_now
from app.models.dashboard import DataQuery, QueryType, WidgetSpec, WidgetType


@pytest.mark.integration
class TestCountQueryExecution:
    """Test simple count queries against MongoDB collections."""

    async def test_count_query_execution(self, test_db):
        """A COUNT query should return the number of matching documents."""
        collection = test_db["people"]

        # Insert test data
        for i in range(5):
            await collection.insert_one({
                "person_id": generate_uuid(),
                "name": f"Person {i}",
                "role": "Developer",
                "activity_level": "active",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            })

        # Execute count query
        query = DataQuery(
            collection="people",
            query_type=QueryType.COUNT,
            match_filters={"activity_level": "active"},
        )

        count = await test_db[query.collection].count_documents(query.match_filters)
        assert count == 5

    async def test_count_query_with_filter(self, test_db):
        """Count query with a filter should only count matching documents."""
        collection = test_db["tasks_count_test"]

        await collection.insert_one({"status": "done", "project": "A"})
        await collection.insert_one({"status": "done", "project": "A"})
        await collection.insert_one({"status": "in_progress", "project": "A"})
        await collection.insert_one({"status": "done", "project": "B"})

        count = await collection.count_documents({"status": "done", "project": "A"})
        assert count == 2


@pytest.mark.integration
class TestGroupCountQuery:
    """Test group-by count aggregation queries."""

    async def test_group_count_query(self, test_db):
        """A GROUP_COUNT query should group documents and count per group."""
        collection = test_db["tasks_group_test"]

        test_data = [
            {"status": "done", "project": "Alpha"},
            {"status": "done", "project": "Alpha"},
            {"status": "in_progress", "project": "Alpha"},
            {"status": "done", "project": "Beta"},
            {"status": "blocked", "project": "Beta"},
        ]
        await collection.insert_many(test_data)

        # Execute aggregation pipeline for group count
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]

        results = await collection.aggregate(pipeline).to_list(length=100)

        # Convert to dict for easier assertion
        result_map = {r["_id"]: r["count"] for r in results}

        assert result_map["done"] == 3
        assert result_map["in_progress"] == 1
        assert result_map["blocked"] == 1

    async def test_group_count_by_project(self, test_db):
        """Group count by project should produce per-project counts."""
        collection = test_db["tasks_group_project"]

        await collection.insert_many([
            {"project": "Alpha", "status": "done"},
            {"project": "Alpha", "status": "done"},
            {"project": "Beta", "status": "done"},
        ])

        pipeline = [
            {"$group": {"_id": "$project", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]

        results = await collection.aggregate(pipeline).to_list(length=100)
        result_map = {r["_id"]: r["count"] for r in results}

        assert result_map["Alpha"] == 2
        assert result_map["Beta"] == 1


@pytest.mark.integration
class TestTimeSeriesQuery:
    """Test time-series aggregation queries."""

    async def test_time_series_query(self, test_db):
        """A TIME_SERIES query should bucket documents by date."""
        collection = test_db["activity_ts_test"]

        # Insert activities across different dates
        dates = [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 3, tzinfo=timezone.utc),
        ]

        for d in dates:
            await collection.insert_one({
                "type": "message",
                "created_at": d,
            })

        # Aggregate by day
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at",
                        }
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        results = await collection.aggregate(pipeline).to_list(length=100)

        assert len(results) == 3
        assert results[0]["_id"] == "2026-01-01"
        assert results[0]["count"] == 2
        assert results[1]["_id"] == "2026-01-02"
        assert results[1]["count"] == 3
        assert results[2]["_id"] == "2026-01-03"
        assert results[2]["count"] == 1


@pytest.mark.integration
class TestTopNQuery:
    """Test Top-N aggregation queries."""

    async def test_top_n_query(self, test_db):
        """A TOP_N query should return the top N documents sorted by a field."""
        collection = test_db["people_topn_test"]

        people = [
            {"name": "Alice", "tasks_completed": 30},
            {"name": "Bob", "tasks_completed": 15},
            {"name": "Charlie", "tasks_completed": 45},
            {"name": "Diana", "tasks_completed": 22},
            {"name": "Eve", "tasks_completed": 8},
        ]
        await collection.insert_many(people)

        # Top 3 by tasks_completed
        pipeline = [
            {"$sort": {"tasks_completed": -1}},
            {"$limit": 3},
            {"$project": {"_id": 0, "name": 1, "tasks_completed": 1}},
        ]

        results = await collection.aggregate(pipeline).to_list(length=3)

        assert len(results) == 3
        assert results[0]["name"] == "Charlie"
        assert results[0]["tasks_completed"] == 45
        assert results[1]["name"] == "Alice"
        assert results[1]["tasks_completed"] == 30
        assert results[2]["name"] == "Diana"
        assert results[2]["tasks_completed"] == 22


class TestWidgetSpecGenerationWithMockAI:
    """Test AI-driven widget specification generation."""

    async def test_widget_spec_generation_with_mock_ai(self, mock_ai_adapter):
        """MockAIAdapter should return a valid widget spec for widget-related prompts."""
        request = AIRequest(
            system_prompt="You are a widget creation assistant. Generate a widget specification.",
            user_prompt="Create a scorecard showing project health status counts.",
            context={
                "available_collections": ["projects", "people", "tasks"],
                "widget_types": ["bar_chart", "kpi_card", "data_table"],
            },
        )

        response = await mock_ai_adapter.generate_structured(request)
        data = response.parse_json()

        assert "widget_spec" in data
        spec = data["widget_spec"]

        assert "title" in spec
        assert spec["title"]  # Non-empty
        assert "widget_type" in spec
        assert "metrics" in spec
        assert isinstance(spec["metrics"], list)
        assert len(spec["metrics"]) > 0

        # Each metric should have a label and query
        for metric in spec["metrics"]:
            assert "label" in metric
            assert "query" in metric

    async def test_widget_spec_has_layout(self, mock_ai_adapter):
        """Widget spec should include layout configuration."""
        request = AIRequest(
            system_prompt="Widget generation: create a dashboard widget specification.",
            user_prompt="Show me task distribution by status.",
        )

        response = await mock_ai_adapter.generate_structured(request)
        data = response.parse_json()

        assert "widget_spec" in data
        spec = data["widget_spec"]
        assert "layout" in spec


class TestDataQueryModel:
    """Test DataQuery model creation and validation."""

    def test_data_query_defaults(self):
        query = DataQuery(collection="people")
        assert query.query_type == QueryType.COUNT
        assert query.match_filters == {}
        assert query.group_by is None
        assert query.sort_order == "desc"
        assert query.limit == 100

    def test_data_query_with_all_fields(self):
        query = DataQuery(
            collection="tasks",
            query_type=QueryType.GROUP_COUNT,
            match_filters={"status": "done"},
            group_by="assignee",
            sort_by="count",
            sort_order="asc",
            limit=10,
            date_field="created_at",
            date_bucket="week",
        )
        assert query.query_type == QueryType.GROUP_COUNT
        assert query.group_by == "assignee"
        assert query.date_bucket == "week"
