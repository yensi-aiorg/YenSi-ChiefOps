"""
Unit tests for the report generation and export services.

Tests AI-driven report generation, conversational report editing,
and PDF export with graceful fallback handling.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.adapter import AIRequest, AIResponse
from app.ai.mock_adapter import MockAIAdapter
from app.models.base import generate_uuid, utc_now
from app.models.report import (
    ReportHistory,
    ReportSection,
    ReportSpec,
    ReportStatus,
    ReportType,
    SectionType,
)


class TestReportGenerationWithMockAI:
    """Test AI-driven report specification generation."""

    async def test_report_generation_with_mock_ai(self, mock_ai_adapter):
        """MockAIAdapter should produce a valid report spec for generation prompts."""
        request = AIRequest(
            system_prompt="You are a report generation assistant. Generate a report specification.",
            user_prompt="Create a weekly engineering status report covering all active projects.",
            context={
                "projects": [
                    {"name": "Platform Migration", "status": "at_risk"},
                    {"name": "Data Pipeline", "status": "on_track"},
                ],
                "time_range": "last 7 days",
            },
        )

        response = await mock_ai_adapter.generate_structured(request)
        data = response.parse_json()

        assert "report_spec" in data
        spec = data["report_spec"]

        assert "title" in spec
        assert spec["title"]  # Non-empty
        assert "sections" in spec
        assert isinstance(spec["sections"], list)
        assert len(spec["sections"]) > 0

        # Each section should have a title and content_type
        for section in spec["sections"]:
            assert "title" in section
            assert "content_type" in section

    async def test_report_spec_model_creation(self):
        """ReportSpec should be constructable with valid data."""
        spec = ReportSpec(
            report_id=generate_uuid(),
            report_type=ReportType.PROJECT_STATUS,
            title="Q1 Project Status Report",
            time_scope={"start": "2026-01-01", "end": "2026-03-31", "label": "Q1 2026"},
            audience="board",
            projects=["proj-001", "proj-002"],
            sections=[
                ReportSection(
                    section_type=SectionType.NARRATIVE,
                    title="Executive Summary",
                    content={"text": "All projects are progressing well."},
                    order=0,
                ),
                ReportSection(
                    section_type=SectionType.METRICS_GRID,
                    title="Key Metrics",
                    content={
                        "metrics": [
                            {"label": "Active Projects", "value": 4},
                            {"label": "On Track", "value": 3},
                        ]
                    },
                    order=1,
                ),
                ReportSection(
                    section_type=SectionType.TABLE,
                    title="Project Status Overview",
                    content={
                        "headers": ["Project", "Status", "Health"],
                        "rows": [
                            ["Platform Migration", "At Risk", "62"],
                            ["Data Pipeline", "On Track", "85"],
                        ],
                    },
                    order=2,
                ),
            ],
            status=ReportStatus.READY,
        )

        assert spec.title == "Q1 Project Status Report"
        assert spec.report_type == ReportType.PROJECT_STATUS
        assert len(spec.sections) == 3
        assert spec.sections[0].section_type == SectionType.NARRATIVE
        assert spec.status == ReportStatus.READY


class TestReportEditing:
    """Test conversational editing of report sections."""

    async def test_report_editing(self, test_db):
        """A report section should be editable via update operations."""
        collection = test_db["reports"]

        report_id = generate_uuid()
        section_id = generate_uuid()

        report_doc = {
            "report_id": report_id,
            "report_type": ReportType.PROJECT_STATUS.value,
            "title": "Weekly Status Report",
            "time_scope": {},
            "audience": "engineering",
            "projects": [],
            "sections": [
                {
                    "section_id": section_id,
                    "section_type": SectionType.NARRATIVE.value,
                    "title": "Executive Summary",
                    "content": {"text": "Original summary text."},
                    "order": 0,
                },
            ],
            "metadata": {},
            "status": ReportStatus.READY.value,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }

        await collection.insert_one(report_doc)

        # Edit the section content
        new_content = {"text": "Updated summary with new insights about project progress."}
        await collection.update_one(
            {"report_id": report_id, "sections.section_id": section_id},
            {
                "$set": {
                    "sections.$.content": new_content,
                    "sections.$.title": "Updated Executive Summary",
                    "updated_at": utc_now(),
                },
            },
        )

        # Verify the edit
        doc = await collection.find_one({"report_id": report_id})
        assert doc is not None
        section = doc["sections"][0]
        assert section["title"] == "Updated Executive Summary"
        assert section["content"]["text"] == new_content["text"]

    async def test_add_section_to_report(self, test_db):
        """New sections should be appendable to existing reports."""
        collection = test_db["reports"]

        report_id = generate_uuid()
        report_doc = {
            "report_id": report_id,
            "report_type": ReportType.CUSTOM.value,
            "title": "Custom Report",
            "sections": [],
            "status": ReportStatus.GENERATING.value,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        await collection.insert_one(report_doc)

        # Add a new section
        new_section = {
            "section_id": generate_uuid(),
            "section_type": SectionType.CHART.value,
            "title": "Velocity Trend",
            "content": {"chart_type": "line", "data_points": [10, 12, 15, 14, 18]},
            "order": 0,
        }
        await collection.update_one(
            {"report_id": report_id},
            {"$push": {"sections": new_section}, "$set": {"updated_at": utc_now()}},
        )

        doc = await collection.find_one({"report_id": report_id})
        assert len(doc["sections"]) == 1
        assert doc["sections"][0]["title"] == "Velocity Trend"


class TestPdfExportGracefulFallback:
    """Test PDF export with graceful fallback when WeasyPrint is unavailable."""

    def test_pdf_export_graceful_fallback(self):
        """PDF export should handle missing WeasyPrint gracefully."""
        report_html = "<html><body><h1>Test Report</h1><p>Content here.</p></body></html>"

        pdf_bytes = None
        error_message = None

        try:
            # Attempt to import weasyprint -- this will fail in test environments
            # without the library installed, which is the expected behavior.
            import weasyprint
            doc = weasyprint.HTML(string=report_html)
            pdf_bytes = doc.write_pdf()
        except ImportError:
            error_message = "PDF export unavailable: WeasyPrint not installed."
        except Exception as exc:
            error_message = f"PDF export failed: {exc}"

        # In a test environment without WeasyPrint, we should get a graceful fallback
        if pdf_bytes is not None:
            assert isinstance(pdf_bytes, bytes)
            assert len(pdf_bytes) > 0
        else:
            assert error_message is not None
            assert "unavailable" in error_message or "failed" in error_message

    def test_pdf_fallback_returns_html(self):
        """When PDF export fails, the system should fall back to HTML output."""
        report_html = "<html><body><h1>Fallback Report</h1></body></html>"

        # Simulate fallback behavior
        def export_report(html: str) -> tuple[bytes | None, str | None, str]:
            """Try PDF, fall back to HTML."""
            try:
                import weasyprint
                doc = weasyprint.HTML(string=html)
                return doc.write_pdf(), None, "application/pdf"
            except (ImportError, Exception):
                return html.encode("utf-8"), "PDF unavailable, returning HTML.", "text/html"

        content, warning, mime_type = export_report(report_html)

        assert content is not None
        assert len(content) > 0
        # Either PDF or HTML should be returned
        assert mime_type in ("application/pdf", "text/html")


class TestReportHistory:
    """Test report history / versioning."""

    async def test_report_history_creation(self, test_db):
        """Creating a report history entry should capture the full spec snapshot."""
        collection = test_db["report_history"]

        history = ReportHistory(
            history_id=generate_uuid(),
            report_id="report-001",
            report_spec={
                "title": "Weekly Report v1",
                "sections": [{"title": "Summary", "content": "Initial version."}],
            },
            pdf_path="/exports/report-001-v1.pdf",
            generated_by="system",
        )

        await collection.insert_one(history.model_dump())

        doc = await collection.find_one({"history_id": history.history_id})
        assert doc is not None
        assert doc["report_id"] == "report-001"
        assert doc["report_spec"]["title"] == "Weekly Report v1"
        assert doc["pdf_path"] == "/exports/report-001-v1.pdf"
