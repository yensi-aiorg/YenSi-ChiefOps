"""
People service facade.

Coordinates the people pipeline, corrections module, and entity
resolver to provide a unified interface for the API endpoints.
Handles listing, detail retrieval, COO corrections, and
reprocessing of the people identity pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, ValidationException
from app.models.base import utc_now

logger = logging.getLogger(__name__)


class PeopleService:
    """High-level facade for people directory management.

    Wraps :mod:`app.services.people.pipeline`,
    :mod:`app.services.people.corrections`, and
    :mod:`app.services.people.resolver` into a single interface.

    Args:
        db: Motor async database handle.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._db = db
        self._collection = db["people"]

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

    async def list_people(
        self,
        filters: Optional[dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return a paginated list of people matching *filters*.

        Args:
            filters: MongoDB query filter dict
                     (e.g. ``{"activity_level": "active"}``).
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Dict with ``people`` (list of docs), ``total``, ``skip``,
            ``limit``.
        """
        query = filters or {}
        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query, {"_id": 0})
            .sort("name", 1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        return {
            "people": docs,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_person(self, person_id: str) -> dict[str, Any]:
        """Retrieve the full detail of a single person.

        Args:
            person_id: Unique person identifier.

        Returns:
            The person document.

        Raises:
            NotFoundException: If *person_id* does not exist.
        """
        doc = await self._collection.find_one(
            {"person_id": person_id}, {"_id": 0}
        )
        if doc is None:
            raise NotFoundException(resource="Person", identifier=person_id)
        return doc

    async def correct_person(
        self,
        person_id: str,
        corrections: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply COO corrections to a person record.

        Delegates to :func:`corrections.apply_correction` which
        persists the correction as a hard fact in the memory system
        so it survives pipeline reprocessing.

        Args:
            person_id: UUID of the person to correct.
            corrections: Dict with keys ``name``, ``role``,
                         ``department``, or ``email``.

        Returns:
            The updated person document.

        Raises:
            NotFoundException: If *person_id* does not exist.
            ValidationException: If *corrections* is empty.
        """
        from app.services.people.corrections import apply_correction

        return await apply_correction(
            person_id=person_id,
            correction_data=corrections,
            db=self._db,
        )

    async def reprocess_all(self) -> list[dict[str, Any]]:
        """Re-run the full people identification pipeline.

        Delegates to :func:`pipeline.run_pipeline` which:

        1. Builds the initial directory from Slack, Jira, and Drive.
        2. Performs cross-source entity resolution.
        3. Runs AI-powered role detection.
        4. Calculates activity levels.
        5. Persists results to MongoDB.

        COO-corrected fields are preserved through reprocessing.

        Returns:
            List of person documents that were created or updated.
        """
        from app.services.people.pipeline import run_pipeline

        ai_adapter = self._get_ai_adapter()

        logger.info("Starting people pipeline reprocessing")
        try:
            results = await run_pipeline(db=self._db, ai_adapter=ai_adapter)
            logger.info(
                "People pipeline reprocessing complete: %d records",
                len(results),
            )
            return results
        except Exception as exc:
            logger.error("People pipeline reprocessing failed: %s", exc)
            raise
