"""
PII redaction service.

Identifies and redacts personally identifiable information from text
content before storage or AI processing. Uses regex patterns for
emails, phone numbers, SSNs, credit card numbers, and other sensitive
data patterns.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# Redaction placeholder format
_REDACTED = "[REDACTED]"
_REDACTED_EMAIL = "[EMAIL REDACTED]"
_REDACTED_PHONE = "[PHONE REDACTED]"
_REDACTED_SSN = "[SSN REDACTED]"
_REDACTED_CC = "[CREDIT CARD REDACTED]"
_REDACTED_IP = "[IP REDACTED]"
_REDACTED_PASSPORT = "[PASSPORT REDACTED]"

# Pre-compiled regex patterns for PII detection
_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # Email addresses
    (
        re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
        ),
        _REDACTED_EMAIL,
        "email",
    ),
    # US phone numbers (various formats)
    (
        re.compile(
            r"(?<!\d)"  # Not preceded by digit
            r"(?:"
            r"\+?1[\s.-]?"  # Optional country code
            r")?"
            r"(?:\(?\d{3}\)?[\s.-]?)"  # Area code
            r"\d{3}[\s.-]?"  # Exchange
            r"\d{4}"  # Subscriber
            r"(?!\d)"  # Not followed by digit
        ),
        _REDACTED_PHONE,
        "phone",
    ),
    # International phone numbers
    (
        re.compile(
            r"\+\d{1,3}[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,4}(?:[\s.-]?\d{1,4})?"
        ),
        _REDACTED_PHONE,
        "phone_international",
    ),
    # US Social Security Numbers (XXX-XX-XXXX)
    (
        re.compile(
            r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
        ),
        _REDACTED_SSN,
        "ssn",
    ),
    # Credit card numbers (major patterns)
    (
        re.compile(
            r"\b(?:"
            r"4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"  # Visa
            r"|5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"  # Mastercard
            r"|3[47]\d{1}[-\s]?\d{6}[-\s]?\d{5}"  # Amex
            r"|6(?:011|5\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"  # Discover
            r")\b"
        ),
        _REDACTED_CC,
        "credit_card",
    ),
    # IPv4 addresses (when they look like private/specific IPs)
    (
        re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"  # 10.x.x.x
            r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"  # 172.16-31.x.x
            r"|192\.168\.\d{1,3}\.\d{1,3})\b"  # 192.168.x.x
        ),
        _REDACTED_IP,
        "private_ip",
    ),
    # Passport numbers (common formats)
    (
        re.compile(
            r"\b[A-Z]{1,2}\d{6,9}\b"
        ),
        _REDACTED_PASSPORT,
        "passport",
    ),
]

# Additional patterns that are more aggressive (opt-in)
_AGGRESSIVE_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # Date of birth patterns
    (
        re.compile(
            r"\b(?:DOB|date of birth|born on|birthday)[:\s]*"
            r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b",
            re.IGNORECASE,
        ),
        "[DOB REDACTED]",
        "dob",
    ),
    # Street addresses (basic US format)
    (
        re.compile(
            r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s+){1,3}"
            r"(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ln|Lane|Rd|Road|Way|Ct|Court)"
            r"(?:\.|\b)",
            re.IGNORECASE,
        ),
        "[ADDRESS REDACTED]",
        "address",
    ),
]


def redact_pii(text: str, aggressive: bool = False) -> str:
    """Redact PII from text content.

    Applies regex-based pattern matching to identify and replace
    personally identifiable information with redaction placeholders.

    Args:
        text: The text to redact.
        aggressive: If True, also applies aggressive patterns (addresses, DOB).

    Returns:
        The text with PII replaced by redaction markers.
    """
    settings = get_settings()
    if not settings.PII_REDACTION_ENABLED:
        return text

    if not text:
        return text

    redacted = text
    patterns_applied = 0

    for pattern, replacement, pii_type in _PATTERNS:
        new_text, count = pattern.subn(replacement, redacted)
        if count > 0:
            patterns_applied += count
            redacted = new_text
            logger.debug("Redacted %d %s pattern(s)", count, pii_type)

    if aggressive:
        for pattern, replacement, pii_type in _AGGRESSIVE_PATTERNS:
            new_text, count = pattern.subn(replacement, redacted)
            if count > 0:
                patterns_applied += count
                redacted = new_text
                logger.debug("Redacted %d %s pattern(s) (aggressive)", count, pii_type)

    if patterns_applied > 0:
        logger.info("Redacted %d PII patterns from text", patterns_applied)

    return redacted


def scan_for_pii(text: str) -> list[dict[str, Any]]:
    """Scan text for PII without redacting.

    Identifies PII locations and types for audit logging or
    user notification.

    Args:
        text: The text to scan.

    Returns:
        List of dicts with ``type``, ``start``, ``end``, and ``snippet`` keys.
    """
    if not text:
        return []

    findings: list[dict[str, Any]] = []

    for pattern, _, pii_type in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append({
                "type": pii_type,
                "start": match.start(),
                "end": match.end(),
                "snippet": _mask_snippet(match.group()),
            })

    return findings


def _mask_snippet(text: str) -> str:
    """Mask a PII snippet for safe logging (show first/last chars only)."""
    if len(text) <= 4:
        return "*" * len(text)
    return text[0] + "*" * (len(text) - 2) + text[-1]


def redact_dict(data: dict[str, Any], fields: list[str] | None = None) -> dict[str, Any]:
    """Redact PII from string values in a dictionary.

    Args:
        data: The dictionary to process.
        fields: Optional list of field names to redact. If None, all
                string values are processed.

    Returns:
        A new dictionary with PII redacted from specified fields.
    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, str):
            if fields is None or key in fields:
                result[key] = redact_pii(value)
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = redact_dict(value, fields)
        elif isinstance(value, list):
            result[key] = [
                redact_pii(item) if isinstance(item, str) else
                redact_dict(item, fields) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result
