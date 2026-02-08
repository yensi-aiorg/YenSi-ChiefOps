"""
Project service facade.

Coordinates the project analyzer, health calculator, gap detector,
and feasibility assessor to provide a unified interface for the
API endpoints.  Handles listing, detail retrieval, creation,
updates, and AI-powered analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.exceptions import NotFoundException
from app.models.base import generate_uuid, utc_now

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ProjectService:
    """High-level facade for project management.

    Wraps :mod:`app.services.projects.analyzer`,
    :mod:`app.services.projects.health`,
    :mod:`app.services.projects.gaps`, and
    :mod:`app.services.projects.feasibility` into a single interface.

    Args:
        db: Motor async database handle.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._db = db
        self._collection = db["projects"]
        self._analysis_collection = db["project_analyses"]

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

    async def list_projects(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return a paginated list of projects matching *filters*.

        Args:
            filters: MongoDB query filter dict
                     (e.g. ``{"status": "active"}``).
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Dict with ``projects``, ``total``, ``skip``, ``limit``.
        """
        query = filters or {}
        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        return {
            "projects": docs,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Retrieve the full detail of a single project.

        Args:
            project_id: Unique project identifier.

        Returns:
            The project document.

        Raises:
            NotFoundException: If *project_id* does not exist.
        """
        doc = await self._collection.find_one({"project_id": project_id}, {"_id": 0})
        if doc is None:
            raise NotFoundException(resource="Project", identifier=project_id)
        return doc

    async def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new project from the supplied data.

        Args:
            data: Dict with at minimum a ``name`` key.  Optional keys
                  include ``description`` and ``deadline``.

        Returns:
            The newly created project document.
        """
        now = utc_now()
        project_id = generate_uuid()

        project_doc: dict[str, Any] = {
            "project_id": project_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "status": "active",
            "health_score": "unknown",
            "deadline": data.get("deadline"),
            "team_members": [],
            "open_tasks": 0,
            "completed_tasks": 0,
            "total_tasks": 0,
            "key_risks": [],
            "key_milestones": [],
            "recent_activity": [],
            "last_analysis_at": None,
            "created_at": now,
            "updated_at": now,
        }

        await self._collection.insert_one(project_doc)
        project_doc.pop("_id", None)

        logger.info("Created project %s (%s)", project_id, data["name"])
        return project_doc

    async def update_project(
        self,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply partial updates to an existing project.

        Args:
            project_id: Unique project identifier.
            data: Fields to update (e.g. ``name``, ``description``,
                  ``deadline``, ``status``).

        Returns:
            The updated project document.

        Raises:
            NotFoundException: If *project_id* does not exist.
        """
        doc = await self._collection.find_one({"project_id": project_id})
        if doc is None:
            raise NotFoundException(resource="Project", identifier=project_id)

        data["updated_at"] = utc_now()
        await self._collection.update_one(
            {"project_id": project_id},
            {"$set": data},
        )

        updated = await self._collection.find_one({"project_id": project_id}, {"_id": 0})
        return updated or {}

    async def get_analysis(self, project_id: str) -> dict[str, Any]:
        """Return the most recent analysis for a project.

        Args:
            project_id: Project identifier.

        Returns:
            The analysis document.

        Raises:
            NotFoundException: If the project or its analysis does not
                exist.
        """
        project = await self._collection.find_one({"project_id": project_id})
        if project is None:
            raise NotFoundException(resource="Project", identifier=project_id)

        analysis = await self._analysis_collection.find_one(
            {"project_id": project_id},
            {"_id": 0},
            sort=[("analyzed_at", -1)],
        )
        if analysis is None:
            raise NotFoundException(
                resource="Project analysis",
                identifier=project_id,
            )
        return analysis

    async def analyze_project(self, project_id: str) -> dict[str, Any]:
        """Trigger a fresh AI-powered analysis of a project.

        Delegates to :func:`analyzer.analyze_project` which runs
        health, gap, and feasibility sub-analyses and persists the
        results.

        Args:
            project_id: Project identifier.

        Returns:
            The analysis result dict.

        Raises:
            NotFoundException: If *project_id* does not exist.
        """
        from app.services.projects.analyzer import analyze_project

        project = await self._collection.find_one({"project_id": project_id})
        if project is None:
            raise NotFoundException(resource="Project", identifier=project_id)

        ai_adapter = self._get_ai_adapter()

        logger.info("Triggering analysis for project %s", project_id)
        try:
            result = await analyze_project(
                project_id=project_id,
                db=self._db,
                ai_adapter=ai_adapter,
            )

            # Persist a snapshot in the analyses collection
            analysis_doc = {
                "project_id": project_id,
                "health_score": result.get("health", {}).get("score", "unknown"),
                "summary": result.get("health", {}).get("summary", ""),
                "risks": result.get("feasibility", {}).get("risk_items", []),
                "recommendations": result.get("gap_analysis", {}).get("missing_tasks", []),
                "team_dynamics": {},
                "velocity_trend": "stable",
                "citex_ingestion": result.get("citex_ingestion", {}),
                "citex_context_chunks": result.get("citex_context_chunks", 0),
                "analyzed_at": utc_now(),
            }
            await self._analysis_collection.insert_one(analysis_doc)

            logger.info("Analysis complete for project %s", project_id)
            return result
        except Exception as exc:
            logger.error("Analysis failed for project %s: %s", project_id, exc)
            raise

    async def trigger_analysis(self, project_id: str) -> dict[str, Any]:
        """Convenience alias for :meth:`analyze_project`.

        Matches the method name expected by certain callers.

        Args:
            project_id: Project identifier.

        Returns:
            The analysis result dict.
        """
        return await self.analyze_project(project_id)
