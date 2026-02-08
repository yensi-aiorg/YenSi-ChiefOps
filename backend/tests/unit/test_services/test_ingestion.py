"""
Unit tests for the ingestion pipeline services.

Tests file type detection, content hashing, duplicate detection,
and CSV parsing without requiring external dependencies.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile

import pytest

from app.services.ingestion.detector import FileType, detect_file_type
from app.services.ingestion.hasher import compute_hash


class TestDetectSlackAdminExport:
    """Test detection of Slack Admin export ZIP files."""

    def test_detect_slack_admin_export(self):
        """A ZIP containing users.json and channels.json is a Slack Admin export."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("users.json", json.dumps([
                {"id": "U01", "name": "alice", "real_name": "Alice Johnson"},
                {"id": "U02", "name": "bob", "real_name": "Bob Smith"},
            ]))
            zf.writestr("channels.json", json.dumps([
                {"id": "C01", "name": "general", "members": ["U01", "U02"]},
            ]))
            zf.writestr("general/2026-01-01.json", json.dumps([
                {"user": "U01", "text": "Hello world", "ts": "1706000000.000000"},
            ]))

        result = detect_file_type("workspace_export.zip", buf.getvalue())
        assert result == FileType.SLACK_ADMIN_EXPORT

    def test_detect_slack_admin_export_case_insensitive(self):
        """Detection should be case-insensitive for the filename."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("users.json", "[]")
            zf.writestr("channels.json", "[]")

        result = detect_file_type("EXPORT.ZIP", buf.getvalue())
        assert result == FileType.SLACK_ADMIN_EXPORT

    def test_zip_without_markers_is_drive_document(self):
        """A ZIP without Slack markers defaults to DRIVE_DOCUMENT."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "Just a normal archive.")
            zf.writestr("data/file.csv", "a,b,c\n1,2,3")

        result = detect_file_type("archive.zip", buf.getvalue())
        assert result == FileType.DRIVE_DOCUMENT

    def test_invalid_zip_returns_unknown(self):
        """Non-ZIP content with .zip extension returns UNKNOWN."""
        result = detect_file_type("fake.zip", b"this is not a zip file")
        assert result == FileType.UNKNOWN


class TestDetectJiraCsv:
    """Test detection of Jira CSV export files."""

    def test_detect_jira_csv(self):
        """A CSV with standard Jira headers is classified as JIRA_CSV."""
        headers = ["Issue Key", "Summary", "Status", "Priority", "Assignee", "Reporter"]
        rows = [
            ["PROJ-1", "Fix login bug", "In Progress", "High", "Alice", "Bob"],
            ["PROJ-2", "Add dark mode", "To Do", "Medium", "Charlie", "Alice"],
        ]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        writer.writerows(rows)
        content = buf.getvalue().encode("utf-8")

        result = detect_file_type("jira_export.csv", content)
        assert result == FileType.JIRA_CSV

    def test_jira_csv_with_quoted_headers(self):
        """Jira headers wrapped in quotes should still be detected."""
        line = '"Issue Key","Issue ID","Summary","Status","Issue Type","Priority"\n'
        line += '"PROJ-1","10001","Fix bug","Done","Bug","High"\n'
        content = line.encode("utf-8")

        result = detect_file_type("export.csv", content)
        assert result == FileType.JIRA_CSV

    def test_non_jira_csv_is_drive_document(self):
        """A CSV without Jira headers is classified as DRIVE_DOCUMENT."""
        content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n".encode("utf-8")

        result = detect_file_type("people.csv", content)
        assert result == FileType.DRIVE_DOCUMENT


class TestDetectDriveDocument:
    """Test detection of Google Drive document types."""

    def test_detect_drive_document(self):
        """Common document extensions should be classified as DRIVE_DOCUMENT."""
        extensions = [".pdf", ".docx", ".xlsx", ".txt", ".md", ".html", ".pptx"]

        for ext in extensions:
            result = detect_file_type(f"document{ext}", b"file content here")
            assert result == FileType.DRIVE_DOCUMENT, f"Failed for extension {ext}"

    def test_json_file_is_drive_document(self):
        """A standalone JSON file (not in a ZIP) is a DRIVE_DOCUMENT."""
        content = json.dumps({"key": "value"}).encode("utf-8")
        result = detect_file_type("config.json", content)
        assert result == FileType.DRIVE_DOCUMENT

    def test_unknown_extension_defaults_to_drive(self):
        """Files with unrecognized extensions default to DRIVE_DOCUMENT."""
        result = detect_file_type("mystery.xyz", b"some content")
        assert result == FileType.DRIVE_DOCUMENT


