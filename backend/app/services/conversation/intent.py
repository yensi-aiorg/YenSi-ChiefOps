"""
Intent detection for conversation messages.

Classifies incoming messages into action categories:
- query: Information requests about projects, people, data
- correction: COO correcting a person's role or project detail
- command: Widget creation, report generation, alert setup, dashboard actions
- chat: General conversation or chitchat
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """Detected intent from a user message."""

    intent_type: str  # query, correction, command, chat
    sub_type: str = ""  # widget, report, alert, dashboard, role_correction, etc.
    confidence: float = 0.0
    parameters: dict[str, Any] = field(default_factory=dict)
    raw_message: str = ""


# Keyword patterns for fast intent detection (before AI fallback)
_COMMAND_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "widget": [
        re.compile(r"\b(?:create|make|add|build|show)\b.*\b(?:widget|chart|graph|metric|gauge|kpi)\b", re.IGNORECASE),
        re.compile(r"\b(?:widget|chart|graph)\b.*\b(?:for|showing|with|of)\b", re.IGNORECASE),
    ],
    "report": [
        re.compile(r"\b(?:generate|create|make|build|prepare|write)\b.*\b(?:report|summary|overview|status update)\b", re.IGNORECASE),
        re.compile(r"\b(?:report|summary)\b.*\b(?:on|about|for)\b", re.IGNORECASE),
    ],
    "alert": [
        re.compile(r"\b(?:set|create|add|configure)\b.*\b(?:alert|notification|warning|threshold|trigger)\b", re.IGNORECASE),
        re.compile(r"\b(?:alert|notify|warn)\b.*\b(?:when|if|once)\b", re.IGNORECASE),
    ],
    "dashboard": [
        re.compile(r"\b(?:create|make|build|setup|configure)\b.*\b(?:dashboard|board|view)\b", re.IGNORECASE),
        re.compile(r"\b(?:add|put)\b.*\b(?:to|on|in)\b.*\b(?:dashboard|board)\b", re.IGNORECASE),
    ],
}

_CORRECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:actually|no|wrong|incorrect|correct|fix)\b.*\b(?:is|role|title|department)\b", re.IGNORECASE),
    re.compile(r"\b(?:he|she|they)\b.*\b(?:is|are)\b.*\b(?:a|an|the)\b.*\b(?:manager|lead|developer|engineer|designer|analyst)\b", re.IGNORECASE),
    re.compile(r"\b(?:change|update|set|assign)\b.*\b(?:role|title|department|position)\b", re.IGNORECASE),
    re.compile(r"\bactually\b.*\b(?:works|working)\b.*\b(?:as|in)\b", re.IGNORECASE),
]

_QUERY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:who|what|when|where|how|why|which|tell me|show me|list|find)\b", re.IGNORECASE),
    re.compile(r"\b(?:status|health|progress|velocity|blockers|risks|gaps)\b", re.IGNORECASE),
    re.compile(r"\b(?:how many|how much|count|total|average|percentage)\b", re.IGNORECASE),
    re.compile(r"\?$"),
]


async def detect_intent(
    message: str,
    ai_adapter: Any,
) -> Intent:
    """Detect the intent of a user message.

    Uses pattern matching for fast detection, falling back to AI
    classification for ambiguous messages.

    Args:
        message: The user's message text.
        ai_adapter: AI adapter instance for fallback classification.

    Returns:
        An ``Intent`` object with type, sub-type, and parameters.
    """
    message = message.strip()
    if not message:
        return Intent(intent_type="chat", confidence=1.0, raw_message=message)

    # Try pattern-based detection first
    intent = _pattern_detect(message)
    if intent.confidence >= 0.7:
        return intent

    # Fallback to AI classification
    if ai_adapter is not None:
        ai_intent = await _ai_detect(message, ai_adapter)
        if ai_intent.confidence > intent.confidence:
            return ai_intent

    # Return the best pattern match or default to query
    if intent.confidence > 0:
        return intent

    # Default: if it looks like a question, it's a query; otherwise chat
    if message.endswith("?") or any(p.search(message) for p in _QUERY_PATTERNS):
        return Intent(intent_type="query", confidence=0.5, raw_message=message)

    return Intent(intent_type="chat", confidence=0.4, raw_message=message)


def _pattern_detect(message: str) -> Intent:
    """Detect intent using regex pattern matching."""

    # Check corrections first (they are specific)
    for pattern in _CORRECTION_PATTERNS:
        if pattern.search(message):
            params = _extract_correction_params(message)
            return Intent(
                intent_type="correction",
                sub_type="role_correction",
                confidence=0.8,
                parameters=params,
                raw_message=message,
            )

    # Check commands
    for sub_type, patterns in _COMMAND_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(message):
                return Intent(
                    intent_type="command",
                    sub_type=sub_type,
                    confidence=0.8,
                    parameters={"description": message},
                    raw_message=message,
                )

    # Check queries
    for pattern in _QUERY_PATTERNS:
        if pattern.search(message):
            return Intent(
                intent_type="query",
                confidence=0.6,
                raw_message=message,
            )

    return Intent(intent_type="", confidence=0.0, raw_message=message)


def _extract_correction_params(message: str) -> dict[str, Any]:
    """Extract correction parameters from a correction message."""
    params: dict[str, Any] = {"raw_correction": message}

    # Try to extract person name
    name_patterns = [
        re.compile(r"(\w+(?:\s+\w+)?)\s+(?:is|works as|is actually)\s+(?:a\s+)?(.+)", re.IGNORECASE),
        re.compile(r"(?:change|update|set)\s+(\w+(?:\s+\w+)?)'?s?\s+role\s+to\s+(.+)", re.IGNORECASE),
    ]
    for pattern in name_patterns:
        match = pattern.search(message)
        if match:
            params["person_name"] = match.group(1).strip()
            params["new_role"] = match.group(2).strip().rstrip(".")
            break

    return params


async def _ai_detect(message: str, ai_adapter: Any) -> Intent:
    """Use AI to classify the message intent."""
    prompt = (
        "Classify the following message into one of these intent categories:\n"
        "- query: Asking for information about projects, people, status, metrics\n"
        "- correction: Correcting a person's role, title, department, or other attribute\n"
        "- command: Requesting creation of a widget, report, alert, or dashboard\n"
        "- chat: General conversation, greetings, or unrelated discussion\n\n"
        f'Message: "{message}"\n\n'
        "Respond with a JSON object containing:\n"
        '  "intent_type": one of [query, correction, command, chat]\n'
        '  "sub_type": specific type (widget, report, alert, dashboard, role_correction, or empty)\n'
        '  "confidence": 0.0 to 1.0\n'
        '  "parameters": any extracted parameters as key-value pairs'
    )

    schema = {
        "type": "object",
        "properties": {
            "intent_type": {"type": "string", "enum": ["query", "correction", "command", "chat"]},
            "sub_type": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "parameters": {"type": "object"},
        },
        "required": ["intent_type", "confidence"],
    }

    try:
        result = await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are an intent classifier for a project management assistant.",
        )

        return Intent(
            intent_type=result.get("intent_type", "chat"),
            sub_type=result.get("sub_type", ""),
            confidence=result.get("confidence", 0.5),
            parameters=result.get("parameters", {}),
            raw_message=message,
        )

    except Exception as exc:
        logger.warning("AI intent detection failed: %s", exc)
        return Intent(intent_type="chat", confidence=0.3, raw_message=message)
