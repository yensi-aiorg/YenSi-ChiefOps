"""
Slack API Extract ZIP parser.

Processes ZIP archives produced by Slack API data extraction tools.
These archives contain a ``_metadata.json`` marker file alongside
channel directories with message JSON files. The structure is similar
to admin exports but uses the metadata marker for identification.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.models.base import generate_uuid, utc_now
from app.services.ingestion.hasher import check_duplicate, compute_hash, record_hash
from app.services.ingestion.slack_admin import IngestionFileResult
from app.services.insights.semantic import extract_semantic_insights, generate_project_snapshot

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def parse_slack_api_extract(
    zip_path: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> IngestionFileResult:
    """Parse a Slack API extract ZIP and persist its contents.

    The API extract format uses ``_metadata.json`` as a marker file and
    may include ``users.json``, ``channels.json``, and per-channel
    message directories.

    Args:
        zip_path: Path to the ZIP file on disk.
        db: Motor database handle.

    Returns:
        An ``IngestionFileResult`` summarising what was processed.
    """
    result = IngestionFileResult(filename=zip_path, file_type="slack_api_extract")

    try:
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()
    except OSError as exc:
        result.status = "failed"
        result.errors.append(f"Cannot read file: {exc}")
        return result

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")
    except zipfile.BadZipFile as exc:
        result.status = "failed"
        result.errors.append(f"Invalid ZIP archive: {exc}")
        return result

    with zf:
        # ---- Read metadata ----
        metadata = _read_metadata(zf, result)

        # ---- Users (if present) ----
        await _process_users(zf, db, result)

        # ---- Channels (if present) ----
        await _process_channels(zf, db, result, metadata)

        # ---- Messages ----
        await _process_messages(zf, db, result, metadata)

    logger.info(
        "Slack API extract processed: %d records created, %d skipped",
        result.records_created,
        result.records_skipped,
    )
    return result


def _read_metadata(
    zf: zipfile.ZipFile,
    result: IngestionFileResult,
) -> dict[str, Any]:
    """Read and parse the _metadata.json marker file."""
    try:
        raw = zf.read("_metadata.json")
        metadata = json.loads(raw)
        if isinstance(metadata, dict):
            return metadata
    except (KeyError, json.JSONDecodeError) as exc:
        result.errors.append(f"_metadata.json parse error: {exc}")
    return {}


async def _process_users(
    zf: zipfile.ZipFile,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    result: IngestionFileResult,
) -> None:
    """Extract users from the archive if users.json exists."""
    if "users.json" not in zf.namelist():
        return

    try:
        raw = zf.read("users.json")
        users = json.loads(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        result.errors.append(f"users.json parse error: {exc}")
        return

    if not isinstance(users, list):
        return

    for user in users:
        if not isinstance(user, dict):
            continue

        user_id = user.get("id", "")
        if not user_id:
            continue

        if user.get("is_bot") or user_id == "USLACKBOT":
            result.records_skipped += 1
            continue

        profile = user.get("profile", {})
        name = (
            user.get("real_name")
            or profile.get("real_name_normalized")
            or profile.get("display_name")
            or user.get("name", "Unknown")
        )
        email = profile.get("email")
        avatar_url = profile.get("image_192") or profile.get("image_72")

        existing = await db.people.find_one({"slack_user_id": user_id})
        if existing:
            await db.people.update_one(
                {"slack_user_id": user_id},
                {
                    "$set": {
                        "name": name,
                        "email": email or existing.get("email"),
                        "avatar_url": avatar_url or existing.get("avatar_url"),
                        "updated_at": utc_now(),
                    }
                },
            )
            result.records_skipped += 1
        else:
            person_doc = {
                "person_id": generate_uuid(),
                "name": name,
                "email": email,
                "slack_user_id": user_id,
                "avatar_url": avatar_url,
                "source_ids": [{"source": "slack", "source_id": user_id}],
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
            result.records_created += 1


async def _process_channels(
    zf: zipfile.ZipFile,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    result: IngestionFileResult,
    metadata: dict[str, Any],
) -> None:
    """Extract channel info from channels.json or metadata."""
    channels_data: list[dict[str, Any]] = []

    if "channels.json" in zf.namelist():
        try:
            raw = zf.read("channels.json")
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                channels_data = parsed
        except (KeyError, json.JSONDecodeError) as exc:
            result.errors.append(f"channels.json parse error: {exc}")

    # Also check metadata for channel info
    if not channels_data and "channels" in metadata:
        meta_channels = metadata["channels"]
        if isinstance(meta_channels, list):
            channels_data = meta_channels

    for ch in channels_data:
        if not isinstance(ch, dict):
            continue

        channel_id = ch.get("id", ch.get("channel_id", ""))
        if not channel_id:
            continue

        channel_doc = {
            "channel_id": channel_id,
            "name": ch.get("name", ""),
            "purpose": ch.get("purpose", {}).get("value", "")
            if isinstance(ch.get("purpose"), dict)
            else str(ch.get("purpose", "")),
            "topic": ch.get("topic", {}).get("value", "")
            if isinstance(ch.get("topic"), dict)
            else str(ch.get("topic", "")),
            "is_archived": ch.get("is_archived", False),
            "members": ch.get("members", []),
            "num_members": len(ch.get("members", [])),
            "updated_at": utc_now(),
        }

        existing = await db.slack_channels.find_one({"channel_id": channel_id})
        if existing:
            await db.slack_channels.update_one(
                {"channel_id": channel_id},
                {"$set": channel_doc},
            )
            result.records_skipped += 1
        else:
            channel_doc["created_at"] = utc_now()
            await db.slack_channels.insert_one(channel_doc)
            result.records_created += 1


async def _process_messages(
    zf: zipfile.ZipFile,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    result: IngestionFileResult,
    metadata: dict[str, Any],
) -> None:
    """Parse message JSON files from channel directories."""
    names = zf.namelist()
    channel_messages: dict[str, list[dict[str, Any]]] = {}

    for entry_name in sorted(names):
        parts = entry_name.split("/")
        if len(parts) < 2:
            continue

        channel_name = parts[0]
        day_file = parts[-1]

        if not day_file.endswith(".json"):
            continue
        if channel_name.startswith("_") or day_file.startswith("_"):
            continue

        try:
            raw = zf.read(entry_name)
            messages = json.loads(raw)
        except (json.JSONDecodeError, KeyError) as exc:
            result.errors.append(f"Message parse error in {entry_name}: {exc}")
            continue

        if not isinstance(messages, list):
            continue

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            subtype = msg.get("subtype", "")
            if subtype in ("channel_join", "channel_leave", "channel_purpose", "channel_topic"):
                continue

            text = msg.get("text", "")
            user = msg.get("user", "")
            ts = msg.get("ts", "")

            if not text or not ts:
                continue

            try:
                ts_float = float(ts)
                timestamp = datetime.fromtimestamp(ts_float, tz=UTC)
            except (ValueError, TypeError, OSError):
                timestamp = utc_now()

            msg_doc = {
                "channel": channel_name,
                "user_id": user,
                "text": text,
                "timestamp": timestamp,
                "ts": ts,
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
                "reactions": [
                    {
                        "name": r.get("name", ""),
                        "count": r.get("count", 0),
                        "users": r.get("users", []),
                    }
                    for r in msg.get("reactions", [])
                    if isinstance(r, dict)
                ],
                "created_at": utc_now(),
            }

            existing = await db.slack_messages.find_one({"channel": channel_name, "ts": ts})
            if existing:
                result.records_skipped += 1
                continue

            await db.slack_messages.insert_one(msg_doc)
            result.records_created += 1

            if channel_name not in channel_messages:
                channel_messages[channel_name] = []
            channel_messages[channel_name].append(
                {
                    "user": user,
                    "text": text,
                    "timestamp": timestamp.isoformat(),
                }
            )

    # Build text documents for Citex indexing
    for channel_name, messages in channel_messages.items():
        if not messages:
            continue

        lines: list[str] = [f"# Slack Channel: #{channel_name}", ""]
        for msg in messages:
            lines.append(f"[{msg['timestamp']}] {msg['user']}: {msg['text']}")

        full_text = "\n".join(lines)
        content_hash = compute_hash(full_text.encode("utf-8"))

        is_dup = await check_duplicate(content_hash, db)
        if is_dup:
            continue

        doc = {
            "document_id": generate_uuid(),
            "source": "slack_api",
            "source_ref": channel_name,
            "title": f"Slack #{channel_name} messages (API extract)",
            "content": full_text,
            "content_hash": content_hash,
            "content_type": "text/plain",
            "message_count": len(messages),
            "created_at": utc_now(),
        }
        await db.text_documents.update_one(
            {"source": "slack_api", "source_ref": channel_name},
            {"$set": doc},
            upsert=True,
        )
        await extract_semantic_insights(
            project_id=None,
            source_type="slack_api",
            source_ref=channel_name,
            content=full_text,
            db=db,
        )
        await record_hash(content_hash, f"slack_api_channel_{channel_name}", db)

    await generate_project_snapshot(project_id=None, db=db, force=True)