class TestContentHashComputation:
    """Test SHA-256 content hash computation."""

    def test_content_hash_computation(self):
        """compute_hash produces a valid SHA-256 hex digest."""
        content = b"Hello, ChiefOps!"
        expected = hashlib.sha256(content).hexdigest()

        result = compute_hash(content)

        assert result == expected
        assert len(result) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_deterministic(self):
        """Same content produces the same hash."""
        content = b"deterministic content"
        hash1 = compute_hash(content)
        hash2 = compute_hash(content)
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content produces different hashes."""
        hash1 = compute_hash(b"content A")
        hash2 = compute_hash(b"content B")
        assert hash1 != hash2

    def test_empty_content_hash(self):
        """Empty bytes still produce a valid hash."""
        result = compute_hash(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected


class TestDuplicateDetection:
    """Test duplicate detection via content hashing."""

    async def test_duplicate_detection(self, test_db):
        """Recording a hash and then checking it should detect the duplicate."""
        from app.services.ingestion.hasher import check_duplicate, record_hash

        content = b"unique document content for duplicate test"
        content_hash = compute_hash(content)

        # Should not be a duplicate initially
        is_dup = await check_duplicate(content_hash, test_db)
        assert is_dup is False

        # Record the hash
        await record_hash(content_hash, "test_file.pdf", test_db)

        # Now it should be detected as a duplicate
        is_dup = await check_duplicate(content_hash, test_db)
        assert is_dup is True

    async def test_different_content_not_duplicate(self, test_db):
        """Different content should not be flagged as duplicate."""
        from app.services.ingestion.hasher import check_duplicate, record_hash

        hash1 = compute_hash(b"first document")
        hash2 = compute_hash(b"second document")

        await record_hash(hash1, "first.pdf", test_db)

        is_dup = await check_duplicate(hash2, test_db)
        assert is_dup is False


class TestJiraCsvParsing:
    """Test parsing of Jira CSV data into structured records."""

    def test_jira_csv_parsing(self):
        """Parse a mock Jira CSV and validate extracted fields."""
        csv_content = (
            "Issue Key,Summary,Status,Priority,Assignee,Reporter,Created,Story Points\n"
            'PROJ-101,"Implement login flow",In Progress,High,Alice,Bob,2026-01-15,5\n'
            'PROJ-102,"Fix search bug",Done,Medium,Charlie,Alice,2026-01-16,3\n'
            'PROJ-103,"Add export feature",To Do,Low,,"Bob",2026-01-17,8\n'
        )

        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 3

        # First row
        assert rows[0]["Issue Key"] == "PROJ-101"
        assert rows[0]["Summary"] == "Implement login flow"
        assert rows[0]["Status"] == "In Progress"
        assert rows[0]["Priority"] == "High"
        assert rows[0]["Assignee"] == "Alice"
        assert rows[0]["Reporter"] == "Bob"
        assert rows[0]["Story Points"] == "5"

        # Second row
        assert rows[1]["Issue Key"] == "PROJ-102"
        assert rows[1]["Status"] == "Done"

        # Third row -- unassigned task
        assert rows[2]["Issue Key"] == "PROJ-103"
        assert rows[2]["Assignee"] == ""
        assert rows[2]["Story Points"] == "8"

    def test_jira_csv_with_extra_columns(self):
        """CSV with additional non-standard columns should still parse."""
        csv_content = (
            "Issue Key,Summary,Status,Custom Field,Priority\n"
            "PROJ-201,Task A,Open,custom_value,High\n"
        )

        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["Issue Key"] == "PROJ-201"
        assert rows[0]["Custom Field"] == "custom_value"
