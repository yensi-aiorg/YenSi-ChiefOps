"""
Jira CSV export parser.

Handles both "All fields" and "Current fields" CSV export variants
from Jira. Automatically detects column positions from header names,
parses dates and story points, and stores tasks in the ``jira_tasks``
collection. Also builds text documents for Citex RAG indexing.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now
from app.services.ingestion.hasher import check_duplicate, compute_hash, record_hash
from app.services.ingestion.slack_admin import IngestionFileResult

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Canonical Jira status mappings to normalised categories
_STATUS_MAP: dict[str, str] = {
    "to do": "to_do",
    "open": "to_do",
    "new": "to_do",
    "backlog": "to_do",
    "selected for development": "to_do",
    "in progress": "in_progress",
    "in development": "in_progress",
    "in review": "in_progress",
    "code review": "in_progress",
    "in testing": "in_progress",
    "in qa": "in_progress",
    "done": "done",
    "closed": "done",
    "resolved": "done",
    "complete": "done",
    "completed": "done",
    "blocked": "blocked",
    "impediment": "blocked",
    "on hold": "blocked",
}

# Header name normalisation for flexible column detection
_HEADER_ALIASES: dict[str, list[str]] = {
    "issue_key": ["issue key", "key"],
    "issue_id": ["issue id"],
    "summary": ["summary", "title"],
    "status": ["status"],
    "issue_type": ["issue type", "issuetype", "type"],
    "priority": ["priority"],
    "assignee": ["assignee"],
    "reporter": ["reporter"],
    "project_key": ["project key", "project"],
    "project_name": ["project name"],
    "created": ["created", "date created"],
    "updated": ["updated", "date updated"],
    "resolved": ["resolved", "resolution date", "date resolved"],
    "due_date": ["due date", "due"],
    "description": ["description"],
    "story_points": ["story points", "story point estimate", "custom field (story points)"],
    "sprint": ["sprint"],
    "epic_link": ["epic link", "epic name", "epic"],
    "epic_name": ["epic name"],
    "labels": ["labels", "label"],
    "components": ["components", "component"],
    "fix_versions": ["fix version/s", "fix version", "fix versions"],
    "resolution": ["resolution"],
    "parent": ["parent", "parent id"],
    "subtasks": ["sub-tasks", "subtasks"],
    "time_spent": ["time spent", "time spent (seconds)"],
    "original_estimate": ["original estimate", "original estimate (seconds)"],
    "comments": ["comment", "comments"],
}


async def parse_jira_csv(
    file_path: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> IngestionFileResult:
    """Parse a Jira CSV export and persist tasks to MongoDB.

    Args:
        file_path: Path to the CSV file on disk.
        db: Motor database handle.

    Returns:
        An ``IngestionFileResult`` summarising what was processed.
    """
    result = IngestionFileResult(filename=file_path, file_type="jira_csv")

    try:
        with open(file_path, encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
    except OSError as exc:
        result.status = "failed"
        result.errors.append(f"Cannot read file: {exc}")
        return result

    reader = csv.reader(io.StringIO(content))

    try:
        raw_headers = next(reader)
    except StopIteration:
        result.status = "failed"
        result.errors.append("CSV file is empty")
        return result

    # Build column index mapping
    col_map = _build_column_map(raw_headers)
    if "issue_key" not in col_map and "summary" not in col_map:
        result.status = "failed"
        result.errors.append("CSV does not contain recognizable Jira columns")
        return result

    # Track unique project keys for text document building
    project_tasks: dict[str, list[dict[str, Any]]] = {}
    row_number = 1

    for row in reader:
        row_number += 1
        try:
            task = _parse_row(row, col_map, row_number, result)
            if task is None:
                continue

            task_key = task.get("task_key", "")

            # Upsert by task key
            if task_key:
                existing = await db.jira_tasks.find_one({"task_key": task_key})
                if existing:
                    await db.jira_tasks.update_one(
                        {"task_key": task_key},
                        {"$set": {**task, "updated_at": utc_now()}},
                    )
                    result.records_skipped += 1
                else:
                    task["created_at"] = utc_now()
                    task["updated_at"] = utc_now()
                    await db.jira_tasks.insert_one(task)
                    result.records_created += 1
            else:
                task["task_key"] = f"UNKNOWN-{generate_uuid()[:8]}"
                task["created_at"] = utc_now()
                task["updated_at"] = utc_now()
                await db.jira_tasks.insert_one(task)
                result.records_created += 1

            # Collect for text document building
            project_key = task.get("project_key", "UNKNOWN")
            if project_key not in project_tasks:
                project_tasks[project_key] = []
            project_tasks[project_key].append(task)

            # Create person records for assignees/reporters
            await _ensure_person_exists(task.get("assignee"), "jira", db)
            await _ensure_person_exists(task.get("reporter"), "jira", db)

        except Exception as exc:
            result.errors.append(f"Row {row_number}: {exc}")

    # Build text documents for Citex indexing
    await _build_text_documents(project_tasks, db)

    logger.info(
        "Jira CSV processed: %d created, %d skipped, %d errors",
        result.records_created,
        result.records_skipped,
        len(result.errors),
    )
    return result


def _build_column_map(raw_headers: list[str]) -> dict[str, int]:
    """Map canonical field names to column indices."""
    col_map: dict[str, int] = {}
    normalised = [h.strip().strip('"').strip("'").lower() for h in raw_headers]

    for canonical, aliases in _HEADER_ALIASES.items():
        for i, header in enumerate(normalised):
            if header in aliases:
                col_map[canonical] = i
                break

    return col_map


def _get_cell(row: list[str], col_map: dict[str, int], field: str) -> str:
    """Safely retrieve a cell value from a row."""
    idx = col_map.get(field)
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def _parse_date(value: str) -> datetime | None:
    """Parse various Jira date formats into a UTC datetime."""
    if not value:
        return None

    # Common Jira date formats
    formats = [
        "%d/%b/%y %I:%M %p",
        "%d/%b/%Y %I:%M %p",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            continue

    return None


def _parse_story_points(value: str) -> float | None:
    """Parse story points, handling empty strings and various formats."""
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _normalise_status(raw_status: str) -> str:
    """Map a raw Jira status string to a normalised category."""
    lower = raw_status.strip().lower()
    return _STATUS_MAP.get(lower, lower.replace(" ", "_"))


def _parse_row(
    row: list[str],
    col_map: dict[str, int],
    row_number: int,
    result: IngestionFileResult,
) -> dict[str, Any] | None:
    """Parse a single CSV row into a Jira task document."""
    issue_key = _get_cell(row, col_map, "issue_key")
    summary = _get_cell(row, col_map, "summary")

    if not summary and not issue_key:
        result.records_skipped += 1
        return None

    # Derive project key from issue key (e.g., "PROJ-123" -> "PROJ")
    project_key = ""
    if issue_key and "-" in issue_key:
        project_key = issue_key.rsplit("-", 1)[0]
    if not project_key:
        project_key = _get_cell(row, col_map, "project_key")

    raw_status = _get_cell(row, col_map, "status")
    status = _normalise_status(raw_status) if raw_status else "to_do"

    # Parse labels and components from semicolon or comma separated values
    raw_labels = _get_cell(row, col_map, "labels")
    labels = (
        [l.strip() for l in raw_labels.replace(";", ",").split(",") if l.strip()]
        if raw_labels
        else []
    )

    raw_components = _get_cell(row, col_map, "components")
    components = (
        [c.strip() for c in raw_components.replace(";", ",").split(",") if c.strip()]
        if raw_components
        else []
    )

    raw_fix_versions = _get_cell(row, col_map, "fix_versions")
    fix_versions = (
        [v.strip() for v in raw_fix_versions.replace(";", ",").split(",") if v.strip()]
        if raw_fix_versions
        else []
    )

    return {
        "task_key": issue_key,
        "issue_id": _get_cell(row, col_map, "issue_id"),
        "summary": summary,
        "description": _get_cell(row, col_map, "description"),
        "status": status,
        "status_raw": raw_status,
        "issue_type": _get_cell(row, col_map, "issue_type"),
        "priority": _get_cell(row, col_map, "priority"),
        "assignee": _get_cell(row, col_map, "assignee"),
        "reporter": _get_cell(row, col_map, "reporter"),
        "project_key": project_key,
        "project_name": _get_cell(row, col_map, "project_name"),
        "created_date": _parse_date(_get_cell(row, col_map, "created")),
        "updated_date": _parse_date(_get_cell(row, col_map, "updated")),
        "resolved_date": _parse_date(_get_cell(row, col_map, "resolved")),
        "due_date": _parse_date(_get_cell(row, col_map, "due_date")),
        "story_points": _parse_story_points(_get_cell(row, col_map, "story_points")),
        "sprint": _get_cell(row, col_map, "sprint"),
        "epic_link": _get_cell(row, col_map, "epic_link"),
        "epic_name": _get_cell(row, col_map, "epic_name"),
        "labels": labels,
        "components": components,
        "fix_versions": fix_versions,
        "resolution": _get_cell(row, col_map, "resolution"),
        "parent": _get_cell(row, col_map, "parent"),
    }


async def _ensure_person_exists(
    name: str | None,
    source: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Ensure a person record exists for the given name."""
    if not name or not name.strip():
        return

    name = name.strip()

    # Check if person already exists by jira_username or name
    existing = await db.people.find_one(
        {
            "$or": [
                {"jira_username": name},
                {"name": name},
            ]
        }
    )
    if existing:
        # Ensure jira source_id is present
        source_ids = existing.get("source_ids", [])
        has_jira = any(s.get("source") == "jira" for s in source_ids)
        if not has_jira:
            await db.people.update_one(
                {"_id": existing["_id"]},
                {
                    "$push": {"source_ids": {"source": "jira", "source_id": name}},
                    "$set": {"jira_username": name, "updated_at": utc_now()},
                },
            )
        return

    person_doc = {
        "person_id": generate_uuid(),
        "name": name,
        "email": None,
        "jira_username": name,
        "slack_user_id": None,
        "avatar_url": None,
        "source_ids": [{"source": "jira", "source_id": name}],
        "role": "team_member",
        "role_source": "ai_identified",
        "activity_level": "moderate",
        "engagement_metrics": {
            "messages_sent": 0,
            "threads_replied": 0,
            "reactions_given": 0,
        },
        "tasks_assigned": 0,
        "tasks_completed": 0,
        "projects": [],
        "last_active_date": utc_now(),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    await db.people.insert_one(person_doc)


async def _build_text_documents(
    project_tasks: dict[str, list[dict[str, Any]]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Build concatenated text documents per Jira project for Citex indexing."""
    for project_key, tasks in project_tasks.items():
        if not tasks:
            continue

        lines: list[str] = [f"# Jira Project: {project_key}", ""]
        for task in tasks:
            status = task.get("status", "unknown")
            assignee = task.get("assignee", "Unassigned")
            summary = task.get("summary", "")
            description = task.get("description", "")
            points = task.get("story_points")
            task_key = task.get("task_key", "")

            line = f"[{task_key}] ({status}) {summary}"
            if assignee:
                line += f" | Assignee: {assignee}"
            if points is not None:
                line += f" | Points: {points}"
            lines.append(line)

            if description:
                # Truncate long descriptions for the text document
                desc_preview = description[:500].replace("\n", " ")
                lines.append(f"  Description: {desc_preview}")
            lines.append("")

        full_text = "\n".join(lines)
        content_hash = compute_hash(full_text.encode("utf-8"))

        is_dup = await check_duplicate(content_hash, db)
        if is_dup:
            continue

        doc = {
            "document_id": generate_uuid(),
            "source": "jira",
            "source_ref": project_key,
            "title": f"Jira Project {project_key} tasks",
            "content": full_text,
            "content_hash": content_hash,
            "content_type": "text/plain",
            "task_count": len(tasks),
            "created_at": utc_now(),
        }
        await db.text_documents.update_one(
            {"source": "jira", "source_ref": project_key},
            {"$set": doc},
            upsert=True,
        )
        await record_hash(content_hash, f"jira_project_{project_key}", db)
