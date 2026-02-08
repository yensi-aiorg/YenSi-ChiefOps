"""
Hard fact extraction and management.

Hard facts are durable pieces of knowledge extracted from conversations
or corrections. They persist across sessions and are always included
in the context window. Facts can be superseded when new information
contradicts them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Categories of hard facts
FACT_CATEGORIES = [
    "team_structure",
    "project_decision",
    "technical_constraint",
    "deadline",
    "priority",
    "process",
    "people_correction",
    "preference",
    "risk",
    "dependency",
    "other",
]


async def extract_facts(
    turn_content: str,
    ai_adapter: Any,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    """Extract hard facts from a conversation turn using AI.

    Analyses the turn content to identify durable facts that should
    persist: decisions, constraints, deadlines, corrections, etc.

    Args:
        turn_content: The conversation turn text (both user and assistant).
        ai_adapter: AI adapter instance with ``generate_structured`` method.
        db: Motor database handle.
        project_id: Optional project context.

    Returns:
        List of extracted fact documents.
    """
    if ai_adapter is None:
        return []

    prompt = (
        "Analyze the following conversation turn and extract any hard facts "
        "that should be remembered permanently. Hard facts include:\n"
        "- Team structure decisions (who does what)\n"
        "- Project decisions (chosen approach, architecture)\n"
        "- Technical constraints (must use X, cannot use Y)\n"
        "- Deadlines and timelines\n"
        "- Priority changes\n"
        "- Process decisions\n"
        "- Risk acknowledgments\n"
        "- Dependencies between teams/projects\n\n"
        "Only extract facts that are clearly stated or decided. Do not infer.\n\n"
        f"Conversation turn:\n{turn_content}\n\n"
        "Respond with a JSON object containing:\n"
        '  "facts": [\n'
        "    {\n"
        f'      "category": one of {FACT_CATEGORIES},\n'
        '      "content": "the fact statement",\n'
        '      "confidence": 0.0 to 1.0\n'
        "    }\n"
        "  ]\n"
        "If no facts are found, return an empty facts array."
    )

    schema = {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": FACT_CATEGORIES},
                        "content": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    },
                    "required": ["category", "content", "confidence"],
                },
            },
        },
        "required": ["facts"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a fact extraction system. Extract only clearly stated facts from conversation turns.",
        )

        extracted: list[dict[str, Any]] = []
        for fact_data in result.get("facts", []):
            if fact_data.get("confidence", 0) < 0.6:
                continue

            fact = await store_fact(
                content=fact_data["content"],
                category=fact_data["category"],
                project_id=project_id,
                source="conversation",
                confidence=fact_data["confidence"],
                db=db,
            )
            extracted.append(fact)

        logger.info("Extracted %d hard facts from conversation turn", len(extracted))
        return extracted

    except Exception as exc:
        logger.warning("Fact extraction failed: %s", exc)
        return []


async def store_fact(
    content: str,
    category: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    project_id: str | None = None,
    source: str = "conversation",
    entity_type: str | None = None,
    entity_id: str | None = None,
    confidence: float = 1.0,
) -> dict[str, Any]:
    """Store a hard fact in the database.

    Args:
        content: The fact statement.
        category: Fact category from FACT_CATEGORIES.
        db: Motor database handle.
        project_id: Optional project scope.
        source: Where the fact came from.
        entity_type: Optional entity type (person, project, etc.).
        entity_id: Optional entity identifier.
        confidence: AI confidence score.

    Returns:
        The stored fact document.
    """
    fact_doc: dict[str, Any] = {
        "fact_id": generate_uuid(),
        "content": content,
        "category": category if category in FACT_CATEGORIES else "other",
        "project_id": project_id,
        "source": source,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "confidence": confidence,
        "active": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    await db.conversation_facts.insert_one(fact_doc)
    logger.debug("Stored fact [%s]: %s", category, content[:80])
    return fact_doc


async def get_active_facts(
    project_id: str | None,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[dict[str, Any]]:
    """Retrieve all active hard facts for a project.

    Args:
        project_id: Project ID to filter by, or None for global facts.
        db: Motor database handle.

    Returns:
        List of active fact documents, sorted by creation date.
    """
    query: dict[str, Any] = {"active": True}
    if project_id:
        query["$or"] = [
            {"project_id": project_id},
            {"project_id": None},  # Include global facts
        ]

    facts: list[dict[str, Any]] = []
    async for doc in db.conversation_facts.find(query).sort("created_at", 1):
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        facts.append(doc)

    return facts


async def supersede_fact(
    old_fact_id: str,
    new_fact: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Supersede an existing fact with a new one.

    Marks the old fact as inactive and creates the new fact with a
    reference to the superseded fact.

    Args:
        old_fact_id: UUID of the fact being superseded.
        new_fact: Dict with ``content`` and ``category`` for the new fact.
        db: Motor database handle.

    Returns:
        The new fact document.
    """
    # Deactivate old fact
    old_doc = await db.conversation_facts.find_one({"fact_id": old_fact_id})
    if old_doc:
        await db.conversation_facts.update_one(
            {"fact_id": old_fact_id},
            {
                "$set": {
                    "active": False,
                    "superseded_at": utc_now(),
                    "updated_at": utc_now(),
                }
            },
        )

    # Create new fact
    new_doc: dict[str, Any] = {
        "fact_id": generate_uuid(),
        "content": new_fact.get("content", ""),
        "category": new_fact.get("category", "other"),
        "project_id": new_fact.get("project_id")
        or (old_doc.get("project_id") if old_doc else None),
        "source": new_fact.get("source", "correction"),
        "entity_type": new_fact.get("entity_type"),
        "entity_id": new_fact.get("entity_id"),
        "confidence": new_fact.get("confidence", 1.0),
        "supersedes": old_fact_id,
        "active": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    await db.conversation_facts.insert_one(new_doc)
    logger.info("Fact %s superseded by %s", old_fact_id, new_doc["fact_id"])
    return new_doc
