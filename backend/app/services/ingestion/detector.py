"""
File type auto-detection for the ingestion pipeline.

Examines filenames, extensions, and content signatures to classify
uploaded files as Slack Admin exports, Slack API extracts, Jira CSV
exports, or generic Drive documents.
"""

from __future__ import annotations

import io
import logging
import zipfile
from enum import Enum

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Recognised file types for ingestion."""

    SLACK_ADMIN_EXPORT = "slack_admin_export"
    SLACK_API_EXTRACT = "slack_api_extract"
    JIRA_CSV = "jira_csv"
    DRIVE_DOCUMENT = "drive_document"
    UNKNOWN = "unknown"


# Jira CSV header columns used for detection.  If at least 3 of these are
# present in the first line of a CSV file, it is classified as Jira.
_JIRA_HEADER_MARKERS: set[str] = {
    "issue key",
    "issue id",
    "summary",
    "status",
    "issue type",
    "issuetype",
    "priority",
    "assignee",
    "reporter",
    "project key",
    "created",
    "updated",
    "resolution",
    "story points",
    "sprint",
    "epic link",
    "labels",
    "fix version",
    "components",
}

# Extensions that map directly to drive documents.
_DRIVE_EXTENSIONS: set[str] = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".rtf",
    ".odt",
    ".ods",
    ".odp",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
}


def detect_file_type(filename: str, file_content: bytes) -> FileType:
    """Detect the type of an uploaded file.

    Detection strategy:
    1. ZIP files are opened and inspected for Slack / API markers.
    2. CSV files have their first line checked for Jira column headers.
    3. Everything else maps to ``DRIVE_DOCUMENT`` based on extension.

    Args:
        filename: Original filename including extension.
        file_content: Raw file bytes.

    Returns:
        A ``FileType`` enum member.
    """
    lower_name = filename.lower()

    # --- ZIP inspection ---
    if lower_name.endswith(".zip"):
        return _detect_zip_type(file_content)

    # --- CSV inspection ---
    if lower_name.endswith(".csv"):
        return _detect_csv_type(file_content)

    # --- Extension-based fallback ---
    for ext in _DRIVE_EXTENSIONS:
        if lower_name.endswith(ext):
            return FileType.DRIVE_DOCUMENT

    logger.warning("Could not detect file type for '%s', falling back to DRIVE_DOCUMENT", filename)
    return FileType.DRIVE_DOCUMENT


def _detect_zip_type(content: bytes) -> FileType:
    """Inspect a ZIP archive to determine if it is a Slack export.

    Slack Admin exports contain ``users.json`` and ``channels.json``
    at the root level.  Slack API extracts contain a ``_metadata.json``
    marker file.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            names = {n.lower() for n in zf.namelist()}

            # Slack Admin Export signature
            if "users.json" in names and "channels.json" in names:
                logger.info("Detected Slack Admin Export (users.json + channels.json)")
                return FileType.SLACK_ADMIN_EXPORT

            # Slack API Extract signature
            if "_metadata.json" in names:
                logger.info("Detected Slack API Extract (_metadata.json)")
                return FileType.SLACK_API_EXTRACT

            # Check for channel-like directory structure (fallback admin detection)
            json_files = [n for n in names if n.endswith(".json")]
            dirs = {n.split("/")[0] for n in names if "/" in n}
            if json_files and dirs:
                # If there are directories with JSON files inside, likely Slack
                for d in dirs:
                    dir_jsons = [n for n in names if n.startswith(d + "/") and n.endswith(".json")]
                    if len(dir_jsons) >= 1:
                        logger.info("Detected Slack Admin Export (directory structure heuristic)")
                        return FileType.SLACK_ADMIN_EXPORT

    except zipfile.BadZipFile:
        logger.warning("File claimed to be ZIP but is not a valid archive")
        return FileType.UNKNOWN

    return FileType.DRIVE_DOCUMENT


def _detect_csv_type(content: bytes) -> FileType:
    """Check whether a CSV file contains Jira-style headers."""
    try:
        text = content.decode("utf-8-sig", errors="replace")
    except Exception:
        text = content.decode("latin-1", errors="replace")

    first_line = text.split("\n", 1)[0].strip()
    if not first_line:
        return FileType.DRIVE_DOCUMENT

    # Normalise headers: lower-case, strip quotes and whitespace
    headers = {h.strip().strip('"').strip("'").lower() for h in first_line.split(",")}

    matches = headers & _JIRA_HEADER_MARKERS
    if len(matches) >= 3:
        logger.info("Detected Jira CSV (%d matching headers: %s)", len(matches), matches)
        return FileType.JIRA_CSV

    return FileType.DRIVE_DOCUMENT
