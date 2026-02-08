"""
Widget generation and editing prompts.

These prompts instruct the AI to produce complete WidgetSpec documents
from natural-language descriptions, and to modify existing widget specs.
"""

from __future__ import annotations

from .base import PromptTemplate

# ---------------------------------------------------------------------------
# Generate a WidgetSpec from a natural-language description
# ---------------------------------------------------------------------------

WIDGET_GENERATION_PROMPT = PromptTemplate(
    name="widget_generation",
    template="""\
The COO wants to add a new widget to their operations dashboard. Based on their \
natural-language description, generate a complete widget specification.

A widget specification must include:
1. **title**: A concise, descriptive title (max 40 characters).
2. **widget_type**: One of:
   - "scorecard": Key metrics displayed as large numbers with trend indicators.
   - "table": Tabular data with sortable columns.
   - "chart": A data visualisation (bar, line, pie, area, donut).
   - "list": An ordered or filtered list of items.
   - "timeline": A chronological view of events or milestones.
   - "status_board": A kanban-style board showing items by status.
   - "heatmap": A grid showing intensity of a metric across two dimensions.
   - "progress_bar": A progress indicator toward a goal.
3. **description**: A one-sentence description of what this widget shows.
4. **data_source**: The primary data collection ("projects", "people", "tasks", \
"alerts", "documents", "activity").
5. **layout**: Display configuration:
   - columns: Number of columns (1-4).
   - rows: Number of rows or "auto".
   - card_style: "compact", "standard", or "detailed".
6. **metrics**: For scorecard and chart widgets, a list of metric definitions:
   - label: Display name.
   - query: Filter criteria as a dict.
   - aggregation: "count", "sum", "avg", "min", "max", "percentage".
   - color: Hex colour code.
   - icon: Icon identifier (e.g., "check-circle", "alert-triangle").
7. **refresh_interval_seconds**: How often to refresh data (60-3600).
8. **click_action**: What happens when the user clicks an item:
   - "navigate_to_detail", "open_modal", "filter_dashboard", "none".

Design guidelines:
- Choose the widget type that best communicates the data at a glance.
- Use colour coding consistently: green for healthy/on-track, amber for at-risk, \
red for blocked/critical.
- Prefer scorecards for KPIs, charts for trends, and tables for detailed data.
- Keep the widget focused on one concept; suggest multiple widgets if the request \
is too broad.

COO's description:
"{user_description}"

Available data sources:
{available_data_sources}

Existing dashboard widgets (to avoid duplication):
{existing_widgets}

You MUST respond with valid JSON matching this schema:
{{
  "widget_spec": {{
    "title": "<string: max 40 chars>",
    "widget_type": "<string: scorecard|table|chart|list|timeline|status_board|heatmap|progress_bar>",
    "description": "<string>",
    "data_source": "<string>",
    "layout": {{
      "columns": <integer: 1-4>,
      "rows": "<string or integer>",
      "card_style": "<string: compact|standard|detailed>"
    }},
    "metrics": [
      {{
        "label": "<string>",
        "query": {{}},
        "aggregation": "<string: count|sum|avg|min|max|percentage>",
        "color": "<string: hex colour>",
        "icon": "<string>"
      }}
    ],
    "refresh_interval_seconds": <integer: 60-3600>,
    "click_action": "<string: navigate_to_detail|open_modal|filter_dashboard|none>"
  }}
}}
""",
)

# ---------------------------------------------------------------------------
# Edit an existing widget spec
# ---------------------------------------------------------------------------

WIDGET_EDIT_PROMPT = PromptTemplate(
    name="widget_edit",
    template="""\
The COO wants to modify an existing dashboard widget. Apply their edit instruction \
to the current widget spec and return the updated version.

Rules:
1. Only change what the COO explicitly requests. Preserve all other fields exactly.
2. If the COO asks to change the widget type, restructure the metrics and layout \
appropriately for the new type.
3. If the COO asks to add a metric, append it to the existing metrics list.
4. If the COO asks to change colours, icons, or labels, update only the specified ones.
5. If the COO asks to change the data source, ensure the metrics and queries are \
still valid for the new source.
6. If the instruction is ambiguous, make the most reasonable interpretation and \
document your assumption.

COO's edit instruction:
"{edit_instruction}"

Current widget spec:
{current_spec}

You MUST respond with valid JSON matching this schema:
{{
  "widget_spec": {{
    "title": "<string>",
    "widget_type": "<string>",
    "description": "<string>",
    "data_source": "<string>",
    "layout": {{
      "columns": <integer>,
      "rows": "<string or integer>",
      "card_style": "<string>"
    }},
    "metrics": [...],
    "refresh_interval_seconds": <integer>,
    "click_action": "<string>"
  }},
  "changes_made": [
    "<string: description of each change applied>"
  ],
  "edit_notes": "<string or null: any assumptions made>"
}}
""",
)
