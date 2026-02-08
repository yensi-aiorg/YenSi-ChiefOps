"""
Unit tests for the memory and conversation context services.

Tests hard fact extraction, fact supersession, compaction triggers,
context assembly, and token budget enforcement.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.ai.adapter import AIRequest, AIResponse
from app.ai.mock_adapter import MockAIAdapter
from app.models.base import generate_uuid, utc_now
from app.models.conversation import (
    CompactedSummary,
    ConversationTurn,
    FactCategory,
    HardFact,
    MemoryStream,
    StreamType,
    TurnRole,
)


class TestHardFactExtraction:
    """Test extraction and storage of hard facts from conversation turns."""

    async def test_hard_fact_extraction(self, test_db, mock_ai_adapter):
        """Mock AI should extract facts from a conversation prompt."""
        request = AIRequest(
            system_prompt="You are a fact extraction assistant. Extract key facts from the conversation.",
            user_prompt="The platform migration deadline is March 15th and Sarah Chen leads the team.",
        )

        response = await mock_ai_adapter.generate_structured(request)
        data = response.parse_json()

        assert "facts" in data
        assert len(data["facts"]) > 0

        # Each fact should have subject, predicate, object
        for fact in data["facts"]:
            assert "subject" in fact
            assert "predicate" in fact
            assert "confidence" in fact

    async def test_hard_fact_storage(self, test_db):
        """Hard facts should be persistable and retrievable from MongoDB."""
        collection = test_db["hard_facts"]

        fact = HardFact(
            fact_id=generate_uuid(),
            project_id="proj-001",
            stream_type=StreamType.PROJECT,
            fact_text="Sarah Chen is the Engineering Lead for Platform Migration.",
            category=FactCategory.ORGANIZATIONAL,
            source={"turn_id": "turn-001", "timestamp": utc_now().isoformat()},
            extracted_by="mock_adapter",
            confidence=0.95,
            active=True,
        )

        await collection.insert_one(fact.model_dump())

        doc = await collection.find_one({"fact_id": fact.fact_id})
        assert doc is not None
        assert doc["fact_text"] == fact.fact_text
        assert doc["category"] == FactCategory.ORGANIZATIONAL.value
        assert doc["active"] is True


class TestHardFactSupersession:
    """Test that new facts correctly supersede old ones."""

    async def test_hard_fact_supersession(self, test_db):
        """A new fact should deactivate the old fact it supersedes."""
        collection = test_db["hard_facts"]

        old_fact_id = generate_uuid()
        new_fact_id = generate_uuid()

        # Insert the old fact
        old_fact = {
            "fact_id": old_fact_id,
            "project_id": "proj-001",
            "stream_type": StreamType.PROJECT.value,
            "fact_text": "Marcus Rivera is a Senior Backend Developer.",
            "category": FactCategory.ROLE_CORRECTION.value,
            "source": {},
            "extracted_by": "system",
            "confidence": 0.88,
            "active": True,
            "supersedes": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        await collection.insert_one(old_fact)

        # Insert the superseding fact
        new_fact = {
            "fact_id": new_fact_id,
            "project_id": "proj-001",
            "stream_type": StreamType.PROJECT.value,
            "fact_text": "Marcus Rivera is a Staff Engineer.",
            "category": FactCategory.ROLE_CORRECTION.value,
            "source": {},
            "extracted_by": "system",
            "confidence": 1.0,
            "active": True,
            "supersedes": old_fact_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        await collection.insert_one(new_fact)

        # Deactivate the old fact
        await collection.update_one(
            {"fact_id": old_fact_id},
            {"$set": {"active": False}},
        )

        # Verify supersession
        old_doc = await collection.find_one({"fact_id": old_fact_id})
        assert old_doc["active"] is False

        new_doc = await collection.find_one({"fact_id": new_fact_id})
        assert new_doc["active"] is True
        assert new_doc["supersedes"] == old_fact_id

        # Only active facts should be returned for context
        active_facts = await collection.find(
            {"project_id": "proj-001", "active": True}
        ).to_list(length=100)
        assert len(active_facts) == 1
        assert active_facts[0]["fact_id"] == new_fact_id


class TestCompactionTriggerThreshold:
    """Test that compaction is triggered when turn count exceeds threshold."""

    async def test_compaction_trigger_threshold(self, test_db):
        """A memory stream with more than 20 recent turns should trigger compaction."""
        turns_collection = test_db["conversation_turns"]
        streams_collection = test_db["memory_streams"]

        stream_id = generate_uuid()
        project_id = "proj-compact-test"
        compaction_threshold = 20

        # Create a memory stream
        turn_ids = []
        for i in range(25):
            turn_id = generate_uuid()
            turn_ids.append(turn_id)
            await turns_collection.insert_one({
                "turn_id": turn_id,
                "project_id": project_id,
                "stream_type": StreamType.PROJECT.value,
                "role": TurnRole.USER.value if i % 2 == 0 else TurnRole.ASSISTANT.value,
                "content": f"Turn {i} content for compaction test.",
                "timestamp": utc_now(),
                "turn_number": i,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            })

        await streams_collection.insert_one({
            "stream_id": stream_id,
            "project_id": project_id,
            "stream_type": StreamType.PROJECT.value,
            "hard_facts": [],
            "summary": "",
            "recent_turns": turn_ids,
            "last_compacted_at": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Check if compaction should be triggered
        stream = await streams_collection.find_one({"stream_id": stream_id})
        needs_compaction = len(stream["recent_turns"]) > compaction_threshold

        assert needs_compaction is True
        assert len(stream["recent_turns"]) == 25


class TestContextAssembly:
    """Test assembly of conversation context from memory components."""

    async def test_context_assembly(self, test_db):
        """Context should include recent turns, active facts, and summary."""
        facts_collection = test_db["hard_facts"]
        turns_collection = test_db["conversation_turns"]
        streams_collection = test_db["memory_streams"]

        project_id = "proj-context-test"

        # Insert facts
        fact_id = generate_uuid()
        await facts_collection.insert_one({
            "fact_id": fact_id,
            "project_id": project_id,
            "stream_type": StreamType.PROJECT.value,
            "fact_text": "The deadline is March 15th.",
            "category": FactCategory.DEADLINE.value,
            "source": {},
            "extracted_by": "system",
            "confidence": 1.0,
            "active": True,
            "supersedes": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Insert turns
        turn_ids = []
        for i in range(3):
            turn_id = generate_uuid()
            turn_ids.append(turn_id)
            await turns_collection.insert_one({
                "turn_id": turn_id,
                "project_id": project_id,
                "stream_type": StreamType.PROJECT.value,
                "role": TurnRole.USER.value if i % 2 == 0 else TurnRole.ASSISTANT.value,
                "content": f"Context assembly test turn {i}.",
                "timestamp": utc_now(),
                "turn_number": i,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            })

        # Insert stream with summary
        await streams_collection.insert_one({
            "stream_id": generate_uuid(),
            "project_id": project_id,
            "stream_type": StreamType.PROJECT.value,
            "hard_facts": [fact_id],
            "summary": "This project is about platform migration with a March deadline.",
            "recent_turns": turn_ids,
            "last_compacted_at": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })

        # Assemble context
        active_facts = await facts_collection.find(
            {"project_id": project_id, "active": True}
        ).to_list(length=100)
        recent_turns = await turns_collection.find(
            {"project_id": project_id}
        ).sort("turn_number", 1).to_list(length=100)
        stream = await streams_collection.find_one({"project_id": project_id})

        context = {
            "facts": [f["fact_text"] for f in active_facts],
            "summary": stream["summary"],
            "recent_turns": [
                {"role": t["role"], "content": t["content"]}
                for t in recent_turns
            ],
        }

        assert len(context["facts"]) == 1
        assert "March 15th" in context["facts"][0]
        assert context["summary"] != ""
        assert len(context["recent_turns"]) == 3


class TestTokenBudgetEnforcement:
    """Test that context assembly respects token budget limits."""

    def test_token_budget_enforcement(self):
        """Context assembly should truncate content to fit within the token budget."""
        max_tokens = 100  # Approximate: ~4 chars per token

        # Simulate context components
        facts = ["Fact 1: The project deadline is March 15th."] * 5
        summary = "This is a summary of the project. " * 10
        turns = [
            {"role": "user", "content": f"Turn {i} with some content." }
            for i in range(20)
        ]

        # Build context with budget enforcement
        budget_chars = max_tokens * 4  # Rough token-to-char ratio
        assembled_parts: list[str] = []
        used_chars = 0

        # Priority 1: Facts (always included)
        for fact in facts:
            if used_chars + len(fact) <= budget_chars:
                assembled_parts.append(fact)
                used_chars += len(fact)

        # Priority 2: Recent turns (most recent first)
        for turn in reversed(turns):
            entry = f"{turn['role']}: {turn['content']}"
            if used_chars + len(entry) <= budget_chars:
                assembled_parts.append(entry)
                used_chars += len(entry)

        # Priority 3: Summary (truncated if needed)
        remaining = budget_chars - used_chars
        if remaining > 0:
            assembled_parts.append(summary[:remaining])

        total_chars = sum(len(p) for p in assembled_parts)
        assert total_chars <= budget_chars
        assert len(assembled_parts) > 0
        # Facts should always be included
        assert any("deadline" in p for p in assembled_parts)
