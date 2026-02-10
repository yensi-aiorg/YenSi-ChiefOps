"""
Context builder for the memory system.

Assembles the full context from five layers:
1. Hard facts (always included)
2. Project data (COO briefing + file summaries)
3. Compacted summary (if available)
4. Last N recent conversation turns
5. Citex RAG chunks (relevant document passages)

Manages a token budget of approximately 16000 tokens total.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.services.memory.compactor import RECENT_WINDOW
from app.services.memory.hard_facts import get_active_facts

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Token budget allocation (approximate)
TOTAL_TOKEN_BUDGET = 16000  # ~16k tokens target
HARD_FACTS_BUDGET = 2000
PROJECT_DATA_BUDGET = 4000
SUMMARY_BUDGET = 3000
RECENT_TURNS_BUDGET = 4000
RAG_CHUNKS_BUDGET = 3000

# Approximate tokens per character (conservative estimate)
CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def _truncate_to_budget(text: str, token_budget: int) -> str:
    """Truncate text to fit within a token budget."""
    max_chars = token_budget * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated to fit context budget]"


async def assemble_context(
    project_id: str,
    query: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    rag_chunks: list[str] | None = None,
) -> str:
    """Assemble the full context for the AI from all memory layers.

    Args:
        project_id: Project identifier for scoping.
        query: The current user query (used for relevance weighting).
        db: Motor database handle.
        rag_chunks: Pre-retrieved RAG chunks from Citex (optional).

    Returns:
        A formatted context string ready for the AI prompt.
    """
    sections: list[str] = []

    # --- Layer 1: Hard Facts ---
    facts_section = await _build_facts_section(project_id, db)
    if facts_section:
        sections.append(facts_section)

    # --- Layer 2: Project Data (COO Briefing + File Summaries) ---
    project_data_section = await _build_project_data_section(project_id, db)
    if project_data_section:
        sections.append(project_data_section)

    # --- Layer 3: Compacted Summary ---
    summary_section = await _build_summary_section(project_id, db)
    if summary_section:
        sections.append(summary_section)

    # --- Layer 4: Recent Turns ---
    turns_section = await _build_recent_turns_section(project_id, db)
    if turns_section:
        sections.append(turns_section)

    # --- Layer 5: RAG Chunks ---
    rag_section = _build_rag_section(rag_chunks)
    if rag_section:
        sections.append(rag_section)

    context = "\n\n".join(sections)

    total_tokens = _estimate_tokens(context)
    logger.debug(
        "Assembled context for project %s: ~%d tokens (%d sections)",
        project_id,
        total_tokens,
        len(sections),
    )

    return context


async def _build_project_data_section(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Build the project data section from COO briefing and file summaries."""
    lines: list[str] = []

    # --- COO Briefing ---
    briefing_doc = await db.coo_briefings.find_one(
        {"project_id": project_id, "status": "completed"},
        sort=[("created_at", -1)],
    )
    if briefing_doc:
        briefing = briefing_doc.get("briefing") or {}
        lines.append("## Project Briefing")

        exec_summary = briefing.get("executive_summary", "")
        if exec_summary:
            lines.append("### Executive Summary")
            lines.append(exec_summary)
            lines.append("")

        attention_items = briefing.get("attention_items") or []
        if attention_items:
            lines.append("### Attention Items")
            for item in attention_items:
                severity = item.get("severity", "INFO").upper()
                title = item.get("title", "")
                details = item.get("details", "")
                lines.append(f"- [{severity}] {title}: {details}")
            lines.append("")

        health = briefing.get("project_health")
        if health:
            score = health.get("score", "?")
            status = health.get("status", "unknown")
            rationale = health.get("rationale", "")
            lines.append("### Project Health")
            lines.append(f"Score: {score}/100 ({status}) — {rationale}")
            lines.append("")

        capacity = briefing.get("team_capacity") or []
        if capacity:
            lines.append("### Team Capacity")
            for person in capacity:
                name = person.get("person", "")
                p_status = person.get("status", "")
                details = person.get("details", "")
                lines.append(f"- {name}: {p_status} — {details}")
            lines.append("")

        deadlines = briefing.get("upcoming_deadlines") or []
        if deadlines:
            lines.append("### Deadlines")
            for dl in deadlines:
                item = dl.get("item", "")
                date = dl.get("date", "")
                d_status = dl.get("status", "")
                lines.append(f"- {item} ({date}): {d_status}")
            lines.append("")

        changes = briefing.get("recent_changes") or []
        if changes:
            lines.append("### Recent Changes")
            for ch in changes:
                change = ch.get("change", "")
                impact = ch.get("impact", "")
                lines.append(f"- {change} → {impact}")
            lines.append("")

    # --- File Summaries ---
    summaries_cursor = db.file_summaries.find(
        {"project_id": project_id, "status": "completed"},
        {"filename": 1, "file_type": 1, "summary_markdown": 1, "_id": 0},
    ).sort("created_at", -1)

    file_summaries: list[dict[str, Any]] = await summaries_cursor.to_list(length=50)
    if file_summaries:
        lines.append("## File Summaries")
        for fs in file_summaries:
            filename = fs.get("filename", "unknown")
            file_type = fs.get("file_type", "")
            md = fs.get("summary_markdown", "")
            if md:
                lines.append(f"### {filename} ({file_type})")
                lines.append(md)
                lines.append("---")
                lines.append("")

    if not lines:
        return ""

    section = "\n".join(lines)
    return _truncate_to_budget(section, PROJECT_DATA_BUDGET)


