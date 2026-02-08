"""
Natural language report editing service.

Allows the COO to modify an existing report through conversational
instructions (e.g., "add a section about blockers", "remove the risk
section", "make the summary shorter").
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.exceptions import NotFoundException
from app.models.base import utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def edit_report(
    report_id: str,
    instruction: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> dict[str, Any]:
    """Edit an existing report based on a natural language instruction.

    Loads the current report spec, sends it to AI along with the
    edit instruction, and stores the modified result.

    Args:
        report_id: UUID of the report to edit.
        instruction: Natural language edit instruction.
        db: Motor database handle.
        ai_adapter: AI adapter instance.

    Returns:
        The updated report document.

    Raises:
        NotFoundException: If the report_id does not exist.
    """
    report = await db.reports.find_one({"report_id": report_id})
    if not report:
        raise NotFoundException(resource="Report", identifier=report_id)

    if ai_adapter is not None:
        updated_spec = await _ai_edit_report(report, instruction, ai_adapter)
    else:
        updated_spec = _heuristic_edit_report(report, instruction)

    # Apply updates
    update_fields: dict[str, Any] = {
        "updated_at": utc_now(),
    }

    if "title" in updated_spec:
        update_fields["title"] = updated_spec["title"]
    if "summary" in updated_spec:
        update_fields["summary"] = updated_spec["summary"]
    if "sections" in updated_spec:
        update_fields["sections"] = updated_spec["sections"]
    if "key_metrics" in updated_spec:
        update_fields["key_metrics"] = updated_spec["key_metrics"]
    if "recommendations" in updated_spec:
        update_fields["recommendations"] = updated_spec["recommendations"]

    await db.reports.update_one(
        {"report_id": report_id},
        {"$set": update_fields},
    )

    # Return updated document
    updated = await db.reports.find_one({"report_id": report_id})
    if updated and "_id" in updated:
        updated["_id"] = str(updated["_id"])

    logger.info("Report %s edited: %s", report_id, instruction[:80])
    return updated or {}


async def _ai_edit_report(
    report: dict[str, Any],
    instruction: str,
    ai_adapter: Any,
) -> dict[str, Any]:
    """Use AI to edit the report based on instruction."""
    current_spec = {
        "title": report.get("title", ""),
        "summary": report.get("summary", ""),
        "sections": report.get("sections", []),
        "key_metrics": report.get("key_metrics", []),
        "recommendations": report.get("recommendations", []),
    }

    import json

    current_json = json.dumps(current_spec, indent=2, default=str)

    prompt = (
        "Edit the following report specification based on the instruction.\n\n"
        f"Current report:\n{current_json}\n\n"
        f"Edit instruction: {instruction}\n\n"
        "Return the COMPLETE updated report specification as JSON. "
        "Include ALL sections, not just the changed ones. "
        "Maintain the same structure but apply the requested changes."
    )

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["heading", "content"],
                },
            },
            "key_metrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                        "trend": {"type": "string"},
                    },
                    "required": ["label", "value"],
                },
            },
            "recommendations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "summary", "sections"],
    }

    try:
        return await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a report editor. Apply the requested changes while preserving the overall structure.",
        )
    except Exception as exc:
        logger.warning("AI report editing failed: %s", exc)
        return _heuristic_edit_report(report, instruction)


def _heuristic_edit_report(
    report: dict[str, Any],
    instruction: str,
) -> dict[str, Any]:
    """Apply simple heuristic edits to a report."""
    inst_lower = instruction.lower()
    result: dict[str, Any] = {}

    sections = list(report.get("sections", []))

    # Handle "remove" instructions
    if "remove" in inst_lower or "delete" in inst_lower:
        for section in sections[:]:
            heading = section.get("heading", "").lower()
            if any(word in heading for word in inst_lower.split() if len(word) > 3):
                sections.remove(section)
                logger.info("Removed section: %s", section.get("heading", ""))
        result["sections"] = sections

    # Handle "add" instructions
    elif "add" in inst_lower:
        new_section = {
            "heading": instruction.replace("add", "").replace("section", "").strip().title(),
            "content": "Content to be filled.",
            "type": "text",
        }
        sections.append(new_section)
        result["sections"] = sections

    # Handle title changes
    elif "title" in inst_lower or "rename" in inst_lower:
        # Extract new title from instruction
        for marker in ("to ", "as ", "title "):
            if marker in inst_lower:
                new_title = instruction.split(marker, 1)[-1].strip().strip('"').strip("'")
                if new_title:
                    result["title"] = new_title
                break

    # Handle summary changes
    elif "summary" in inst_lower:
        if "shorter" in inst_lower:
            current = report.get("summary", "")
            # Keep first sentence
            sentences = current.split(". ")
            if len(sentences) > 1:
                result["summary"] = sentences[0] + "."
        elif "longer" in inst_lower:
            result["summary"] = report.get("summary", "") + " Additional details to follow."

    return result
