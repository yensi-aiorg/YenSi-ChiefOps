from __future__ import annotations

import pytest

from app.services.insights.semantic import (
    extract_conversation_signal,
    extract_semantic_insights,
    generate_project_snapshot,
)


@pytest.mark.integration
class TestSemanticInsights:
    async def test_extract_semantic_insights_heuristic(self, test_db):
        result = await extract_semantic_insights(
            project_id="proj-sem-1",
            source_type="ui_note",
            source_ref="note-1",
            content=(
                "Decision: we changed direction to prioritize onboarding. "
                "Major red flag: migration is not going well and deadline may slip."
            ),
            db=test_db,
            ai_adapter=None,
        )
        assert result["created"] >= 1

        count = await test_db.operational_insights.count_documents({"project_id": "proj-sem-1"})
        assert count >= 1

    async def test_extract_conversation_signal_creates_critical_flag(self, test_db):
        result = await extract_conversation_signal(
            content="This project is not going well and this is a major red flag.",
            project_id="proj-sem-2",
            db=test_db,
        )
        assert result["created"] >= 1

        critical = await test_db.operational_insights.count_documents(
            {"project_id": "proj-sem-2", "severity": "critical"}
        )
        assert critical >= 1

    async def test_generate_project_snapshot(self, test_db):
        await test_db.operational_insights.insert_one(
            {
                "insight_id": "i1",
                "project_id": "proj-sem-3",
                "source_type": "slack",
                "source_ref": "chan-a",
                "insight_type": "risk",
                "summary": "Integration testing is blocked by unstable staging.",
                "severity": "high",
                "confidence": 0.91,
                "tags": [],
                "entities": [],
                "active": True,
            }
        )
        snapshot = await generate_project_snapshot(project_id="proj-sem-3", db=test_db, force=True)
        assert snapshot["project_id"] == "proj-sem-3"
        assert snapshot["executive_summary"]
        assert snapshot["summary"]
        assert snapshot["detailed_understanding"]
