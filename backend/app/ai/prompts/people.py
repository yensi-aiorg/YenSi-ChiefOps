"""
People-related prompts for role detection, entity resolution, and corrections.

These prompts help ChiefOps understand who people are, what they do, and how
to handle ambiguous or corrected people references from the COO.
"""

from __future__ import annotations

from .base import PromptTemplate

# ---------------------------------------------------------------------------
# Role detection: infer a person's role from their activity data
# ---------------------------------------------------------------------------

ROLE_DETECTION_PROMPT = PromptTemplate(
    name="role_detection",
    template="""\
You are analysing activity data for a person in an organisation to detect their \
likely role and seniority level.

Analyse the following activity signals and determine:
1. The most likely job role/title for this person.
2. Your confidence level (0.0 to 1.0).
3. Specific evidence from the activity data that supports your conclusion.
4. Up to 3 alternative roles that could also fit, with their confidence levels.
5. The seniority level: "junior", "mid", "senior", "staff", "principal", or "executive".

Activity signals to consider:
- Code review patterns: Do they review others' work? Are they an approver?
- Task types: Are they doing implementation, architecture, management, or coordination?
- Communication patterns: Do they send updates, lead meetings, or delegate work?
- Document authorship: Do they write specs, RFCs, or status reports?
- Cross-team interaction: Do they work within one team or across multiple teams?

Person's name: {person_name}
Person's known department: {department}

Activity data:
{activity_data}

You MUST respond with valid JSON matching this schema:
{{
  "detected_role": "<string: most likely role title>",
  "confidence": <float: 0.0-1.0>,
  "evidence": ["<string: evidence point 1>", "<string: evidence point 2>", ...],
  "alternative_roles": [
    {{"role": "<string>", "confidence": <float>}},
    ...
  ],
  "seniority_level": "<string: junior|mid|senior|staff|principal|executive>"
}}
""",
)

# ---------------------------------------------------------------------------
# Entity resolution: disambiguate fuzzy people matches
# ---------------------------------------------------------------------------

ENTITY_RESOLUTION_PROMPT = PromptTemplate(
    name="entity_resolution",
    template="""\
The COO referred to a person using an ambiguous or partial reference. Your job is \
to determine which person in the organisation they most likely mean.

Consider the following factors when ranking matches:
1. Name similarity (exact match, first name match, nickname match, typo tolerance).
2. Contextual relevance: Is this person involved in the projects or topics currently \
being discussed?
3. Recency: Has this person been mentioned recently in the conversation?
4. Role relevance: Does this person's role align with the context of the question?

If there is a single high-confidence match (>0.8), mark the result as unambiguous.
If the top two matches are within 0.2 confidence of each other, mark the result as \
ambiguous and note that clarification is needed.

The COO's reference: "{query}"

Known people in the organisation:
{people_list}

Current conversation context:
{conversation_context}

Projects currently being discussed:
{active_projects}

You MUST respond with valid JSON matching this schema:
{{
  "resolution": {{
    "query": "<string: the original reference>",
    "matches": [
      {{
        "name": "<string: full name>",
        "confidence": <float: 0.0-1.0>,
        "department": "<string>",
        "role": "<string>",
        "match_reason": "<string: why this person matched>"
      }}
    ],
    "best_match": "<string: full name of top match or null if too ambiguous>",
    "ambiguous": <boolean: true if clarification is needed>
  }}
}}
""",
)

# ---------------------------------------------------------------------------
# Correction interpretation: parse COO corrections about people
# ---------------------------------------------------------------------------

CORRECTION_INTERPRETATION_PROMPT = PromptTemplate(
    name="correction_interpretation",
    template="""\
The COO is correcting information about a person. Parse their correction statement \
to understand exactly what needs to be updated.

Determine:
1. The type of correction: "attribute_update" (changing a field value), \
"relationship_update" (changing who reports to whom or team membership), \
"merge" (two records refer to the same person), or "split" (one record \
actually refers to two different people).
2. Which person is being corrected (entity identifier).
3. Which field is being changed.
4. The old value (if inferrable from context).
5. The new value.
6. Whether this correction should be applied automatically or requires \
confirmation (e.g., a merge should always require confirmation).

COO's correction statement:
"{correction_text}"

Current data for the person being discussed:
{person_data}

Conversation context:
{conversation_context}

You MUST respond with valid JSON matching this schema:
{{
  "correction": {{
    "type": "<string: attribute_update|relationship_update|merge|split>",
    "entity_type": "person",
    "entity_identifier": "<string: person name or ID>",
    "field": "<string: field being corrected>",
    "old_value": "<string or null: previous value if known>",
    "new_value": "<string: corrected value>",
    "confidence": <float: 0.0-1.0>,
    "reasoning": "<string: explanation of how you interpreted the correction>",
    "requires_confirmation": <boolean>
  }}
}}
""",
)
