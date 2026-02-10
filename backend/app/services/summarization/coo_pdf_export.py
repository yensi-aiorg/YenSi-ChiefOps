"""
PDF export service for COO briefings.

Renders a COO briefing to HTML via an embedded Jinja2 template and
converts to PDF using WeasyPrint. Falls back gracefully to HTML if
WeasyPrint system dependencies are not available.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.exceptions import NotFoundException

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedded HTML template — A4, YENSI branding, teal color scheme
# ---------------------------------------------------------------------------

_BRIEFING_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>COO Briefing — {{ project_name }}</title>
<style>
  @page {
    size: A4;
    margin: 2cm 2.5cm;
    @top-center {
      content: "COO Briefing — {{ project_name }}";
      font-size: 9pt;
      color: #666;
    }
    @bottom-left {
      content: "YENSI ChiefOps";
      font-size: 8pt;
      color: #999;
    }
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #999;
    }
  }
  body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
  }
  .header {
    text-align: center;
    margin-bottom: 2em;
    padding-bottom: 1em;
    border-bottom: 2px solid #0D9488;
  }
  .header h1 {
    color: #115E59;
    font-size: 24pt;
    margin: 0 0 0.3em 0;
  }
  .header .subtitle {
    color: #666;
    font-size: 10pt;
  }
  .header .brand {
    color: #0D9488;
    font-weight: bold;
    font-size: 12pt;
    margin-bottom: 0.5em;
  }
  h2 {
    color: #115E59;
    font-size: 16pt;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 0.3em;
    margin-top: 1.5em;
  }
  h3 { color: #374151; font-size: 13pt; }

  .summary {
    background: #F0FDFA;
    padding: 1em 1.5em;
    border-radius: 8px;
    margin-bottom: 2em;
    border-left: 4px solid #0D9488;
  }
  .summary h2 {
    color: #115E59;
    font-size: 14pt;
    margin-top: 0;
    border-bottom: none;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
  }
  th, td {
    border: 1px solid #E2E8F0;
    padding: 0.5em 0.8em;
    text-align: left;
    font-size: 10pt;
  }
  th {
    background: #F1F5F9;
    font-weight: 600;
    color: #374151;
  }

  .severity-red { color: #DC2626; font-weight: bold; }
  .severity-amber { color: #D97706; font-weight: bold; }
  .severity-green { color: #059669; font-weight: bold; }

  .status-overdue { color: #DC2626; font-weight: bold; }
  .status-at_risk { color: #D97706; font-weight: bold; }
  .status-on_track { color: #059669; font-weight: bold; }

  .status-overloaded { color: #DC2626; font-weight: bold; }
  .status-balanced { color: #059669; font-weight: bold; }
  .status-underutilized { color: #6B7280; }

  .health-box {
    display: flex;
    align-items: center;
    gap: 1em;
    margin: 1em 0;
  }
  .health-score {
    display: inline-block;
    width: 60px;
    height: 60px;
    line-height: 60px;
    text-align: center;
    border-radius: 50%;
    font-size: 20pt;
    font-weight: bold;
    color: white;
  }
  .health-green { background: #059669; }
  .health-yellow { background: #D97706; }
  .health-red { background: #DC2626; }

  .section { margin-bottom: 1.5em; }

  ul { padding-left: 1.5em; }
  li { margin-bottom: 0.3em; }

  .change-item {
    margin-bottom: 0.8em;
    padding-left: 1em;
    border-left: 3px solid #0D9488;
  }
  .change-item .change-text {
    font-weight: 600;
    color: #374151;
  }
  .change-item .impact-text {
    font-size: 10pt;
    color: #6B7280;
    margin-top: 0.2em;
  }

  .footer-note {
    margin-top: 3em;
    padding-top: 1em;
    border-top: 1px solid #E2E8F0;
    font-size: 8pt;
    color: #9CA3AF;
    text-align: center;
  }
</style>
</head>
<body>
  <div class="header">
    <div class="brand">YENSI ChiefOps</div>
    <h1>COO Briefing</h1>
    <div class="subtitle">{{ project_name }} | Generated on {{ generated_date }}</div>
  </div>

  {% if executive_summary %}
  <div class="summary">
    <h2>Executive Summary</h2>
    <p>{{ executive_summary }}</p>
  </div>
  {% endif %}

  {% if attention_items %}
  <div class="section">
    <h2>Needs Attention</h2>
    <table>
      <thead>
        <tr>
          <th style="width: 15%;">Severity</th>
          <th style="width: 30%;">Item</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        {% for item in attention_items %}
        <tr>
          <td class="severity-{{ item.severity }}">{{ item.severity | upper }}</td>
          <td>{{ item.title }}</td>
          <td>{{ item.details }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if project_health %}
  <div class="section">
    <h2>Project Health</h2>
    <div class="health-box">
      <div class="health-score health-{{ project_health.status }}">{{ project_health.score }}</div>
      <div>
        <strong>{{ project_health.status | capitalize }}</strong><br>
        <span style="font-size: 10pt; color: #6B7280;">{{ project_health.rationale }}</span>
      </div>
    </div>
  </div>
  {% endif %}

  {% if team_capacity %}
  <div class="section">
    <h2>Team Capacity</h2>
    <table>
      <thead>
        <tr>
          <th style="width: 25%;">Person</th>
          <th style="width: 20%;">Status</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        {% for item in team_capacity %}
        <tr>
          <td>{{ item.person }}</td>
          <td class="status-{{ item.status }}">{{ item.status | replace('_', ' ') | capitalize }}</td>
          <td>{{ item.details }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if upcoming_deadlines %}
  <div class="section">
    <h2>Upcoming Deadlines</h2>
    <table>
      <thead>
        <tr>
          <th>Item</th>
          <th style="width: 20%;">Date</th>
          <th style="width: 15%;">Status</th>
        </tr>
      </thead>
      <tbody>
        {% for item in upcoming_deadlines %}
        <tr>
          <td>{{ item.item }}</td>
          <td>{{ item.date }}</td>
          <td class="status-{{ item.status }}">{{ item.status | replace('_', ' ') | capitalize }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if recent_changes %}
  <div class="section">
    <h2>Recent Changes</h2>
    {% for item in recent_changes %}
    <div class="change-item">
      <div class="change-text">{{ item.change }}</div>
      <div class="impact-text">Impact: {{ item.impact }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <div class="footer-note">
    This briefing was generated by YENSI ChiefOps AI Assistant.
    Data is based on information available at time of generation.
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public export function
# ---------------------------------------------------------------------------


async def export_coo_briefing_pdf(
    briefing_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> str:
    """Export a COO briefing to PDF.

    Renders the briefing to HTML and converts to PDF using WeasyPrint.
    Falls back to returning HTML if WeasyPrint is unavailable.

    Args:
        briefing_id: UUID of the briefing to export.
        db: Motor database handle.

    Returns:
        File path to the generated PDF (or HTML fallback).

    Raises:
        NotFoundException: If the briefing does not exist.
    """
    briefing = await db.coo_briefings.find_one({"briefing_id": briefing_id})
    if not briefing:
        raise NotFoundException(resource="COO Briefing", identifier=briefing_id)

    html_content = _render_html(briefing)

    try:
        return await _convert_to_pdf(html_content, briefing_id)
    except ImportError:
        logger.warning("WeasyPrint not available, falling back to HTML export")
        return _save_html_fallback(html_content, briefing_id)
    except Exception as exc:
        logger.warning("PDF conversion failed: %s. Falling back to HTML.", exc)
        return _save_html_fallback(html_content, briefing_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _render_html(briefing: dict[str, Any]) -> str:
    """Render the COO briefing to HTML using Jinja2."""
    from jinja2 import Template

    template = Template(_BRIEFING_HTML_TEMPLATE)

    generated_date = ""
    gen_at = briefing.get("updated_at") or briefing.get("created_at")
    if gen_at:
        if isinstance(gen_at, datetime):
            generated_date = gen_at.strftime("%B %d, %Y at %H:%M UTC")
        else:
            generated_date = str(gen_at)
    else:
        generated_date = datetime.now(UTC).strftime("%B %d, %Y at %H:%M UTC")

    # Extract briefing data — may be nested under "briefing" key
    b = briefing.get("briefing", {}) or {}

    return template.render(
        project_name=briefing.get("project_id", "Unknown Project"),
        generated_date=generated_date,
        executive_summary=b.get("executive_summary", ""),
        attention_items=b.get("attention_items", []),
        project_health=b.get("project_health"),
        team_capacity=b.get("team_capacity", []),
        upcoming_deadlines=b.get("upcoming_deadlines", []),
        recent_changes=b.get("recent_changes", []),
    )


async def _convert_to_pdf(html_content: str, briefing_id: str) -> str:
    """Convert HTML to PDF using WeasyPrint."""
    from weasyprint import HTML

    output_dir = tempfile.mkdtemp(prefix="chiefops_coo_briefing_")
    pdf_path = os.path.join(output_dir, f"coo_briefing_{briefing_id[:8]}.pdf")

    html_doc = HTML(string=html_content)
    html_doc.write_pdf(pdf_path)

    logger.info("COO briefing PDF exported to %s", pdf_path)
    return pdf_path


def _save_html_fallback(html_content: str, briefing_id: str) -> str:
    """Save HTML as fallback when PDF conversion is unavailable."""
    output_dir = tempfile.mkdtemp(prefix="chiefops_coo_briefing_")
    html_path = os.path.join(output_dir, f"coo_briefing_{briefing_id[:8]}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info("COO briefing HTML fallback exported to %s", html_path)
    return html_path
