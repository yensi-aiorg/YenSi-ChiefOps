"""
Report service facade.

Coordinates the report generator, natural-language editor, and PDF
exporter to provide a unified interface for the API endpoints.
Handles generation, listing, retrieval, editing, PDF export, and
deletion of reports.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException
from app.models.base import utc_now

logger = logging.getLogger(__name__)


class ReportService:
    """High-level facade for report management.

    Wraps :mod:`app.services.reports.generator`,
    :mod:`app.services.reports.editor`, and
    :mod:`app.services.reports.pdf_export` into a single interface.

    Args:
        db: Motor async database handle.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._db = db
        self._collection = db["reports"]

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

    async def generate(
        self,
        message: str,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate a report from a natural language request.

        Delegates to :func:`generator.generate_report` which assembles
        data context, sends it to AI, and returns a structured report
        specification.

        Args:
            message: Natural language description of the desired report.
            project_id: Optional project scope for the report.

        Returns:
            Dict containing ``title``, ``summary``, ``sections``, and
            ``metadata``.
        """
        from app.services.reports.generator import generate_report

        ai_adapter = self._get_ai_adapter()

        try:
            result = await generate_report(
                message=message,
                project_id=project_id or "",
                db=self._db,
                ai_adapter=ai_adapter,
            )
        except Exception as exc:
            logger.error("Report generation failed: %s", exc)
            raise

        # Normalise section format: the generator uses ``heading`` while
        # the endpoint schema expects ``title`` + ``content`` + ``order``.
        normalised_sections: list[dict[str, Any]] = []
        for idx, section in enumerate(result.get("sections", [])):
            normalised_sections.append({
                "title": section.get("heading", section.get("title", "Section")),
                "content": section.get("content", ""),
                "order": idx,
                "charts": section.get("charts", []),
            })

        return {
            "title": result.get("title", "Generated Report"),
            "summary": result.get("summary", ""),
            "sections": normalised_sections,
            "metadata": {
                "report_type": result.get("report_type", "custom"),
                "key_metrics": result.get("key_metrics", []),
                "recommendations": result.get("recommendations", []),
            },
        }

    async def list_reports(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Return a paginated list of reports.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            filters: Optional MongoDB query filter dict.

        Returns:
            Dict with ``reports``, ``total``, ``skip``, ``limit``.
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
            "reports": docs,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_report(self, report_id: str) -> dict[str, Any]:
        """Retrieve the full specification of a single report.

        Args:
            report_id: Unique report identifier.

        Returns:
            The report document.

        Raises:
            NotFoundException: If *report_id* does not exist.
        """
        doc = await self._collection.find_one(
            {"report_id": report_id}, {"_id": 0}
        )
        if doc is None:
            raise NotFoundException(resource="Report", identifier=report_id)
        return doc

    async def edit(
        self,
        report_id: str,
        current_report: dict[str, Any],
        message: str,
    ) -> dict[str, Any]:
        """Edit an existing report via natural language instruction.

        Delegates to :func:`editor.edit_report` which uses AI to
        interpret the instruction and modify the report specification.

        Args:
            report_id: UUID of the report to edit.
            current_report: The current report document (avoids a
                redundant DB read).
            message: Natural language edit instruction from the COO.

        Returns:
            Dict with updated ``title``, ``summary``, and ``sections``.
        """
        from app.services.reports.editor import edit_report

        ai_adapter = self._get_ai_adapter()

        try:
            result = await edit_report(
                report_id=report_id,
                instruction=message,
                db=self._db,
                ai_adapter=ai_adapter,
            )
        except NotFoundException:
            raise
        except Exception as exc:
            logger.error("Report edit failed for %s: %s", report_id, exc)
            raise

        # Normalise section format for the endpoint response
        normalised_sections: list[dict[str, Any]] = []
        for idx, section in enumerate(result.get("sections", [])):
            normalised_sections.append({
                "title": section.get("heading", section.get("title", "Section")),
                "content": section.get("content", ""),
                "order": idx,
                "charts": section.get("charts", []),
            })

        return {
            "title": result.get("title", current_report.get("title", "")),
            "summary": result.get("summary", current_report.get("summary", "")),
            "sections": normalised_sections or current_report.get("sections", []),
        }

    async def export_pdf(self, report_id: str) -> str:
        """Export a report to PDF (or HTML fallback).

        Delegates to :func:`pdf_export.export_pdf` which renders
        the report to HTML via Jinja2 and converts to PDF using
        WeasyPrint.

        Args:
            report_id: UUID of the report to export.

        Returns:
            File path to the generated PDF (or HTML fallback).

        Raises:
            NotFoundException: If *report_id* does not exist.
        """
        from app.services.reports.pdf_export import export_pdf

        return await export_pdf(report_id=report_id, db=self._db)

    async def delete_report(self, report_id: str) -> dict[str, Any]:
        """Permanently delete a report.

        Args:
            report_id: Unique report identifier.

        Returns:
            Dict with ``report_id`` and ``message``.

        Raises:
            NotFoundException: If *report_id* does not exist.
        """
        doc = await self._collection.find_one({"report_id": report_id})
        if doc is None:
            raise NotFoundException(resource="Report", identifier=report_id)

        await self._collection.delete_one({"report_id": report_id})

        logger.info("Deleted report %s", report_id)
        return {
            "report_id": report_id,
            "message": "Report has been deleted.",
        }