async def _build_facts_section(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Build the hard facts section of the context."""
    facts = await get_active_facts(project_id, db)
    if not facts:
        return ""

    lines: list[str] = ["## Established Facts"]
    for fact in facts:
        category = fact.get("category", "other")
        content = fact.get("content", "")
        lines.append(f"- [{category}] {content}")

    section = "\n".join(lines)
    return _truncate_to_budget(section, HARD_FACTS_BUDGET)


async def _build_summary_section(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Build the compacted summary section."""
    summary_doc = await db.compacted_summaries.find_one(
        {"project_id": project_id},
        sort=[("created_at", -1)],
    )

    if not summary_doc:
        return ""

    summary_text = summary_doc.get("summary", "")
    if not summary_text:
        return ""

    section = f"## Previous Conversation Summary\n{summary_text}"
    return _truncate_to_budget(section, SUMMARY_BUDGET)


async def _build_recent_turns_section(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Build the recent conversation turns section."""

    # Get the last RECENT_WINDOW turns
    turns: list[dict[str, Any]] = []
    cursor = (
        db.conversation_turns.find({"project_id": project_id})
        .sort("turn_number", -1)
        .limit(RECENT_WINDOW)
    )

    async for turn in cursor:
        turns.append(turn)

    if not turns:
        return ""

    # Reverse to chronological order
    turns.reverse()

    lines: list[str] = ["## Recent Conversation"]
    for turn in turns:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        turn_num = turn.get("turn_number", "?")

        # Truncate individual turns if very long
        if len(content) > 1000:
            content = content[:1000] + "..."

        role_label = "COO" if role == "user" else "ChiefOps"
        lines.append(f"**{role_label}** (turn {turn_num}):")
        lines.append(content)
        lines.append("")

    section = "\n".join(lines)
    return _truncate_to_budget(section, RECENT_TURNS_BUDGET)


def _build_rag_section(rag_chunks: list[str] | None) -> str:
    """Build the RAG chunks section from Citex results."""
    if not rag_chunks:
        return ""

    lines: list[str] = ["## Relevant Document Excerpts"]
    total_chars = 0
    max_chars = RAG_CHUNKS_BUDGET * CHARS_PER_TOKEN

    for i, chunk in enumerate(rag_chunks):
        if total_chars + len(chunk) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 100:
                lines.append(f"### Excerpt {i + 1}")
                lines.append(chunk[:remaining] + "...")
            break

        lines.append(f"### Excerpt {i + 1}")
        lines.append(chunk)
        lines.append("")
        total_chars += len(chunk)

    return "\n".join(lines)
