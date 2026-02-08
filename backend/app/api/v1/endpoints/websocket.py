"""
WebSocket endpoints for real-time communication.

Provides two WebSocket channels:
  1. /ws/ingestion/{job_id} - Real-time progress updates for an ingestion job.
  2. /ws/updates - General real-time updates (dashboard refreshes, alert triggers,
     widget data changes).

Clients connect and receive JSON-encoded event messages. The server pushes
updates as they occur via Redis pub/sub or polling MongoDB for state changes.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import get_database_sync

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Manages active WebSocket connections grouped by channel."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection on a channel."""
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = []
        self._connections[channel].append(websocket)
        logger.info(
            "WebSocket connected",
            extra={"channel": channel, "total": len(self._connections[channel])},
        )

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from a channel."""
        if channel in self._connections:
            self._connections[channel] = [
                ws for ws in self._connections[channel] if ws is not websocket
            ]
            if not self._connections[channel]:
                del self._connections[channel]

    async def send_to_channel(self, channel: str, data: dict) -> None:
        """Broadcast a message to all connections on a channel."""
        if channel not in self._connections:
            return

        dead: list[WebSocket] = []
        for ws in self._connections[channel]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self._connections[channel] = [
                c for c in self._connections.get(channel, []) if c is not ws
            ]

    async def send_personal(self, websocket: WebSocket, data: dict) -> None:
        """Send a message to a single WebSocket connection."""
        with contextlib.suppress(Exception):
            await websocket.send_json(data)

    def get_channel_count(self, channel: str) -> int:
        """Return the number of connections on a channel."""
        return len(self._connections.get(channel, []))


# Singleton connection manager
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _poll_ingestion_status(
    websocket: WebSocket,
    job_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Poll MongoDB for ingestion job status and push updates to the client."""
    collection = db["ingestion_jobs"]
    last_status: str | None = None
    last_processed: int = -1

    while True:
        try:
            doc = await collection.find_one({"job_id": job_id}, {"_id": 0})
            if doc is None:
                await manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "message": f"Job '{job_id}' not found.",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                break

            current_status = doc.get("status", "unknown")
            files_processed = doc.get("files_processed", 0)
            total_files = doc.get("total_files", 0)

            # Only send update if something changed
            if current_status != last_status or files_processed != last_processed:
                last_status = current_status
                last_processed = files_processed

                event = {
                    "type": "ingestion_progress",
                    "job_id": job_id,
                    "status": current_status,
                    "files_processed": files_processed,
                    "total_files": total_files,
                    "progress_percent": round(
                        (files_processed / total_files * 100) if total_files > 0 else 0, 1
                    ),
                    "error_message": doc.get("error_message"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await manager.send_personal(websocket, event)

            # Stop polling if job reached a terminal state
            if current_status in ("completed", "failed", "cancelled"):
                await manager.send_personal(
                    websocket,
                    {
                        "type": "ingestion_complete",
                        "job_id": job_id,
                        "final_status": current_status,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
                break

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Ingestion poll error", extra={"job_id": job_id}, exc_info=exc)
            await asyncio.sleep(2)


async def _push_general_updates(
    websocket: WebSocket,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Push general real-time updates to the client.

    Monitors Redis pub/sub for update events. Falls back to periodic heartbeat
    if Redis pub/sub is not available.
    """
    # Try to subscribe to Redis for real-time events
    try:
        from app.redis_client import get_redis_sync

        redis = get_redis_sync()
        pubsub = redis.pubsub()
        await pubsub.subscribe("chiefops:updates")

        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=5.0,
                )
                if message and message.get("type") == "message":
                    data = message.get("data", "")
                    try:
                        event = json.loads(data) if isinstance(data, str) else data
                    except (json.JSONDecodeError, TypeError):
                        event = {"type": "update", "data": str(data)}

                    event["timestamp"] = datetime.now(UTC).isoformat()
                    await manager.send_personal(websocket, event)
                else:
                    # Send heartbeat to keep connection alive
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "heartbeat",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
        finally:
            await pubsub.unsubscribe("chiefops:updates")
            await pubsub.aclose()

    except (ImportError, RuntimeError):
        # Redis not available; fall back to polling heartbeat
        logger.info("Redis pub/sub unavailable; using heartbeat-only mode for general updates.")
        while True:
            try:
                await manager.send_personal(
                    websocket,
                    {
                        "type": "heartbeat",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

                # Check for recently triggered alerts
                alerts_col = db["alerts"]
                triggered = await alerts_col.count_documents({"status": "triggered"})
                if triggered > 0:
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "alert_summary",
                            "triggered_count": triggered,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )

                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("General updates error", exc_info=exc)
                await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.websocket("/ws/ingestion/{job_id}")
async def websocket_ingestion(
    websocket: WebSocket,
    job_id: str,
) -> None:
    """WebSocket endpoint for real-time ingestion job progress.

    Connect to receive status updates, progress percentages, and completion
    notifications for a specific ingestion job.

    Events sent:
    - ingestion_progress: Current status and file progress
    - ingestion_complete: Job reached terminal state
    - error: Job not found or processing error
    """
    channel = f"ingestion:{job_id}"
    await manager.connect(channel, websocket)

    try:
        db = get_database_sync()
    except RuntimeError:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Database not initialized.",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        await websocket.close()
        manager.disconnect(channel, websocket)
        return

    poll_task = asyncio.create_task(_poll_ingestion_status(websocket, job_id, db))

    try:
        while True:
            # Keep the connection open; handle client messages if needed
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "pong",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"channel": channel})
    finally:
        poll_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poll_task
        manager.disconnect(channel, websocket)


@router.websocket("/ws/updates")
async def websocket_updates(
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint for general real-time updates.

    Connect to receive dashboard refresh signals, widget data updates,
    alert triggers, and other system events.

    Events sent:
    - heartbeat: Periodic keep-alive
    - dashboard_refresh: A dashboard's data has been updated
    - widget_update: A widget's data has changed
    - alert_triggered: An alert condition was met
    - alert_summary: Count of currently triggered alerts
    - ingestion_complete: An ingestion job finished
    """
    channel = "general_updates"
    await manager.connect(channel, websocket)

    try:
        db = get_database_sync()
    except RuntimeError:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Database not initialized.",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        await websocket.close()
        manager.disconnect(channel, websocket)
        return

    update_task = asyncio.create_task(_push_general_updates(websocket, db))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "pong",
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
                elif msg_type == "subscribe":
                    # Client can subscribe to specific event types
                    event_filter = message.get("events", [])
                    await manager.send_personal(
                        websocket,
                        {
                            "type": "subscribed",
                            "events": event_filter,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"channel": channel})
    finally:
        update_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await update_task
        manager.disconnect(channel, websocket)
