"""
Semantic insight extraction and project snapshot synthesis.

This module turns unstructured narrative inputs (Slack text, notes,
meeting minutes, conversation snippets, uploaded markdown/text docs)
into canonical operational insights for dashboards and reports.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.ai.adapter import AIRequest, AIResponse
from app.ai.factory import get_adapter
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

HIGH_RISK_PATTERNS = [
    re.compile(r"\bnot\s+going\s+well\b", re.IGNORECASE),
    re.compile(r"\bmajor\s+red\s+flag\b", re.IGNORECASE),
    re.compile(r"\bblocked\b", re.IGNORECASE),
    re.compile(r"\boff\s+track\b", re.IGNORECASE),
    re.compile(r"\bmiss(ed|ing)\s+deadline\b", re.IGNORECASE),
]

QUESTION_PATTERNS = [
    re.compile(r"\bawaiting\s+metrics\b", re.IGNORECASE),
    re.compile(r"\bi\s+don't\s+know\s+what('?s| has)\s+happened\b", re.IGNORECASE),
]


def _normalize_source(source_type: str) -> str:
    return source_type.strip().lower() or "unknown"


def _to_jsonable(obj: Any) -> dict[str, Any]:
    if isinstance(obj, AIResponse):
        return obj.parse_json()
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        return json.loads(obj)
    raise ValueError("Unsupported structured AI response type")


async def _call_structured_ai(
    ai_adapter: Any,
    *,
    system: str,
    prompt: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    """
    Call AI adapter with compatibility for both interface styles:
    - generate_structured(AIRequest)
    - generate_structured(prompt=..., schema=..., system=...)
    """
    if ai_adapter is None:
        raise RuntimeError("AI adapter unavailable")

    try:
        request = AIRequest(
            system_prompt=system,
            user_prompt=prompt,
            response_schema=schema,
            temperature=0.1,
        )
        response = await ai_adapter.generate_structured(request)
        return _to_jsonable(response)
    except TypeError:
        response = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system=system,
        )
        return _to_jsonable(response)


def _heuristic_extract(content: str) -> list[dict[str, Any]]:
    """Fallback extractor when AI is unavailable or fails."""
    insights: list[dict[str, Any]] = []
    lowered = content.lower()

    if any(p.search(content) for p in HIGH_RISK_PATTERNS):
        insights.append(
            {
                "insight_type": "risk",
                "summary": "Narrative indicates project execution risk.",
                "severity": "high",
                "confidence": 0.8,
                "tags": ["risk", "narrative_signal"],
                "entities": [],
            }
        )

    if "decision" in lowered or "we decided" in lowered:
        insights.append(
            {
                "insight_type": "decision",
                "summary": "Narrative includes an explicit decision.",
                "severity": "medium",
                "confidence": 0.7,
                "tags": ["decision"],
                "entities": [],
            }
        )

    if "deadline" in lowered or "due" in lowered:
        insights.append(
            {
                "insight_type": "deadline_change",
                "summary": "Narrative references deadlines or schedule changes.",
                "severity": "medium",
                "confidence": 0.7,
                "tags": ["timeline"],
                "entities": [],
            }
        )

    if any(p.search(content) for p in QUESTION_PATTERNS):
        insights.append(
            {
                "insight_type": "question_signal",
                "summary": "COO uncertainty signal detected (metrics/context gap).",
                "severity": "high",
                "confidence": 0.85,
                "tags": ["leadership_signal", "metrics_gap"],
                "entities": [],
            }
        )

    return insights


async def extract_semantic_insights(
    *,
    project_id: str | None,
    source_type: str,
    source_ref: str,
    content: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any | None = None,
) -> dict[str, Any]:
    """Extract and persist semantic insights from a narrative text blob."""
    cleaned = content.strip()
    if not cleaned:
        return {"created": 0, "insights": []}

    adapter = ai_adapter
    if adapter is None:
        try:
            adapter = get_adapter()
        except Exception:
            adapter = None

    schema = {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "insight_type": {
                            "type": "string",
                            "enum": [
                                "assignment",
                                "decision",
                                "risk",
                                "blocker",
                                "deadline_change",
                                "direction_change",
                                "status_signal",
                                "question_signal",
                                "meeting_note",
                                "dependency",
                                "other",
                            ],
                        },
                        "summary": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "entities": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["insight_type", "summary", "severity", "confidence"],
                },
            }
        },
        "required": ["insights"],
    }

    ai_insights: list[dict[str, Any]] = []
    if adapter is not None:
        prompt = (
            "Extract operational insights from the narrative below.\n"
            "Focus on: ownership changes, assignments, blockers, decisions, risks, "
            "deadlines, direction shifts, unresolved questions, and dependencies.\n"
            "Return concise operational summaries.\n\n"
            f"Source type: {_normalize_source(source_type)}\n"
            f"Source ref: {source_ref}\n\n"
            f"Content:\n{cleaned[:18000]}"
        )
        try:
            parsed = await _call_structured_ai(
                adapter,
                system="You are an operations intelligence extraction engine.",
                prompt=prompt,
                schema=schema,
            )
            ai_insights = parsed.get("insights", [])
        except Exception as exc:
            logger.warning("AI semantic extraction failed for %s: %s", source_ref, exc)

    extracted = ai_insights if ai_insights else _heuristic_extract(cleaned)
    now = utc_now()
    created_ids: list[str] = []

    for item in extracted:
        confidence = float(item.get("confidence", 0.0))
        if confidence < 0.55:
            continue

        insight_id = generate_uuid()
        doc = {
            "insight_id": insight_id,
            "project_id": project_id,
            "source_type": _normalize_source(source_type),
            "source_ref": source_ref,
            "insight_type": item.get("insight_type", "other"),
            "summary": str(item.get("summary", "")).strip(),
            "severity": item.get("severity", "medium"),
            "confidence": confidence,
            "tags": item.get("tags", []),
            "entities": item.get("entities", []),
            "evidence": [
                {
                    "source_ref": source_ref,
                    "excerpt": cleaned[:500],
                }
            ],
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        if not doc["summary"]:
            continue
        await db.operational_insights.insert_one(doc)
        created_ids.append(insight_id)

    summary_text = _build_compact_summary_from_insights(extracted)

    await db.semantic_summaries.update_one(
        {"project_id": project_id, "source_type": _normalize_source(source_type), "source_ref": source_ref},
        {
            "$set": {
                "project_id": project_id,
                "source_type": _normalize_source(source_type),
                "source_ref": source_ref,
                "summary_text": summary_text,
                "insight_count": len(created_ids),
                "updated_at": now,
            },
            "$setOnInsert": {
                "summary_id": generate_uuid(),
                "created_at": now,
            },
        },
        upsert=True,
    )

    return {
        "created": len(created_ids),
        "insights": created_ids,
        "summary_text": summary_text,
    }


def _build_compact_summary_from_insights(insights: list[dict[str, Any]]) -> str:
    if not insights:
        return "No actionable operational signals extracted."
    lines = []
    for item in insights[:8]:
        severity = str(item.get("severity", "medium")).upper()
        summary = str(item.get("summary", "")).strip()
        if summary:
            lines.append(f"[{severity}] {summary}")
    return "\n".join(lines) if lines else "No actionable operational signals extracted."


async def extract_conversation_signal(
    *,
    content: str,
    project_id: str | None,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    source_ref: str = "conversation",
    ai_adapter: Any | None = None,
) -> dict[str, Any]:
    """
    Lightweight extraction for live COO messages.
    Always captures critical lexical patterns even if AI is unavailable.
    """
    created = 0
    text = content.strip()
    if not text:
        return {"created": 0}

    if any(p.search(text) for p in HIGH_RISK_PATTERNS):
        await db.operational_insights.insert_one(
            {
                "insight_id": generate_uuid(),
                "project_id": project_id,
                "source_type": "conversation",
                "source_ref": source_ref,
                "insight_type": "status_signal",
                "summary": "COO flagged major execution concern in conversation.",
                "severity": "critical",
                "confidence": 0.92,
                "tags": ["coo_signal", "red_flag"],
                "entities": [],
                "evidence": [{"excerpt": text[:500], "source_ref": source_ref}],
                "active": True,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
        created += 1

    if any(p.search(text) for p in QUESTION_PATTERNS):
        await db.operational_insights.insert_one(
            {
                "insight_id": generate_uuid(),
                "project_id": project_id,
                "source_type": "conversation",
                "source_ref": source_ref,
                "insight_type": "question_signal",
                "summary": "COO asked for missing context/metrics; requires synthesis.",
                "severity": "high",
                "confidence": 0.9,
                "tags": ["coo_signal", "context_gap"],
                "entities": [],
                "evidence": [{"excerpt": text[:500], "source_ref": source_ref}],
                "active": True,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
        created += 1

    ai_result = await extract_semantic_insights(
        project_id=project_id,
        source_type="conversation",
        source_ref=source_ref,
        content=text,
        db=db,
        ai_adapter=ai_adapter,
    )
    return {"created": created + int(ai_result.get("created", 0))}


async def generate_project_snapshot(
    *,
    project_id: str | None,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Build and persist current project/global operational snapshot:
    - summary
    - executive_summary
    - detailed_understanding
    """
    query: dict[str, Any] = {"project_id": project_id} if project_id else {"project_id": None}
    existing = await db.project_snapshots.find_one(query, sort=[("updated_at", -1)])
    if existing and not force:
        updated_at = existing.get("updated_at")
        if isinstance(updated_at, datetime):
            updated_at_utc = updated_at if updated_at.tzinfo is not None else updated_at.replace(tzinfo=UTC)
            if datetime.now(UTC) - updated_at_utc < timedelta(minutes=15):
                return existing

    insight_filter: dict[str, Any] = {"active": True}
    if project_id:
        insight_filter["project_id"] = project_id
    else:
        insight_filter["project_id"] = None

    insights = await db.operational_insights.find(insight_filter, {"_id": 0}).sort(
        [("severity", -1), ("created_at", -1)]
    ).to_list(length=500)
    insight_counts = Counter(str(x.get("insight_type", "other")) for x in insights)
    severity_counts = Counter(str(x.get("severity", "medium")) for x in insights)
    top_signals = insights[:10]

    project_doc = None
    if project_id:
        project_doc = await db.projects.find_one({"project_id": project_id}, {"_id": 0})

    default_summary = _heuristic_snapshot_text(project_doc, insight_counts, severity_counts, top_signals)
    executive_summary = default_summary["executive_summary"]
    summary = default_summary["summary"]
    detailed = default_summary["detailed_understanding"]

    adapter = ai_adapter
    if adapter is None:
        try:
            adapter = get_adapter()
        except Exception:
            adapter = None

    if adapter is not None:
        schema = {
            "type": "object",
            "properties": {
                "executive_summary": {"type": "string"},
                "summary": {"type": "string"},
                "detailed_understanding": {"type": "string"},
            },
            "required": ["executive_summary", "summary", "detailed_understanding"],
        }
        prompt = (
            "Generate current COO snapshot summaries from these operational signals.\n"
            "Be crisp and decision-oriented.\n\n"
            f"Project: {project_doc.get('name') if project_doc else 'Global'}\n"
            f"Insight counts by type: {dict(insight_counts)}\n"
            f"Severity counts: {dict(severity_counts)}\n"
            f"Top signals: {[s.get('summary', '') for s in top_signals[:12]]}\n"
        )
        try:
            parsed = await _call_structured_ai(
                adapter,
                system="You are a COO snapshot synthesis engine.",
                prompt=prompt,
                schema=schema,
            )
            executive_summary = parsed.get("executive_summary", executive_summary)
            summary = parsed.get("summary", summary)
            detailed = parsed.get("detailed_understanding", detailed)
        except Exception as exc:
            logger.warning("AI snapshot synthesis failed: %s", exc)

    snapshot_doc = {
        "snapshot_id": generate_uuid(),
        "project_id": project_id,
        "as_of": utc_now(),
        "executive_summary": executive_summary,
        "summary": summary,
        "detailed_understanding": detailed,
        "top_signals": top_signals,
        "insight_counts": dict(insight_counts),
        "severity_counts": dict(severity_counts),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    await db.project_snapshots.insert_one(snapshot_doc)
    return snapshot_doc


def _heuristic_snapshot_text(
    project_doc: dict[str, Any] | None,
    insight_counts: Counter[str],
    severity_counts: Counter[str],
    top_signals: list[dict[str, Any]],
) -> dict[str, str]:
    project_name = project_doc.get("name", "Portfolio") if project_doc else "Portfolio"
    critical = severity_counts.get("critical", 0)
    high = severity_counts.get("high", 0)
    blockers = insight_counts.get("blocker", 0)
    risks = insight_counts.get("risk", 0)
    decisions = insight_counts.get("decision", 0)

    executive = (
        f"{project_name} has {critical} critical and {high} high-severity operational signals. "
        f"Key pressure points include blockers ({blockers}) and risks ({risks}). "
        f"Decision velocity captured: {decisions} notable decisions."
    )

    lines = []
    for signal in top_signals[:8]:
        lines.append(f"- ({signal.get('severity', 'medium')}) {signal.get('summary', '')}")
    summary = (
        f"Signal mix: {dict(insight_counts)}. "
        f"Severity distribution: {dict(severity_counts)}.\n"
        + ("\n".join(lines) if lines else "No major signals detected.")
    )

    detailed = (
        "Current understanding combines narrative inputs from Slack, uploaded notes/docs, "
        "and COO conversation signals. "
        "Prioritize critical/high signals first, then resolve context gaps raised by leadership."
    )

    return {
        "executive_summary": executive,
        "summary": summary,
        "detailed_understanding": detailed,
    }
