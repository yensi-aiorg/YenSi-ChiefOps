"""
Report generation and editing prompts.

These prompts instruct the AI to produce complete ReportSpec documents
from natural-language requests, and to modify existing report specs
based on follow-up instructions.
"""

from __future__ import annotations

from .base import PromptTemplate

# ---------------------------------------------------------------------------
# Generate a full ReportSpec from a natural-language request
# ---------------------------------------------------------------------------

REPORT_GENERATION_PROMPT = PromptTemplate(
    name="report_generation",
    template="""\
The COO wants to create a new recurring or one-off report. Based on their \
natural-language description, generate a complete report specification.

A report specification must include:
1. **title**: A clear, professional title for the report.
2. **description**: A one-sentence description of the report's purpose.
3. **report_type**: One of "status", "health", "velocity", "risk", "people", \
"financial", "custom".
4. **frequency**: One of "daily", "weekly", "biweekly", "monthly", "quarterly", \
"one_off".
5. **sections**: An ordered list of report sections. Each section has:
   - title: Section heading.
   - content_type: One of "narrative", "table", "list", "chart", "timeline", \
"metric", "comparison".
   - data_sources: Which data collections to query (e.g., "projects", "people", \
"alerts", "tasks", "documents").
   - instructions: Specific guidance on what to include in this section.
   - Additional fields depending on content_type:
     - For "table": columns (list of column names), sort_by, sort_order.
     - For "chart": chart_type ("bar", "line", "pie", "area"), metrics, time_range.
     - For "list": filter (dict of field->value filters).
     - For "metric": metric_name, aggregation ("count", "sum", "avg", "min", "max").
6. **recipients**: Who should receive this report (list of role names or groups).
7. **delivery_day**: Day of week for recurring reports (e.g., "Monday").
8. **delivery_time**: Time of day in HH:MM format.

Design guidelines:
- Lead with an executive summary section for any report with 3+ sections.
- Include at least one data visualisation (chart or metric) when relevant data exists.
- Order sections from most important to least important.
- Make section instructions specific enough that they could be followed without \
additional context.

COO's request:
"{user_request}"

Available data sources in the system:
{available_data_sources}

Existing reports (to avoid duplication):
{existing_reports}

You MUST respond with valid JSON matching this schema:
{{
  "report_spec": {{
    "title": "<string>",
    "description": "<string>",
    "report_type": "<string: status|health|velocity|risk|people|financial|custom>",
    "frequency": "<string: daily|weekly|biweekly|monthly|quarterly|one_off>",
    "sections": [
      {{
        "title": "<string>",
        "content_type": "<string: narrative|table|list|chart|timeline|metric|comparison>",
        "data_sources": ["<string>", ...],
        "instructions": "<string>",
        ... (additional fields based on content_type)
      }}
    ],
    "recipients": ["<string>", ...],
    "delivery_day": "<string or null>",
    "delivery_time": "<string: HH:MM>"
  }}
}}
""",
)

# ---------------------------------------------------------------------------
# Edit an existing report spec based on an instruction
# ---------------------------------------------------------------------------

REPORT_EDIT_PROMPT = PromptTemplate(
    name="report_edit",
    template="""\
The COO wants to modify an existing report specification. Apply their edit \
instruction to the current report spec and return the updated version.

Rules:
1. Only change what the COO explicitly asks to change. Do not reorganise or \
rewrite sections that are not mentioned.
2. If the COO asks to add a section, insert it at the most logical position \
(usually after related sections).
3. If the COO asks to remove a section, remove it entirely.
4. If the COO asks to change frequency, recipients, or delivery schedule, update \
those fields directly.
5. If the instruction is ambiguous, make the most reasonable interpretation and \
note your assumption in a top-level "edit_notes" field.
6. Preserve all existing section IDs and ordering for unchanged sections.

COO's edit instruction:
"{edit_instruction}"

Current report spec:
{current_spec}

You MUST respond with valid JSON matching this schema:
{{
  "report_spec": {{
    "title": "<string>",
    "description": "<string>",
    "report_type": "<string>",
    "frequency": "<string>",
    "sections": [
      {{
        "title": "<string>",
        "content_type": "<string>",
        "data_sources": ["<string>", ...],
        "instructions": "<string>",
        ...
      }}
    ],
    "recipients": ["<string>", ...],
    "delivery_day": "<string or null>",
    "delivery_time": "<string>"
  }},
  "changes_made": [
    "<string: description of each change applied>"
  ],
  "edit_notes": "<string or null: any assumptions made>"
}}
""",
)
