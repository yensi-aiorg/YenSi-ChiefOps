"""
Intent detection prompt for classifying COO input.

Classifies user messages into actionable intent types so the
orchestration layer can route them to the appropriate handler.
"""

from __future__ import annotations

from .base import PromptTemplate

# ---------------------------------------------------------------------------
# Intent detection and classification
# ---------------------------------------------------------------------------

INTENT_DETECTION_PROMPT = PromptTemplate(
    name="intent_detection",
    template="""\
You are the intent classification engine for ChiefOps, an AI operations advisor \
for COOs. Analyse the user's message and classify it into exactly one intent type.

Intent types:

1. **query** - The user is asking a question about data (projects, people, metrics, \
status, history). They want information, not action.
   Sub-types: "project_status", "people_info", "metric_lookup", "timeline_query", \
"comparison", "search", "general_question".

2. **correction** - The user is correcting previously shown information or updating \
a fact about a person, project, or process.
   Sub-types: "role_correction", "name_correction", "status_correction", \
"data_correction", "relationship_correction".

3. **command** - The user is instructing ChiefOps to create or modify something.
   Sub-types:
   - "create_widget": Create a new dashboard widget.
   - "edit_widget": Modify an existing dashboard widget.
   - "create_report": Create a new report specification.
   - "edit_report": Modify an existing report specification.
   - "create_alert": Set up a new alert or notification rule.
   - "edit_alert": Modify an existing alert rule.
   - "create_dashboard": Create or configure a dashboard layout.
   - "edit_dashboard": Modify dashboard layout or settings.
   - "run_analysis": Trigger a specific analysis (gap analysis, feasibility, etc.).
   - "schedule_briefing": Schedule or configure a recurring briefing.

4. **chat** - General conversation, greetings, feedback, or off-topic remarks that \
do not fit the above categories.
   Sub-types: "greeting", "farewell", "feedback", "clarification", "acknowledgement", \
"off_topic".

For your classification, also extract:
- **extracted_entities**: Any named entities mentioned (project names, people names, \
dates, metrics, time ranges).
- **parameters**: Relevant parameters that the downstream handler will need \
(e.g., for a widget command: widget type, data source; for a query: which project, \
time range).
- **confidence**: Your confidence in the classification (0.0 to 1.0).
- **reasoning**: A one-sentence explanation of why you chose this classification.

Edge cases:
- "Show me a chart of project health" is a **command** (create_widget), not a query.
- "What projects are at risk?" is a **query** (project_status).
- "Actually, Sarah is the tech lead, not Marcus" is a **correction** (role_correction).
- "Thanks, that's helpful" is **chat** (acknowledgement).
- "Generate a weekly report on team velocity" is a **command** (create_report).
- "Is the weekly report still going out?" is a **query** (general_question).
- "Cancel the Monday briefing" is a **command** (edit_alert).

User's message:
"{user_message}"

Recent conversation history (for context):
{conversation_history}

Known projects:
{known_projects}

Known people:
{known_people}

You MUST respond with valid JSON matching this schema:
{{
  "intent": "<string: query|correction|command|chat>",
  "confidence": <float: 0.0-1.0>,
  "sub_type": "<string: one of the sub-types listed above>",
  "extracted_entities": {{
    "project_name": "<string or null>",
    "person_name": "<string or null>",
    "time_range": "<string or null>",
    "metric": "<string or null>",
    "date": "<string or null>",
    "other": ["<string>", ...]
  }},
  "parameters": {{
    ... (varies by intent type)
  }},
  "reasoning": "<string: one-sentence explanation>"
}}
""",
)
