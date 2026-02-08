"""
Conversation orchestrator.

Handles the full lifecycle of a conversation message:
1. Assembles context via MemoryManager
2. Detects intent
3. Routes to appropriate handler (query, correction, command)
4. Streams response
5. Stores turn in MongoDB
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.base import generate_uuid, utc_now
from app.services.conversation.intent import Intent, detect_intent
from app.services.memory.manager import get_context, process_turn

logger = logging.getLogger(__name__)

# System prompt for ChiefOps AI
SYSTEM_PROMPT = (
    "You are ChiefOps, an AI-powered Chief of Staff assistant for technology companies. "
    "You help the COO understand team dynamics, project health, risks, and blockers. "
    "You speak in a professional but approachable tone. You are direct and data-driven. "
    "When you reference data, cite specific numbers and sources. "
    "When you identify risks or gaps, explain your reasoning. "
    "If you are uncertain, say so rather than guessing. "
    "You can create widgets, generate reports, set alerts, and manage dashboards "
    "when asked by the COO."
)


async def process_message(
    content: str,
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> AsyncGenerator[str, None]:
    """Process a conversation message and yield response chunks.

    Args:
        content: The user's message text.
        project_id: Project scope for the conversation.
        db: Motor database handle.
        ai_adapter: AI adapter instance with streaming support.

    Yields:
        Response text chunks as they are generated.
    """
    # Store user turn
    user_turn_number = await _get_next_turn_number(project_id, db)
    await _store_turn(
        project_id=project_id,
        turn_number=user_turn_number,
        role="user",
        content=content,
        db=db,
    )

    # Detect intent
    intent = await detect_intent(content, ai_adapter)
    logger.info(
        "Intent detected: %s/%s (confidence: %.2f) for project %s",
        intent.intent_type,
        intent.sub_type,
        intent.confidence,
        project_id,
    )

    # Assemble context from memory
    context = await get_context(project_id, content, db, ai_adapter)

    # Route based on intent
    full_response: list[str] = []

    if intent.intent_type == "correction":
        async for chunk in _handle_correction(content, intent, context, project_id, db, ai_adapter):
            full_response.append(chunk)
            yield chunk

    elif intent.intent_type == "command":
        async for chunk in _handle_command(content, intent, context, project_id, db, ai_adapter):
            full_response.append(chunk)
            yield chunk

    else:
        # query or chat
        async for chunk in _handle_query(content, context, project_id, db, ai_adapter):
            full_response.append(chunk)
            yield chunk

    # Store assistant turn
    assistant_content = "".join(full_response)
    assistant_turn_number = await _get_next_turn_number(project_id, db)
    await _store_turn(
        project_id=project_id,
        turn_number=assistant_turn_number,
        role="assistant",
        content=assistant_content,
        intent_type=intent.intent_type,
        intent_sub_type=intent.sub_type,
        db=db,
    )

    # Post-turn processing (fact extraction, compaction)
    combined_turn = f"User: {content}\n\nAssistant: {assistant_content}"
    await process_turn(combined_turn, project_id, db, ai_adapter)


async def _handle_query(
    content: str,
    context: str,
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> AsyncGenerator[str, None]:
    """Handle a query or chat message."""
    prompt = _build_prompt(content, context)

    if ai_adapter is None:
        yield "I'm currently unable to process your request as the AI service is not available. Please try again later."
        return

    try:
        async for chunk in ai_adapter.stream_text(
            prompt=prompt,
            system=SYSTEM_PROMPT,
        ):
            yield chunk
    except Exception as exc:
        logger.exception("AI streaming failed for query")
        yield f"I encountered an error while processing your request: {exc}"


async def _handle_correction(
    content: str,
    intent: Intent,
    context: str,
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> AsyncGenerator[str, None]:
    """Handle a person/role correction from the COO."""
    from app.services.people.corrections import apply_correction

    params = intent.parameters
    person_name = params.get("person_name", "")
    new_role = params.get("new_role", "")

    if person_name and new_role:
        # Find the person by name
        person = await db.people.find_one({
            "name": {"$regex": person_name, "$options": "i"}
        })

        if person:
            try:
                correction_data: dict[str, Any] = {"role": new_role}
                await apply_correction(person["person_id"], correction_data, db)
                yield (
                    f"Got it. I've updated {person['name']}'s role to **{new_role}**. "
                    f"This correction has been recorded and will be preserved in future analyses."
                )
                return
            except Exception as exc:
                logger.warning("Correction failed: %s", exc)
                yield f"I tried to update the role but encountered an error: {exc}"
                return
        else:
            yield (
                f"I couldn't find a person matching '{person_name}' in the directory. "
                "Could you provide the exact name as it appears in the system?"
            )
            return

    # If we couldn't extract parameters, use AI to process the correction
    prompt = (
        f"{context}\n\n"
        "The COO wants to make a correction. Parse the following message and "
        "identify what needs to be corrected.\n\n"
        f"Message: {content}"
    )

    if ai_adapter is not None:
        try:
            async for chunk in ai_adapter.stream_text(prompt=prompt, system=SYSTEM_PROMPT):
                yield chunk
        except Exception as exc:
            yield f"I had trouble processing that correction: {exc}"
    else:
        yield "I understand you want to make a correction, but I need the AI service to process this. Please try again later."


async def _handle_command(
    content: str,
    intent: Intent,
    context: str,
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> AsyncGenerator[str, None]:
    """Handle a command (widget, report, alert, dashboard creation)."""

    if intent.sub_type == "widget":
        try:
            from app.services.widgets.spec_generator import generate_widget_spec

            # Find the default dashboard for this project
            dashboard = await db.dashboards.find_one({"project_id": project_id})
            dashboard_id = dashboard["_id"] if dashboard else None

            if dashboard_id is None:
                # Create a default dashboard
                dashboard_doc = {
                    "project_id": project_id,
                    "dashboard_type": "default",
                    "name": "Default Dashboard",
                    "widgets": [],
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                }
                insert_result = await db.dashboards.insert_one(dashboard_doc)
                dashboard_id = str(insert_result.inserted_id)

            spec = await generate_widget_spec(
                description=content,
                dashboard_id=str(dashboard_id),
                db=db,
                ai_adapter=ai_adapter,
            )
            yield f"I've created a new widget: **{spec.get('title', 'Widget')}**. "
            yield f"Type: {spec.get('chart_type', 'metric')}. "
            yield "It has been added to your dashboard."
            return
        except Exception as exc:
            logger.warning("Widget creation failed: %s", exc)
            yield f"I tried to create the widget but encountered an error: {exc}"
            return

    elif intent.sub_type == "report":
        try:
            from app.services.reports.generator import generate_report

            report = await generate_report(content, project_id, db, ai_adapter)
            yield f"I've generated a report: **{report.get('title', 'Report')}**. "
            yield "You can view it in the Reports section or export it as PDF."
            return
        except Exception as exc:
            logger.warning("Report generation failed: %s", exc)
            yield f"I tried to generate the report but encountered an error: {exc}"
            return

    elif intent.sub_type == "alert":
        try:
            from app.services.alerts.alert_engine import create_alert_from_nl

            alert = await create_alert_from_nl(content, db, ai_adapter)
            yield f"I've set up an alert: **{alert.get('name', 'Alert')}**. "
            yield f"Condition: {alert.get('condition_description', 'N/A')}. "
            yield "I'll notify you when this threshold is reached."
            return
        except Exception as exc:
            logger.warning("Alert creation failed: %s", exc)
            yield f"I tried to create the alert but encountered an error: {exc}"
            return

    elif intent.sub_type == "dashboard":
        prompt = (
            f"{context}\n\n"
            "The COO wants to set up or modify a dashboard. Help them with the following request:\n\n"
            f"Message: {content}"
        )
        if ai_adapter is not None:
            try:
                async for chunk in ai_adapter.stream_text(prompt=prompt, system=SYSTEM_PROMPT):
                    yield chunk
            except Exception as exc:
                yield f"I had trouble with the dashboard request: {exc}"
        else:
            yield "I need the AI service to process dashboard commands. Please try again later."
        return

    # Generic command fallback
    prompt = _build_prompt(content, context)
    if ai_adapter is not None:
        try:
            async for chunk in ai_adapter.stream_text(prompt=prompt, system=SYSTEM_PROMPT):
                yield chunk
        except Exception as exc:
            yield f"I encountered an error: {exc}"
    else:
        yield "I'm unable to process this command without the AI service."


def _build_prompt(content: str, context: str) -> str:
    """Build the full prompt with context and user message."""
    parts: list[str] = []

    if context:
        parts.append("## Context")
        parts.append(context)
        parts.append("")

    parts.append("## Current Message")
    parts.append(content)

    return "\n".join(parts)


async def _get_next_turn_number(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> int:
    """Get the next turn number for a project's conversation."""
    last_turn = await db.conversation_turns.find_one(
        {"project_id": project_id},
        sort=[("turn_number", -1)],
    )
    if last_turn:
        return last_turn.get("turn_number", 0) + 1
    return 1


async def _store_turn(
    project_id: str,
    turn_number: int,
    role: str,
    content: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    intent_type: str = "",
    intent_sub_type: str = "",
) -> None:
    """Store a conversation turn in MongoDB."""
    turn_doc = {
        "turn_id": generate_uuid(),
        "project_id": project_id,
        "turn_number": turn_number,
        "role": role,
        "content": content,
        "intent_type": intent_type,
        "intent_sub_type": intent_sub_type,
        "created_at": utc_now(),
    }
    await db.conversation_turns.insert_one(turn_doc)
