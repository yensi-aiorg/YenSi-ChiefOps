"""
Cross-source entity resolution for people identification.

Merges person records discovered across Slack, Jira, and Google Drive
using exact email matching, Slack user ID correlation, and fuzzy name
matching.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class RawPerson:
    """A person identity discovered in a single source."""

    name: str
    email: str | None = None
    slack_user_id: str | None = None
    jira_username: str | None = None
    source: str = ""
    source_id: str = ""
    avatar_url: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MergedPerson:
    """A person identity merged from multiple sources."""

    name: str
    email: str | None = None
    slack_user_id: str | None = None
    jira_username: str | None = None
    avatar_url: str | None = None
    source_ids: list[dict[str, str]] = field(default_factory=list)
    raw_records: list[RawPerson] = field(default_factory=list)


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings.

    Uses the standard dynamic programming approach with O(min(m,n))
    space optimisation.
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _name_similarity(name1: str, name2: str) -> float:
    """Compute a similarity score between two names (0.0 to 1.0).

    Uses normalised Levenshtein distance with additional heuristics
    for name ordering (e.g., "John Smith" vs "Smith, John").
    """
    n1 = name1.strip().lower()
    n2 = name2.strip().lower()

    if n1 == n2:
        return 1.0

    if not n1 or not n2:
        return 0.0

    # Try reversed name matching ("Last, First" vs "First Last")
    parts1 = set(n1.replace(",", " ").split())
    parts2 = set(n2.replace(",", " ").split())
    if parts1 and parts2 and parts1 == parts2:
        return 0.95

    # Levenshtein-based similarity
    max_len = max(len(n1), len(n2))
    distance = _levenshtein_distance(n1, n2)
    similarity = 1.0 - (distance / max_len)

    # Boost if one name contains the other (partial match)
    if n1 in n2 or n2 in n1:
        similarity = max(similarity, 0.8)

    # Boost if first parts match (first name match)
    first1 = n1.split()[0] if n1.split() else ""
    first2 = n2.split()[0] if n2.split() else ""
    if first1 and first2 and first1 == first2 and len(first1) > 2:
        similarity = max(similarity, 0.7)

    return similarity


_FUZZY_THRESHOLD = 0.85


async def resolve_entities(
    raw_people: list[RawPerson],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[MergedPerson]:
    """Resolve identities across sources into merged person records.

    Resolution strategy (in order of priority):
    1. Exact email match
    2. Slack user ID correlation
    3. Fuzzy name matching (Levenshtein similarity >= 0.85)

    Args:
        raw_people: Unresolved person records from all sources.
        db: Motor database handle (used for existing person lookups).

    Returns:
        A list of ``MergedPerson`` objects with deduplicated identities.
    """
    merged: list[MergedPerson] = []

    # Index structures for O(1) lookup
    email_index: dict[str, int] = {}
    slack_id_index: dict[str, int] = {}

    for raw in raw_people:
        matched_idx = _find_match(raw, merged, email_index, slack_id_index)

        if matched_idx is not None:
            _merge_into(merged[matched_idx], raw)
        else:
            # Create new merged person
            mp = MergedPerson(
                name=raw.name,
                email=raw.email,
                slack_user_id=raw.slack_user_id,
                jira_username=raw.jira_username,
                avatar_url=raw.avatar_url,
                source_ids=[{"source": raw.source, "source_id": raw.source_id}]
                if raw.source
                else [],
                raw_records=[raw],
            )
            idx = len(merged)
            merged.append(mp)

            if raw.email:
                email_index[raw.email.lower()] = idx
            if raw.slack_user_id:
                slack_id_index[raw.slack_user_id] = idx

    logger.info(
        "Entity resolution: %d raw records -> %d merged persons",
        len(raw_people),
        len(merged),
    )
    return merged


def _find_match(
    raw: RawPerson,
    merged: list[MergedPerson],
    email_index: dict[str, int],
    slack_id_index: dict[str, int],
) -> int | None:
    """Find an existing merged person that matches the raw record."""

    # Priority 1: Exact email match
    if raw.email:
        email_lower = raw.email.lower()
        if email_lower in email_index:
            return email_index[email_lower]

    # Priority 2: Slack user ID correlation
    if raw.slack_user_id and raw.slack_user_id in slack_id_index:
        return slack_id_index[raw.slack_user_id]

    # Priority 3: Fuzzy name matching
    if raw.name:
        best_score = 0.0
        best_idx: int | None = None
        for i, mp in enumerate(merged):
            score = _name_similarity(raw.name, mp.name)
            if score > best_score and score >= _FUZZY_THRESHOLD:
                best_score = score
                best_idx = i
        if best_idx is not None:
            return best_idx

    return None


def _merge_into(merged: MergedPerson, raw: RawPerson) -> None:
    """Merge a raw person record into an existing merged person."""
    merged.raw_records.append(raw)

    # Prefer the most complete data
    if raw.email and not merged.email:
        merged.email = raw.email
    if raw.slack_user_id and not merged.slack_user_id:
        merged.slack_user_id = raw.slack_user_id
    if raw.jira_username and not merged.jira_username:
        merged.jira_username = raw.jira_username
    if raw.avatar_url and not merged.avatar_url:
        merged.avatar_url = raw.avatar_url

    # Prefer longer / more complete names
    if raw.name and len(raw.name) > len(merged.name):
        merged.name = raw.name

    # Add source reference if not already present
    if raw.source:
        existing_sources = {(s["source"], s["source_id"]) for s in merged.source_ids}
        if (raw.source, raw.source_id) not in existing_sources:
            merged.source_ids.append({"source": raw.source, "source_id": raw.source_id})
