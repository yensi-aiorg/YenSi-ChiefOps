"""
Widget service facade.

Coordinates the widget query engine, NL spec generator, and Redis
cache to provide a unified interface for the API endpoints.  Handles
widget retrieval, data execution, NL generation, dashboard
placement, updates, NL editing, and deletion.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException
from app.models.base import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class WidgetService:
    """High-level facade for widget management.

    Wraps :mod:`app.services.widgets.query_engine`,
    :mod:`app.services.widgets.spec_generator`, and
    :mod:`app.services.widgets.cache` into a single interface.

    Args:
        db: Motor async database handle.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._db = db
        self._collection = db["widgets"]
        self._dashboards = db["dashboards"]

    # ------------------------------------------------------------------
    # AI adapter (lazily resolved)
    # ------------------------------------------------------------------

    def _get_ai_adapter(self) -> Any:
        """Return the singleton AI adapter, or ``None`` on failure."""
        try:
            from app.ai.factory import get_adapter

            return get_adapter()
        except Exception as exc:
            logger.warning("Could not obtain AI adapter: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_widget(self, widget_id: str) -> dict[str, Any]:
        """Retrieve the full specification of a single widget.

        Args:
            widget_id: Unique widget identifier.

        Returns:
            The widget document.

        Raises:
            NotFoundException: If *widget_id* does not exist.
        """
        doc = await self._collection.find_one(
            {"widget_id": widget_id}, {"_id": 0}
        )
        if doc is None:
            raise NotFoundException(resource="Widget", identifier=widget_id)
        return doc

    async def get_widget_data(self, widget_id: str) -> dict[str, Any]:
        """Execute a widget's data query and return results.

        Checks the Redis cache first and falls back to the query
        engine on a cache miss.

        Args:
            widget_id: Unique widget identifier.

        Returns:
            Dict with ``widget_id``, ``title``, ``widget_type``,
            ``data``, ``row_count``, and ``executed_at``.

        Raises:
            NotFoundException: If *widget_id* does not exist.
        """
        from app.services.widgets.query_engine import execute_query
        from app.services.widgets import cache as widget_cache

        doc = await self._collection.find_one(
            {"widget_id": widget_id}, {"_id": 0}
        )
        if doc is None:
            raise NotFoundException(resource="Widget", identifier=widget_id)

        data_query = doc.get("data_query", {})

        # Try cache
        query_hash = widget_cache.compute_query_hash(data_query)
        cached = await widget_cache.get_cached(query_hash)
        if cached is not None:
            return {
                "widget_id": widget_id,
                "title": doc.get("title", ""),
                "widget_type": doc.get("widget_type", "metric_card"),
                "data": cached.get("data", []),
                "row_count": len(cached.get("data", [])) if isinstance(cached.get("data"), list) else 1,
                "executed_at": utc_now(),
            }

        # Execute query
        result = await execute_query(data_query=data_query, db=self._db)
        data = result.get("data", [])

        # Store in cache
        refresh_interval = data_query.get("refresh_interval_seconds", 300)
        ttl = max(refresh_interval, 60)
        await widget_cache.set_cached(query_hash, result, ttl=ttl)

        row_count = len(data) if isinstance(data, list) else 1

        return {
            "widget_id": widget_id,
            "title": doc.get("title", ""),
            "widget_type": doc.get("widget_type", "metric_card"),
            "data": data,
            "row_count": row_count,
            "executed_at": utc_now(),
        }

    async def generate_from_nl(
        self,
        description: str,
        dashboard_id: str,
    ) -> Any:
        """Generate a widget from a natural language description.

        Delegates to :func:`spec_generator.generate_widget_spec` which
        uses AI to convert the description into a structured widget
        specification, persists it, and links it to the dashboard.

        Args:
            description: Natural language description of the desired
                widget from the COO.
            dashboard_id: Dashboard to associate the widget with.

        Returns:
            A ``WidgetSpec``-compatible object or dict describing the
            newly created widget.
        """
        from app.services.widgets.spec_generator import generate_widget_spec

        ai_adapter = self._get_ai_adapter()

        try:
            widget_doc = await generate_widget_spec(
                description=description,
                dashboard_id=dashboard_id,
                db=self._db,
                ai_adapter=ai_adapter,
            )
        except Exception as exc:
            logger.error("Widget NL generation failed: %s", exc)
            raise

        # Map the spec_generator output into a WidgetSpec-compatible shape
        # that the endpoint can return.
        from app.api.v1.endpoints.widgets import DataQuery, WidgetSpec, WidgetType

        now = utc_now()
        raw_query = widget_doc.get("data_query", {})

        # Build a DataQuery from the spec generator's format
        data_query = DataQuery(
            collection=raw_query.get("collection", "projects"),
            pipeline=raw_query.get("pipeline", []),
            refresh_interval_seconds=widget_doc.get("refresh_interval", 300),
        )

        # Map chart_type to WidgetType enum
        chart_to_widget: dict[str, str] = {
            "metric": "metric_card",
            "bar": "bar_chart",
            "line": "line_chart",
            "pie": "pie_chart",
            "stacked_bar": "bar_chart",
            "table": "table",
            "heatmap": "heatmap",
            "gauge": "metric_card",
            "list": "list",
        }
        chart_type = widget_doc.get("chart_type", "metric")
        widget_type_str = chart_to_widget.get(chart_type, "metric_card")

        try:
            widget_type = WidgetType(widget_type_str)
        except ValueError:
            widget_type = WidgetType.METRIC_CARD

        spec = WidgetSpec(
            widget_id=widget_doc.get("widget_id", generate_uuid()),
            title=widget_doc.get("title", f"Generated: {description[:80]}"),
            description=widget_doc.get("description", description),
            widget_type=widget_type,
            data_query=data_query,
            config=widget_doc.get("style", {}),
            dashboard_id=dashboard_id,
            created_at=now,
            updated_at=now,
        )

        return spec

    async def add_to_dashboard(
        self,
        dashboard_id: str,
        widget_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a pre-built widget specification to a dashboard.

        Args:
            dashboard_id: Target dashboard identifier.
            widget_spec: Full widget specification dict.

        Returns:
            The persisted widget document.

        Raises:
            NotFoundException: If *dashboard_id* does not exist.
        """
        dashboard = await self._dashboards.find_one(
            {"dashboard_id": dashboard_id}
        )
        if dashboard is None:
            raise NotFoundException(
                resource="Dashboard", identifier=dashboard_id
            )

        now = utc_now()
        widget_id = widget_spec.get("widget_id", generate_uuid())
        widget_spec["widget_id"] = widget_id
        widget_spec["dashboard_id"] = dashboard_id
        widget_spec.setdefault("created_at", now)
        widget_spec["updated_at"] = now

        await self._collection.insert_one(widget_spec)

        # Link to dashboard
        await self._dashboards.update_one(
            {"dashboard_id": dashboard_id},
            {
                "$push": {"widget_ids": widget_id},
                "$set": {"updated_at": now},
            },
        )

        widget_spec.pop("_id", None)
        logger.info(
            "Added widget %s to dashboard %s", widget_id, dashboard_id
        )
        return widget_spec

    async def update_widget(
        self,
        widget_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply partial updates to an existing widget.

        Args:
            widget_id: Unique widget identifier.
            updates: Fields to update (e.g. ``title``, ``widget_type``,
                     ``data_query``, ``config``).

        Returns:
            The updated widget document.

        Raises:
            NotFoundException: If *widget_id* does not exist.
        """
        doc = await self._collection.find_one({"widget_id": widget_id})
        if doc is None:
            raise NotFoundException(resource="Widget", identifier=widget_id)

        updates["updated_at"] = utc_now()
        await self._collection.update_one(
            {"widget_id": widget_id},
            {"$set": updates},
        )

        # Invalidate cache for this widget
        try:
            from app.services.widgets import cache as widget_cache

            data_query = doc.get("data_query", {})
            if data_query:
                query_hash = widget_cache.compute_query_hash(data_query)
                # Overwrite with empty to effectively invalidate
                await widget_cache.set_cached(query_hash, {}, ttl=1)
        except Exception:
            pass  # Cache invalidation is best-effort

        updated = await self._collection.find_one(
            {"widget_id": widget_id}, {"_id": 0}
        )
        return updated or {}

    async def edit_from_nl(
        self,
        widget_id: str,
        current_spec: Any,
        message: str,
    ) -> Any:
        """Edit a widget via a natural language instruction.

        Uses AI to interpret the instruction and produce an updated
        widget specification.

        Args:
            widget_id: Unique widget identifier.
            current_spec: The current ``WidgetSpec`` instance.
            message: Natural language edit instruction.

        Returns:
            An updated ``WidgetSpec`` instance.
        """
        from app.services.widgets.spec_generator import generate_widget_spec
        from app.api.v1.endpoints.widgets import DataQuery, WidgetSpec, WidgetType

        ai_adapter = self._get_ai_adapter()

        # Use the spec generator with the edit instruction
        # (providing the current widget context)
        try:
            raw_spec = await _ai_edit_widget(
                current_spec=current_spec,
                message=message,
                ai_adapter=ai_adapter,
            )
        except Exception as exc:
            logger.warning(
                "AI widget edit failed for %s: %s; applying heuristic",
                widget_id,
                exc,
            )
            raw_spec = _heuristic_edit_widget(
                current_spec=current_spec,
                message=message,
            )

        now = utc_now()

        # Map the AI output into a WidgetSpec
        chart_to_widget: dict[str, str] = {
            "metric": "metric_card",
            "bar": "bar_chart",
            "line": "line_chart",
            "pie": "pie_chart",
            "stacked_bar": "bar_chart",
            "table": "table",
            "heatmap": "heatmap",
            "gauge": "metric_card",
            "list": "list",
        }

        # Determine widget type
        if "widget_type" in raw_spec:
            try:
                widget_type = WidgetType(raw_spec["widget_type"])
            except ValueError:
                mapped = chart_to_widget.get(raw_spec["widget_type"], "")
                widget_type = WidgetType(mapped) if mapped else current_spec.widget_type
        elif "chart_type" in raw_spec:
            mapped = chart_to_widget.get(raw_spec["chart_type"], "")
            widget_type = WidgetType(mapped) if mapped else current_spec.widget_type
        else:
            widget_type = current_spec.widget_type

        # Build data query
        if "data_query" in raw_spec and isinstance(raw_spec["data_query"], dict):
            rq = raw_spec["data_query"]
            data_query = DataQuery(
                collection=rq.get("collection", current_spec.data_query.collection),
                pipeline=rq.get("pipeline", current_spec.data_query.pipeline),
                refresh_interval_seconds=rq.get(
                    "refresh_interval_seconds",
                    current_spec.data_query.refresh_interval_seconds,
                ),
            )
        else:
            data_query = current_spec.data_query

        updated_spec = WidgetSpec(
            widget_id=widget_id,
            title=raw_spec.get("title", current_spec.title),
            description=raw_spec.get("description", current_spec.description),
            widget_type=widget_type,
            data_query=data_query,
            config=raw_spec.get("config", raw_spec.get("style", current_spec.config)),
            dashboard_id=current_spec.dashboard_id,
            created_at=current_spec.created_at,
            updated_at=now,
        )

        return updated_spec

    async def nl_edit(
        self,
        widget_id: str,
        message: str,
    ) -> dict[str, Any]:
        """Convenience wrapper: fetch widget, edit via NL, persist.

        Args:
            widget_id: Unique widget identifier.
            message: Natural language edit instruction.

        Returns:
            The updated widget document.

        Raises:
            NotFoundException: If *widget_id* does not exist.
        """
        from app.api.v1.endpoints.widgets import WidgetSpec

        doc = await self._collection.find_one(
            {"widget_id": widget_id}, {"_id": 0}
        )
        if doc is None:
            raise NotFoundException(resource="Widget", identifier=widget_id)

        current_spec = WidgetSpec(**doc)
        updated_spec = await self.edit_from_nl(
            widget_id=widget_id,
            current_spec=current_spec,
            message=message,
        )

        # Persist
        await self._collection.update_one(
            {"widget_id": widget_id},
            {"$set": updated_spec.model_dump()},
        )

        return updated_spec.model_dump()

    async def delete_widget(self, widget_id: str) -> dict[str, Any]:
        """Remove a widget and clean up its dashboard reference.

        Args:
            widget_id: Unique widget identifier.

        Returns:
            Dict with ``widget_id`` and ``message``.

        Raises:
            NotFoundException: If *widget_id* does not exist.
        """
        doc = await self._collection.find_one({"widget_id": widget_id})
        if doc is None:
            raise NotFoundException(resource="Widget", identifier=widget_id)

        # Remove from parent dashboard
        dashboard_id = doc.get("dashboard_id")
        if dashboard_id:
            await self._dashboards.update_one(
                {"dashboard_id": dashboard_id},
                {
                    "$pull": {
                        "widget_ids": widget_id,
                        "layout": {"widget_id": widget_id},
                    },
                    "$set": {"updated_at": utc_now()},
                },
            )

        await self._collection.delete_one({"widget_id": widget_id})

        # Invalidate cache
        try:
            from app.services.widgets import cache as widget_cache

            data_query = doc.get("data_query", {})
            if data_query:
                query_hash = widget_cache.compute_query_hash(data_query)
                await widget_cache.set_cached(query_hash, {}, ttl=1)
        except Exception:
            pass

        logger.info("Deleted widget %s", widget_id)
        return {
            "widget_id": widget_id,
            "message": "Widget has been deleted.",
        }


# ----------------------------------------------------------------------
# Private helpers
# ----------------------------------------------------------------------


async def _ai_edit_widget(
    current_spec: Any,
    message: str,
    ai_adapter: Any,
) -> dict[str, Any]:
    """Use AI to edit a widget based on a natural language instruction."""
    if ai_adapter is None:
        return _heuristic_edit_widget(current_spec, message)

    import json

    spec_dict = current_spec.model_dump() if hasattr(current_spec, "model_dump") else dict(current_spec)
    # Remove non-serialisable fields
    spec_dict.pop("created_at", None)
    spec_dict.pop("updated_at", None)

    spec_json = json.dumps(spec_dict, indent=2, default=str)

    prompt = (
        "Edit the following widget specification based on the instruction.\n\n"
        f"Current widget spec:\n{spec_json}\n\n"
        f"Edit instruction: {message}\n\n"
        "Return the COMPLETE updated widget specification as JSON. "
        "Include ALL fields, not just the changed ones."
    )

    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "widget_type": {"type": "string"},
            "chart_type": {"type": "string"},
            "data_query": {"type": "object"},
            "config": {"type": "object"},
            "style": {"type": "object"},
        },
        "required": ["title"],
    }

    try:
        return await ai_adapter.generate_structured(
            prompt=prompt,
            schema=schema,
            system="You are a dashboard widget editor. Apply the requested changes while preserving the overall structure.",
        )
    except Exception as exc:
        logger.warning("AI widget edit failed: %s", exc)
        return _heuristic_edit_widget(current_spec, message)


def _heuristic_edit_widget(
    current_spec: Any,
    message: str,
) -> dict[str, Any]:
    """Apply simple heuristic edits to a widget spec."""
    msg_lower = message.lower()
    result: dict[str, Any] = {}

    # Title changes
    if "title" in msg_lower or "rename" in msg_lower:
        for marker in ("to ", "as ", "title "):
            if marker in msg_lower:
                new_title = message.split(marker, 1)[-1].strip().strip('"').strip("'")
                if new_title:
                    result["title"] = new_title
                break

    # Chart type changes
    chart_keywords = {
        "bar": "bar_chart",
        "line": "line_chart",
        "pie": "pie_chart",
        "table": "table",
        "metric": "metric_card",
        "heatmap": "heatmap",
    }
    if "change" in msg_lower and ("chart" in msg_lower or "type" in msg_lower):
        for keyword, widget_type in chart_keywords.items():
            if keyword in msg_lower:
                result["widget_type"] = widget_type
                break

    # Description changes
    if "description" in msg_lower:
        for marker in ("to ", "as "):
            if marker in msg_lower:
                new_desc = message.split(marker, 1)[-1].strip().strip('"').strip("'")
                if new_desc:
                    result["description"] = new_desc
                break

    return result
