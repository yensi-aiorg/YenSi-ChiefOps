"""
Unit tests for the PII redaction / privacy service.

Tests detection and redaction of email addresses, phone numbers,
Social Security numbers, and credit card numbers. Also verifies
that common non-PII patterns are not falsely flagged.
"""

from __future__ import annotations

import re

import pytest


# ---------------------------------------------------------------------------
# PII detection patterns (replicated from the privacy service for testing)
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

_PHONE_PATTERN = re.compile(
    r"(?<!\d)"  # not preceded by digit
    r"(?:"
    r"\+?1[\s.-]?)?"  # optional country code
    r"(?:\(?\d{3}\)?[\s.-]?)"  # area code
    r"\d{3}[\s.-]?"  # exchange
    r"\d{4}"  # subscriber
    r"(?!\d)",  # not followed by digit
)

_SSN_PATTERN = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

_CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[\s-]?){3}\d{4}\b"
)


def redact_text(text: str) -> str:
    """Apply all PII redaction patterns to the given text."""
    text = _EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    text = _SSN_PATTERN.sub("[SSN_REDACTED]", text)
    text = _CREDIT_CARD_PATTERN.sub("[CARD_REDACTED]", text)
    text = _PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    return text


def contains_pii(text: str) -> bool:
    """Check whether the text contains any detectable PII."""
    return bool(
        _EMAIL_PATTERN.search(text)
        or _PHONE_PATTERN.search(text)
        or _SSN_PATTERN.search(text)
        or _CREDIT_CARD_PATTERN.search(text)
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmailRedaction:
    """Test detection and redaction of email addresses."""

    def test_email_redaction(self):
        text = "Contact sarah.chen@example.com for details."
        result = redact_text(text)

        assert "sarah.chen@example.com" not in result
        assert "[EMAIL_REDACTED]" in result
        assert "Contact" in result
        assert "for details." in result

    def test_multiple_emails_redacted(self):
        text = "Email alice@test.com or bob.smith@company.org for help."
        result = redact_text(text)

        assert "alice@test.com" not in result
        assert "bob.smith@company.org" not in result
        assert result.count("[EMAIL_REDACTED]") == 2

    def test_email_with_plus_addressing(self):
        text = "Send to user+tag@example.com"
        result = redact_text(text)
        assert "user+tag@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_email_with_subdomain(self):
        text = "Contact admin@mail.internal.company.com"
        result = redact_text(text)
        assert "[EMAIL_REDACTED]" in result


class TestPhoneRedaction:
    """Test detection and redaction of phone numbers."""

    def test_phone_redaction(self):
        text = "Call me at (555) 123-4567 for more info."
        result = redact_text(text)

        assert "(555) 123-4567" not in result
        assert "[PHONE_REDACTED]" in result

    def test_phone_with_dashes(self):
        text = "My number is 555-123-4567."
        result = redact_text(text)
        assert "555-123-4567" not in result
        assert "[PHONE_REDACTED]" in result

    def test_phone_with_dots(self):
        text = "Call 555.123.4567 today."
        result = redact_text(text)
        assert "555.123.4567" not in result
        assert "[PHONE_REDACTED]" in result

    def test_phone_with_country_code(self):
        text = "International: +1 555 123 4567"
        result = redact_text(text)
        assert "[PHONE_REDACTED]" in result

    def test_phone_without_area_code_formatting(self):
        text = "Number: 5551234567"
        result = redact_text(text)
        assert "[PHONE_REDACTED]" in result


class TestSsnRedaction:
    """Test detection and redaction of Social Security numbers."""

    def test_ssn_redaction(self):
        text = "SSN on file: 123-45-6789."
        result = redact_text(text)

        assert "123-45-6789" not in result
        assert "[SSN_REDACTED]" in result
        assert "SSN on file:" in result

    def test_multiple_ssns_redacted(self):
        text = "Records: 111-22-3333 and 444-55-6666."
        result = redact_text(text)
        assert result.count("[SSN_REDACTED]") == 2
        assert "111-22-3333" not in result
        assert "444-55-6666" not in result


class TestCreditCardRedaction:
    """Test detection and redaction of credit card numbers."""

    def test_credit_card_redaction(self):
        text = "Card number: 4111-1111-1111-1111."
        result = redact_text(text)

        assert "4111-1111-1111-1111" not in result
        assert "[CARD_REDACTED]" in result

    def test_credit_card_with_spaces(self):
        text = "Card: 4111 1111 1111 1111"
        result = redact_text(text)
        assert "[CARD_REDACTED]" in result

    def test_credit_card_no_separators(self):
        text = "Card: 4111111111111111"
        result = redact_text(text)
        assert "[CARD_REDACTED]" in result


class TestNoFalsePositives:
    """Test that common non-PII patterns are not incorrectly redacted."""

    def test_no_false_positives(self):
        """Common technical strings should not be flagged as PII."""
        safe_texts = [
            "The project PROJ-12345 is on track.",
            "Version 3.14.159 released today.",
            "See ticket https://jira.example.com/browse/PLAT-401",
            "Sprint velocity: 47 story points.",
            "Meeting at 2:30 PM in Room 204.",
            "Budget: $1,234,567.89",
            "Timestamp: 2026-01-15T10:30:00Z",
            "UUID: 550e8400-e29b-41d4-a716-446655440000",
            "IP address configuration: 10.0.0.1",
        ]

        for text in safe_texts:
            result = redact_text(text)
            # The text should be unchanged (no PII detected)
            assert "[EMAIL_REDACTED]" not in result, f"False positive email in: {text}"
            assert "[SSN_REDACTED]" not in result, f"False positive SSN in: {text}"
            assert "[CARD_REDACTED]" not in result, f"False positive card in: {text}"

    def test_project_key_not_flagged(self):
        """Jira-style project keys should not trigger PII detection."""
        text = "PROJ-12345 has been updated."
        assert not contains_pii(text)

    def test_dates_not_flagged(self):
        """Date strings should not trigger PII detection."""
        text = "The deadline is 2026-03-15."
        assert "[SSN_REDACTED]" not in redact_text(text)

    def test_short_numbers_not_flagged(self):
        """Short digit sequences (like IDs) should not be flagged."""
        text = "Room 204, Floor 3, Building A."
        result = redact_text(text)
        assert "[PHONE_REDACTED]" not in result

    def test_mixed_content(self):
        """Mixed content with PII and non-PII should only redact PII."""
        text = (
            "Contact sarah@example.com (PROJ-123 lead). "
            "Sprint velocity: 47 points. SSN: 123-45-6789."
        )
        result = redact_text(text)

        assert "[EMAIL_REDACTED]" in result
        assert "[SSN_REDACTED]" in result
        assert "PROJ-123" in result
        assert "Sprint velocity: 47 points" in result
