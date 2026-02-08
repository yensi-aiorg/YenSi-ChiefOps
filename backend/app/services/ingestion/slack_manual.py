"""
Slack Manual Export parser.

Processes manually created Slack export ZIPs (non-standard formats).
Attempts to detect and parse various manual export structures
including simple JSON message dumps and CSV exports.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.ingestion import IngestionFileResult, FileType
from app.services.ingestion.hasher import compute_hash, check_duplicate, record_hash

logger = logging.getLogger(__name__)


async def parse_slack_manual_export(
    zip_path: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> IngestionFileResult:
    """
    Parse a manually created Slack export ZIP.

    Handles non-standard exports that don't follow the official Slack
    Admin or API export format. Supports:
    - Simple JSON arrays of messages
    - JSON files with channel-keyed message arrays
    - CSV message exports
    """
    records_processed = 0
    records_skipped = 0
    messages_collection = db["slack_messages"]
    channels_collection = db["slack_channels"]

    content_hash = compute_hash(open(zip_path, "rb").read())
    if await check_duplicate(content_hash, db):
        return IngestionFileResult(
            filename=os.path.basename(zip_path),
            file_type=FileType.SLACK_MANUAL_EXPORT,
            status="skipped",
            records_processed=0,
            records_skipped=0,
            error_message="Duplicate file detected",
            content_hash=content_hash,
        )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)

            for root, _dirs, files in os.walk(tmpdir):
                for filename in files:
                    filepath = os.path.join(root, filename)

                    if filename.endswith(".json"):
                        result = await _process_json_file(
                            filepath, filename, messages_collection, channels_collection, db
                        )
                        records_processed += result["processed"]
                        records_skipped += result["skipped"]

                    elif filename.endswith(".csv"):
                        result = await _process_csv_file(
                            filepath, filename, messages_collection, db
                        )
                        records_processed += result["processed"]
                        records_skipped += result["skipped"]

        await record_hash(content_hash, os.path.basename(zip_path), db)

        return IngestionFileResult(
            filename=os.path.basename(zip_path),
            file_type=FileType.SLACK_MANUAL_EXPORT,
            status="completed",
            records_processed=records_processed,
            records_skipped=records_skipped,
            content_hash=content_hash,
        )

    except Exception as e:
        logger.error("Failed to parse manual Slack export: %s", e)
        return IngestionFileResult(
            filename=os.path.basename(zip_path),
            file_type=FileType.SLACK_MANUAL_EXPORT,
            status="failed",
            records_processed=records_processed,
            records_skipped=records_skipped,
            error_message=str(e),
            content_hash=content_hash,
        )


async def _process_json_file(
    filepath: str,
    filename: str,
    messages_collection: Any,
    channels_collection: Any,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, int]:
    """Process a JSON file that may contain Slack messages."""
    processed = 0
    skipped = 0

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Could not parse JSON file: %s", filename)
        return {"processed": 0, "skipped": 0}

    messages: list[dict[str, Any]] = []

    if isinstance(data, list):
        messages = [m for m in data if isinstance(m, dict) and "text" in m]
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                channel_messages = [
                    {**m, "_channel": key}
                    for m in value
                    if isinstance(m, dict) and "text" in m
                ]
                messages.extend(channel_messages)

    channel_name = os.path.splitext(filename)[0].replace("-", "_")

    for msg in messages:
        msg_channel = msg.pop("_channel", channel_name)
        msg_id = msg.get("ts", msg.get("timestamp", ""))
        if not msg_id:
            skipped += 1
            continue

        doc = {
            "message_id": f"{msg_channel}_{msg_id}",
            "channel": msg_channel,
            "user_id": msg.get("user", msg.get("user_id", "unknown")),
            "user_name": msg.get("user_name", msg.get("username", "")),
            "text": msg.get("text", ""),
            "timestamp": _parse_timestamp(msg.get("ts", msg.get("timestamp", ""))),
            "thread_ts": msg.get("thread_ts"),
            "reactions": msg.get("reactions", []),
            "reply_count": msg.get("reply_count", 0),
            "source": "slack_manual_export",
        }

        try:
            await messages_collection.update_one(
                {"message_id": doc["message_id"]},
                {"$set": doc},
                upsert=True,
            )
            processed += 1
        except Exception:
            skipped += 1

    if messages:
        await channels_collection.update_one(
            {"channel_id": channel_name},
            {
                "$set": {
                    "channel_id": channel_name,
                    "name": channel_name,
                    "purpose": f"Imported from manual export: {filename}",
                    "message_count": len(messages),
                    "updated_at": datetime.now(tz=timezone.utc),
                },
                "$setOnInsert": {
                    "created_at": datetime.now(tz=timezone.utc),
                    "members": [],
                },
            },
            upsert=True,
        )

    return {"processed": processed, "skipped": skipped}


async def _process_csv_file(
    filepath: str,
    filename: str,
    messages_collection: Any,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, int]:
    """Process a CSV file that may contain Slack messages."""
    import csv

    processed = 0
    skipped = 0
    channel_name = os.path.splitext(filename)[0].replace("-", "_")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return {"processed": 0, "skipped": 0}

            text_field = None
            for candidate in ["text", "message", "content", "body"]:
                if candidate in reader.fieldnames:
                    text_field = candidate
                    break

            if text_field is None:
                return {"processed": 0, "skipped": 0}

            for row in reader:
                text = row.get(text_field, "").strip()
                if not text:
                    skipped += 1
                    continue

                ts = row.get("ts", row.get("timestamp", row.get("date", "")))
                user = row.get("user", row.get("user_id", row.get("username", "unknown")))

                doc = {
                    "message_id": f"{channel_name}_{ts or processed}",
                    "channel": channel_name,
                    "user_id": user,
                    "user_name": row.get("user_name", row.get("username", "")),
                    "text": text,
                    "timestamp": _parse_timestamp(ts) if ts else datetime.now(tz=timezone.utc),
                    "thread_ts": row.get("thread_ts"),
                    "reactions": [],
                    "reply_count": 0,
                    "source": "slack_manual_export",
                }

                try:
                    await messages_collection.update_one(
                        {"message_id": doc["message_id"]},
                        {"$set": doc},
                        upsert=True,
                    )
                    processed += 1
                except Exception:
                    skipped += 1

    except Exception as e:
        logger.warning("Failed to parse CSV file %s: %s", filename, e)

    return {"processed": processed, "skipped": skipped}


def _parse_timestamp(ts_value: str) -> datetime:
    """Parse a Slack timestamp into a datetime object."""
    if not ts_value:
        return datetime.now(tz=timezone.utc)

    try:
        ts_float = float(ts_value.split(".")[0])
        return datetime.fromtimestamp(ts_float, tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(ts_value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return datetime.now(tz=timezone.utc)
