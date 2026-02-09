"""
Per-project file upload processing.

Handles files uploaded to a specific project: Slack JSON exports, Jira XLSX
spreadsheets, and general documentation (PDF, DOCX, MD, TXT). Each file
produces a ``text_documents`` entry tagged with ``project_id`` and is
optionally ingested into Citex for RAG retrieval.
"""

from __future__ import annotations

import io
import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.citex.client import CitexClient
from app.config import get_settings
from app.models.base import generate_uuid, utc_now
from app.services.ingestion.drive import (
    _extract_docx_text,
    _extract_pdf_text,
    _extract_plain_text,
    _get_content_type,
)
from app.services.ingestion.hasher import compute_hash

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Supported extensions for per-project upload
ALLOWED_EXTENSIONS: set[str] = {".json", ".xlsx", ".pdf", ".docx", ".md", ".txt"}

_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def process_project_file(
    project_id: str,
    filename: str,
    content: bytes,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Process a single file uploaded to a project.

    Detects file category by extension, extracts text, stores metadata in
    ``project_files``, creates/upserts a ``text_documents`` entry with
    ``project_id``, and attempts Citex ingestion.

    Returns:
        A result dict with keys: file_id, filename, file_type, status,
        records_created, citex_ingested, error_message.
    """
    ext = Path(filename).suffix.lower()
    file_type = _detect_file_type(ext)
    content_hash = compute_hash(content)
    file_id = generate_uuid()
    now = utc_now()

    result: dict[str, Any] = {
        "file_id": file_id,
        "filename": filename,
        "file_type": file_type,
        "status": "completed",
        "records_created": 0,
        "citex_ingested": False,
        "error_message": None,
    }

    # Check duplicate within this project
    existing = await db.project_files.find_one(
        {"project_id": project_id, "content_hash": content_hash}
    )
    if existing:
        result["status"] = "skipped"
        result["error_message"] = "Duplicate file (same content already uploaded to this project)"
        result["file_id"] = existing["file_id"]
        return result

    try:
        # Dispatch to category-specific processor
        if file_type == "slack_json":
            text_content, records = await _process_slack_json(
                project_id, filename, content, db
            )
        elif file_type == "jira_xlsx":
            text_content, records = await _process_jira_xlsx(
                project_id, filename, content, db
            )
        else:
            text_content, records = await _process_documentation(
                project_id, filename, content, ext
            )

        result["records_created"] = records

        # Store text document if we extracted text
        text_document_id = None
        if text_content and text_content.strip():
            text_document_id = await _store_text_document(
                project_id=project_id,
                source=file_type,
                source_ref=filename,
                title=filename,
                content=text_content,
                db=db,
            )

        # Attempt Citex ingestion
        if text_content and text_content.strip():
            result["citex_ingested"] = await _ingest_to_citex(
                project_id=project_id,
                content=text_content,
                filename=filename,
                source=file_type,
            )

        # Store file metadata
        file_doc: dict[str, Any] = {
            "file_id": file_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": file_type,
            "content_type": _get_content_type(ext),
            "file_size": len(content),
            "content_hash": content_hash,
            "status": "completed",
            "records_created": records,
            "text_document_id": text_document_id,
            "citex_ingested": result["citex_ingested"],
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        await db.project_files.insert_one(file_doc)

    except Exception as exc:
        logger.exception("Failed to process project file %s: %s", filename, exc)
        result["status"] = "failed"
        result["error_message"] = str(exc)

        # Still store the file metadata with failed status
        file_doc = {
            "file_id": file_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": file_type,
            "content_type": _get_content_type(ext),
            "file_size": len(content),
            "content_hash": content_hash,
            "status": "failed",
            "records_created": 0,
            "text_document_id": None,
            "citex_ingested": False,
            "error_message": str(exc),
            "created_at": now,
            "updated_at": now,
        }
        await db.project_files.insert_one(file_doc)

    return result


# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------


def _detect_file_type(ext: str) -> str:
    """Map file extension to a processing category."""
    if ext == ".json":
        return "slack_json"
    if ext == ".xlsx":
        return "jira_xlsx"
    return "documentation"


# ---------------------------------------------------------------------------
# Category-specific processors
# ---------------------------------------------------------------------------


async def _process_slack_json(
    project_id: str,
    filename: str,
    content: bytes,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> tuple[str, int]:
    """Parse a Slack JSON export and build a concatenated text document.

    Returns:
        Tuple of (extracted_text, records_created).
    """
    text = content.decode("utf-8")
    data = json.loads(text)

    if not isinstance(data, list):
        # Might be a single-object export; wrap it
        data = [data]

    lines: list[str] = []
    msg_count = 0
    for msg in data:
        if not isinstance(msg, dict):
            continue
        user = msg.get("user") or msg.get("username") or "unknown"
        ts = msg.get("ts") or msg.get("timestamp") or ""
        msg_text = msg.get("text", "")
        if msg_text:
            lines.append(f"[{ts}] {user}: {msg_text}")
            msg_count += 1

    full_text = "\n".join(lines)
    return full_text, msg_count


async def _process_jira_xlsx(
    project_id: str,
    filename: str,
    content: bytes,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> tuple[str, int]:
    """Parse a Jira XLSX export using openpyxl.

    Reuses column detection and row parsing from jira_csv.py where possible.
    Builds a text document and upserts tasks into jira_tasks.

    Returns:
        Tuple of (extracted_text, records_created).
    """
    from openpyxl import load_workbook

    from app.services.ingestion.jira_csv import (
        _build_column_map,
        _normalise_status,
        _parse_date,
        _parse_row,
        _parse_story_points,
    )

    wb = load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return "", 0

    # Read all rows as lists of strings
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])
    wb.close()

    if len(rows) < 2:
        return "", 0

    # First row is the header
    header = rows[0]
    col_map = _build_column_map(header)

    records_created = 0
    text_lines: list[str] = []
    now = utc_now()

    # _parse_row expects an IngestionFileResult-like object for skip tracking
    from app.services.ingestion.slack_admin import IngestionFileResult

    result = IngestionFileResult(filename=filename, file_type="jira")

    for row_number, row_values in enumerate(rows[1:], start=2):
        if not any(v.strip() for v in row_values):
            continue

        parsed = _parse_row(row_values, col_map, row_number, result)
        if not parsed:
            continue

        task_key = parsed.get("task_key", "")
        if not task_key:
            continue

        # Build task doc following jira_csv pattern
        task_doc: dict[str, Any] = {
            "task_key": task_key,
            "project_key": parsed.get("project_key", task_key.split("-")[0] if "-" in task_key else ""),
            "summary": parsed.get("summary", ""),
            "status": _normalise_status(parsed.get("status", "")),
            "priority": parsed.get("priority", ""),
            "assignee": parsed.get("assignee", ""),
            "reporter": parsed.get("reporter", ""),
            "issue_type": parsed.get("issue_type", ""),
            "story_points": _parse_story_points(parsed.get("story_points", "")),
            "created_date": _parse_date(parsed.get("created", "")),
            "updated_date": _parse_date(parsed.get("updated", "")),
            "due_date": _parse_date(parsed.get("due_date", "")),
            "resolution_date": _parse_date(parsed.get("resolution_date", "")),
            "labels": [l.strip() for l in parsed.get("labels", "").split(",") if l.strip()],
            "components": [c.strip() for c in parsed.get("components", "").split(",") if c.strip()],
            "sprint": parsed.get("sprint", ""),
            "source_project_id": project_id,
            "updated_at": now,
        }

        await db.jira_tasks.update_one(
            {"task_key": task_key},
            {"$set": task_doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        records_created += 1

        # Build text line for the text document
        text_lines.append(
            f"{task_key}: [{task_doc['status']}] {task_doc['summary']} "
            f"(assignee={task_doc['assignee']}, priority={task_doc['priority']})"
        )

    full_text = "\n".join(text_lines)
    return full_text, records_created


async def _process_documentation(
    project_id: str,
    filename: str,
    content: bytes,
    ext: str,
) -> tuple[str, int]:
    """Extract text from a documentation file (PDF, DOCX, MD, TXT).

    Returns:
        Tuple of (extracted_text, records_created). records_created is always
        1 if text was extracted, 0 otherwise.
    """

    class _ErrorCollector:
        """Minimal stand-in for IngestionFileResult to capture extraction errors."""
        errors: list[str] = []

    errors = _ErrorCollector()
    errors.errors = []

    extracted: str | None = None

    if ext in _TEXT_EXTENSIONS:
        extracted = _extract_plain_text(content)
    elif ext == ".pdf":
        extracted = _extract_pdf_text(content, errors)  # type: ignore[arg-type]
    elif ext == ".docx":
        # python-docx needs a file path, write to temp
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            extracted = _extract_docx_text(tmp_path, errors)  # type: ignore[arg-type]
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        # Fallback: try plain text decoding
        extracted = _extract_plain_text(content)

    if errors.errors:
        logger.warning("Extraction warnings for %s: %s", filename, errors.errors)

    if extracted and extracted.strip():
        return extracted, 1
    return "", 0


# ---------------------------------------------------------------------------
# Text document storage
# ---------------------------------------------------------------------------


async def _store_text_document(
    project_id: str,
    source: str,
    source_ref: str,
    title: str,
    content: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Upsert a text_documents entry tagged with project_id.

    Returns:
        The document_id of the created/updated text document.
    """
    content_hash = compute_hash(content.encode("utf-8"))
    document_id = generate_uuid()
    now = utc_now()

    doc: dict[str, Any] = {
        "document_id": document_id,
        "project_id": project_id,
        "source": source,
        "source_ref": source_ref,
        "title": title,
        "content": content,
        "content_hash": content_hash,
        "content_type": "text/plain",
        "created_at": now,
        "updated_at": now,
    }

    # Upsert by project_id + source + source_ref to avoid duplicates on re-upload
    result = await db.text_documents.update_one(
        {"project_id": project_id, "source": source, "source_ref": source_ref},
        {"$set": doc},
        upsert=True,
    )

    # If it was an update, retrieve the existing document_id
    if not result.upserted_id:
        existing = await db.text_documents.find_one(
            {"project_id": project_id, "source": source, "source_ref": source_ref},
            {"document_id": 1},
        )
        if existing:
            document_id = existing["document_id"]

    return document_id


# ---------------------------------------------------------------------------
# Citex ingestion
# ---------------------------------------------------------------------------


async def _ingest_to_citex(
    project_id: str,
    content: str,
    filename: str,
    source: str,
) -> bool:
    """Attempt to ingest content into Citex. Returns True on success."""
    settings = get_settings()
    client = CitexClient(
        settings.CITEX_API_URL,
        api_key=settings.CITEX_API_KEY,
        user_id=settings.CITEX_USER_ID,
        scope_id=f"project:{project_id}",
    )

    try:
        if not await client.ping():
            logger.debug("Citex unavailable; skipping ingestion for %s", filename)
            return False

        metadata = {
            "source": source,
            "source_ref": filename,
            "upload_type": "project_file",
        }
        response = await client.ingest_document(
            project_id=project_id,
            content=content,
            metadata=metadata,
            filename=filename,
        )
        return bool(response)

    except Exception as exc:
        logger.warning("Citex ingestion failed for %s: %s", filename, exc)
        return False
    finally:
        await client.close()
