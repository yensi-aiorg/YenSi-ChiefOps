"""
Alert service facade.

Coordinates the lower-level alert engine module and provides a
high-level interface for the API endpoints to create, list, update,
delete, and dismiss alerts.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, ValidationException
from app.models.base import utc_now

logger = logging.getLogger(__name__)


class AlertService:
    """High-level facade for alert management.

    Wraps :mod:`app.services.alerts.alert_engine` and direct MongoDB
    operations into a single, endpoint-friendly interface.

    Args:
        db: Motor async database handle.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._db = db
        self._collection = db["alerts"]

    # ------------------------------------------------------------------
    # AI adapter (lazily resolved)
    # ------------------------------------------------------------------

    def _get_ai_adapter(self) -> Any:
        """Return the singleton AI adapter from the factory.

        Returns ``None`` if the adapter cannot be initialised so that
        downstream code can fall back to heuristic parsing.
        """
        try:
            from app.ai.factory import get_adapter

            return get_adapter()
        except Exception as exc:
            logger.warning("Could not obtain AI adapter: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_from_nl(self, message: str) -> dict[str, Any]:
        """Create an alert from a natural language description.

        Delegates the NL parsing to the alert engine which uses AI
        (with heuristic fallback) to extract a structured condition.

        Args:
            message: Natural language alert description from the COO.

        Returns:
            A dict containing at minimum ``name``, ``description``,
            ``severity``, ``condition``, and optionally ``project_id``.
        """
        from app.services.alerts.alert_engine import (
            create_alert_from_nl,
        )

        ai_adapter = self._get_ai_adapter()

        try:
            result = await create_alert_from_nl(
                description=message,
                db=self._db,
                ai_adapter=ai_adapter,
            )
        except Exception as exc:
            logger.error("Alert engine create_from_nl failed: %s", exc)
            raise

        # Translate the engine output into the shape the endpoint expects.
        condition_data: dict[str, Any] | None = None
        raw_condition = result.get("condition")
        if raw_condition and isinstance(raw_condition, dict):
            condition_data = {
                "field": raw_condition.get("metric", ""),
                "operator": raw_condition.get("operator", "gt"),
                "value": raw_condition.get("threshold", 0),
                "collection": raw_condition.get("collection", "jira_tasks"),
                "filter": raw_condition.get("filters", {}),
            }

        severity_map: dict[str, str] = {
            "task_blocker_count": "critical",
            "health_score": "critical",
            "overdue_tasks": "warning",
            "unassigned_tasks": "warning",
            "completion_rate": "info",
            "velocity_change": "info",
        }
        alert_type = result.get("alert_type", "custom")

        return {
            "name": result.get("name", f"Alert: {message[:60]}"),
            "description": result.get("description", message),
            "severity": severity_map.get(alert_type, "warning"),
            "condition": condition_data,
            "project_id": result.get("project_id"),
        }

    async def list_alerts(
        self,
        filters: Optional[dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return a paginated list of alerts matching *filters*.

        Args:
            filters: MongoDB query filter dict (e.g. ``{"status": "active"}``).
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Dict with ``alerts`` (list of docs), ``total``, ``skip``, ``limit``.
        """
        query = filters or {}
        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        return {
            "alerts": docs,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_triggered(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return all currently triggered alerts.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Dict with ``alerts``, ``total``, ``skip``, ``limit``.
        """
        query: dict[str, Any] = {"status": "triggered"}
        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query, {"_id": 0})
            .sort("last_triggered_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        return {
            "alerts": docs,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def update_alert(
        self,
        alert_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply partial updates to an existing alert.

        Args:
            alert_id: Unique alert identifier.
            updates: Fields to update (e.g. ``status``, ``severity``, ``name``).

        Returns:
            The updated alert document.

        Raises:
            NotFoundException: If *alert_id* does not exist.
        """
        doc = await self._collection.find_one({"alert_id": alert_id})
        if doc is None:
            raise NotFoundException(resource="Alert", identifier=alert_id)

        updates["updated_at"] = utc_now()
        await self._collection.update_one(
            {"alert_id": alert_id},
            {"$set": updates},
        )

        updated = await self._collection.find_one(
            {"alert_id": alert_id}, {"_id": 0}
        )
        return updated or {}

    async def delete_alert(self, alert_id: str) -> dict[str, Any]:
        """Permanently delete an alert.

        Args:
            alert_id: Unique alert identifier.

        Returns:
            Dict with ``alert_id`` and ``message``.

        Raises:
            NotFoundException: If *alert_id* does not exist.
        """
        doc = await self._collection.find_one({"alert_id": alert_id})
        if doc is None:
            raise NotFoundException(resource="Alert", identifier=alert_id)

        await self._collection.delete_one({"alert_id": alert_id})

        logger.info("Deleted alert %s", alert_id)
        return {
            "alert_id": alert_id,
            "message": "Alert has been deleted.",
        }

    async def dismiss_trigger(self, trigger_id: str) -> dict[str, Any]:
        """Dismiss (acknowledge) a triggered alert.

        Delegates to :func:`alert_engine.acknowledge_alert` and
        transitions the alert status to ``dismissed``.

        Args:
            trigger_id: The alert_id of the triggered alert.

        Returns:
            The updated alert document.

        Raises:
            NotFoundException: If *trigger_id* does not exist.
        """
        from app.services.alerts.alert_engine import acknowledge_alert

        doc = await self._collection.find_one({"alert_id": trigger_id})
        if doc is None:
            raise NotFoundException(resource="Alert", identifier=trigger_id)

        result = await acknowledge_alert(alert_id=trigger_id, db=self._db)

        # Also update status to dismissed in the endpoint schema
        await self._collection.update_one(
            {"alert_id": trigger_id},
            {"$set": {"status": "dismissed", "updated_at": utc_now()}},
        )

        updated = await self._collection.find_one(
            {"alert_id": trigger_id}, {"_id": 0}
        )
        logger.info("Dismissed trigger for alert %s", trigger_id)
        return updated or result
