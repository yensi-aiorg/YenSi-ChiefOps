"""
Slack Admin Export ZIP parser.

Processes the standard Slack workspace export format:
- ``users.json`` -- workspace member directory
- ``channels.json`` -- channel metadata
- ``<channel_name>/YYYY-MM-DD.json`` -- daily message archives

Creates person records from user profiles, channel records, and stores
every message in the ``slack_messages`` collection.  Also builds
concatenated text documents for Citex RAG indexing.
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
from app.services.insights.semantic import extract_semantic_insights, generate_project_snapshot

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class IngestionFileResult:
    """Outcome of processing a single file during ingestion."""

    __slots__ = (
        "errors",
        "file_type",
        "filename",
        "records_created",
        "records_skipped",
        "status",
    )

    def __init__(self, filename: str, file_type: str) -> None:
        self.filename = filename
        self.file_type = file_type
        self.status: str = "completed"
        self.records_created: int = 0
        self.records_skipped: int = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "file_type": self.file_type,
            "status": self.status,
            "records_created": self.records_created,
            "records_skipped": self.records_skipped,
            "errors": self.errors,
        }


async def parse_slack_admin_export(
    zip_path: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> IngestionFileResult:
    """Parse a Slack Admin Export ZIP and persist its contents.

    Args:
        zip_path: Path to the ZIP file on disk.
        db: Motor database handle.

    Returns:
        An ``IngestionFileResult`` summarising what was processed.
    """
    result = IngestionFileResult(filename=zip_path, file_type="slack_admin_export")

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
        # ---- Users ----
        users_created = await _process_users(zf, db, result)

        # ---- Channels ----
        channels_created = await _process_channels(zf, db, result)

        # ---- Messages per channel/day ----
        await _process_messages(zf, db, result)

    logger.info(
        "Slack admin export processed: %d users, %d channels, %d records total",
        users_created,
        channels_created,
        result.records_created,
    )
    return result


async def _process_users(
    zf: zipfile.ZipFile,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    result: IngestionFileResult,
) -> int:
    """Extract users.json and upsert person records."""
    created = 0
    try:
        raw = zf.read("users.json")
        users = json.loads(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        result.errors.append(f"users.json parse error: {exc}")
        return 0

    for user in users:
        if not isinstance(user, dict):
            continue

        user_id: str = user.get("id", "")
        if not user_id:
            continue

        # Skip bots and Slackbot
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
        avatar_url = profile.get("image_192") or profile.get("image_72") or profile.get("image_48")

        person_doc = {
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
            "updated_at": utc_now(),
        }

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
            person_doc["person_id"] = generate_uuid()
            person_doc["created_at"] = utc_now()
            person_doc["last_active_date"] = utc_now()
            await db.people.insert_one(person_doc)
            created += 1
            result.records_created += 1

    return created


async def _process_channels(
    zf: zipfile.ZipFile,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    result: IngestionFileResult,
) -> int:
    """Extract channels.json and upsert channel records."""
    created = 0
    try:
        raw = zf.read("channels.json")
        channels = json.loads(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        result.errors.append(f"channels.json parse error: {exc}")
        return 0

    for ch in channels:
        if not isinstance(ch, dict):
            continue

        channel_id = ch.get("id", "")
        if not channel_id:
            continue

        channel_doc = {
            "channel_id": channel_id,
            "name": ch.get("name", ""),
            "purpose": ch.get("purpose", {}).get("value", "")
            if isinstance(ch.get("purpose"), dict)
            else "",
            "topic": ch.get("topic", {}).get("value", "")
            if isinstance(ch.get("topic"), dict)
            else "",
            "is_archived": ch.get("is_archived", False),
            "members": ch.get("members", []),
            "num_members": len(ch.get("members", [])),
            "created_ts": ch.get("created"),
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
            created += 1
            result.records_created += 1

    return created


async def _process_messages(
    zf: zipfile.ZipFile,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    result: IngestionFileResult,
) -> None:
    """Parse per-channel per-day JSON message files and store them.

    Also builds concatenated text documents for Citex indexing. Messages
    are grouped per channel into a single text document.
    """
    # Build a lookup of channel names from the ZIP structure
    names = zf.namelist()
    channel_messages: dict[str, list[dict[str, Any]]] = {}

    for entry_name in sorted(names):
        # Message files follow the pattern: <channel_name>/YYYY-MM-DD.json
        parts = entry_name.split("/")
        if len(parts) != 2:
            continue
        channel_name, day_file = parts[0], parts[1]
        if not day_file.endswith(".json"):
            continue
        # Skip top-level metadata files
        if channel_name in ("", "users", "channels") or day_file in (
            "users.json",
            "channels.json",
            "integration_logs.json",
        ):
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
            # Skip non-message subtypes like channel_join, channel_leave
            subtype = msg.get("subtype", "")
            if subtype in ("channel_join", "channel_leave", "channel_purpose", "channel_topic"):
                continue

            text = msg.get("text", "")
            user = msg.get("user", "")
            ts = msg.get("ts", "")

            if not text or not ts:
                continue

            # Parse timestamp
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
                "files": [
                    {
                        "name": f.get("name", ""),
                        "mimetype": f.get("mimetype", ""),
                        "url": f.get("url_private", ""),
                    }
                    for f in msg.get("files", [])
                    if isinstance(f, dict)
                ],
                "created_at": utc_now(),
            }

            # Deduplicate by channel + ts
            existing = await db.slack_messages.find_one({"channel": channel_name, "ts": ts})
            if existing:
                result.records_skipped += 1
                continue

            await db.slack_messages.insert_one(msg_doc)
            result.records_created += 1

            # Collect for Citex text document building
            if channel_name not in channel_messages:
                channel_messages[channel_name] = []
            channel_messages[channel_name].append(
                {
                    "user": user,
                    "text": text,
                    "timestamp": timestamp.isoformat(),
                }
            )

    # Update engagement metrics for users
    await _update_engagement_metrics(db)

    # Build text documents for Citex indexing
    await _build_text_documents(channel_messages, db)


async def _update_engagement_metrics(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Recalculate engagement metrics for all people based on Slack messages."""
    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "messages_sent": {"$sum": 1},
                "threads_replied": {"$sum": {"$cond": [{"$ifNull": ["$thread_ts", False]}, 1, 0]}},
                "reactions_given": {"$sum": {"$size": {"$ifNull": ["$reactions", []]}}},
            }
        },
    ]
    async for agg in db.slack_messages.aggregate(pipeline):
        user_id = agg["_id"]
        if not user_id:
            continue
        await db.people.update_one(
            {"slack_user_id": user_id},
            {
                "$set": {
                    "engagement_metrics.messages_sent": agg["messages_sent"],
                    "engagement_metrics.threads_replied": agg["threads_replied"],
                    "engagement_metrics.reactions_given": agg["reactions_given"],
                    "updated_at": utc_now(),
                }
            },
        )


async def _build_text_documents(
    channel_messages: dict[str, list[dict[str, Any]]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Build concatenated text documents per channel for Citex indexing."""
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
            "source": "slack",
            "source_ref": channel_name,
            "title": f"Slack #{channel_name} messages",
            "content": full_text,
            "content_hash": content_hash,
            "content_type": "text/plain",
            "message_count": len(messages),
            "created_at": utc_now(),
        }
        await db.text_documents.update_one(
            {"source": "slack", "source_ref": channel_name},
            {"$set": doc},
            upsert=True,
        )
        await extract_semantic_insights(
            project_id=None,
            source_type="slack",
            source_ref=channel_name,
            content=full_text,
            db=db,
        )
        await record_hash(content_hash, f"slack_channel_{channel_name}", db)

    await generate_project_snapshot(project_id=None, db=db, force=True)
