"""
5-step people identification pipeline.

Orchestrates the full process of discovering, resolving, and enriching
people from all ingested data sources:

1. Build initial directory from Slack users, Jira assignees, Drive metadata.
2. Cross-source entity resolution.
3. AI-powered role detection.
4. Activity level calculation.
5. Persist to MongoDB.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.base import generate_uuid, utc_now
from app.models.person import ActivityLevel
from app.services.people.resolver import MergedPerson, RawPerson, resolve_entities
from app.services.people.role_detector import detect_roles

logger = logging.getLogger(__name__)


async def run_pipeline(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> list[dict[str, Any]]:
    """Run the full 5-step people identification pipeline.

    Args:
        db: Motor database handle.
        ai_adapter: AI adapter instance (can be None for heuristic-only).

    Returns:
        List of person documents that were created or updated.
    """
    logger.info("Starting people identification pipeline")

    # Step 1: Build initial directory
    raw_people = await _step1_build_directory(db)
    logger.info("Step 1: Built directory with %d raw person records", len(raw_people))

    if not raw_people:
        logger.info("No people found in any source, pipeline complete")
        return []

    # Step 2: Cross-source entity resolution
    merged_people = await _step2_resolve_entities(raw_people, db)
    logger.info("Step 2: Resolved to %d merged persons", len(merged_people))

    # Step 3: AI-powered role detection
    people_with_roles = await _step3_detect_roles(merged_people, db, ai_adapter)
    logger.info("Step 3: Role detection complete")

    # Step 4: Activity level calculation
    people_with_activity = await _step4_calculate_activity(people_with_roles, db)
    logger.info("Step 4: Activity levels calculated")

    # Step 5: Persist to MongoDB
    persisted = await _step5_persist(people_with_activity, db)
    logger.info("Step 5: Persisted %d people to MongoDB", len(persisted))

    return persisted


async def _step1_build_directory(
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[RawPerson]:
    """Build initial directory from all sources."""
    raw_people: list[RawPerson] = []

    # Slack users
    async for user in db.people.find({"slack_user_id": {"$ne": None}}):
        raw_people.append(RawPerson(
            name=user.get("name", ""),
            email=user.get("email"),
            slack_user_id=user.get("slack_user_id"),
            jira_username=user.get("jira_username"),
            source="slack",
            source_id=user.get("slack_user_id", ""),
            avatar_url=user.get("avatar_url"),
            extra={
                "person_id": user.get("person_id"),
                "engagement_metrics": user.get("engagement_metrics", {}),
            },
        ))

    # Jira assignees not already in the list
    seen_jira: set[str] = {
        p.jira_username for p in raw_people if p.jira_username
    }

    distinct_assignees = await db.jira_tasks.distinct("assignee")
    distinct_reporters = await db.jira_tasks.distinct("reporter")
    jira_names = set(distinct_assignees + distinct_reporters) - {None, ""}

    for jira_name in jira_names:
        if jira_name in seen_jira:
            continue
        # Check if person already has a jira_username record
        existing = await db.people.find_one({"jira_username": jira_name})
        if existing:
            raw_people.append(RawPerson(
                name=existing.get("name", jira_name),
                email=existing.get("email"),
                slack_user_id=existing.get("slack_user_id"),
                jira_username=jira_name,
                source="jira",
                source_id=jira_name,
                extra={"person_id": existing.get("person_id")},
            ))
        else:
            raw_people.append(RawPerson(
                name=jira_name,
                jira_username=jira_name,
                source="jira",
                source_id=jira_name,
            ))

    # Drive file owners
    distinct_owners = await db.drive_files.distinct("owner")
    if distinct_owners:
        seen_names = {p.name.lower() for p in raw_people}
        for owner in distinct_owners:
            if not owner or owner.lower() in seen_names:
                continue
            raw_people.append(RawPerson(
                name=owner,
                source="gdrive",
                source_id=owner,
            ))

    return raw_people


async def _step2_resolve_entities(
    raw_people: list[RawPerson],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[MergedPerson]:
    """Cross-source entity resolution."""
    return await resolve_entities(raw_people, db)


async def _step3_detect_roles(
    merged_people: list[MergedPerson],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    ai_adapter: Any,
) -> list[dict[str, Any]]:
    """AI-powered role detection.

    Gathers activity data for each person and runs role detection.
    Returns enriched person dicts.
    """
    # Build activity data for each merged person
    people_dicts: list[dict[str, Any]] = []
    activity_data: dict[str, dict[str, Any]] = {}

    for mp in merged_people:
        person_id = ""
        for raw in mp.raw_records:
            if raw.extra.get("person_id"):
                person_id = raw.extra["person_id"]
                break
        if not person_id:
            person_id = generate_uuid()

        person_dict: dict[str, Any] = {
            "person_id": person_id,
            "name": mp.name,
            "email": mp.email,
            "slack_user_id": mp.slack_user_id,
            "jira_username": mp.jira_username,
            "avatar_url": mp.avatar_url,
            "source_ids": mp.source_ids,
        }
        people_dicts.append(person_dict)

        # Gather activity data
        activity = await _gather_activity_data(mp, db)
        activity_data[person_id] = activity

    # Detect roles (skips COO-corrected records)
    coo_corrected_ids: set[str] = set()
    async for doc in db.people.find({"role_source": "coo_corrected"}):
        pid = doc.get("person_id")
        if pid:
            coo_corrected_ids.add(pid)

    # Only detect roles for non-corrected people
    people_for_detection = [p for p in people_dicts if p["person_id"] not in coo_corrected_ids]

    if people_for_detection:
        role_results = await detect_roles(people_for_detection, activity_data, ai_adapter)
        role_map = {r.person_id: r for r in role_results}
    else:
        role_map = {}

    # Merge role results back into person dicts
    enriched: list[dict[str, Any]] = []
    for pd in people_dicts:
        pid = pd["person_id"]
        if pid in coo_corrected_ids:
            # Preserve COO corrections
            existing = await db.people.find_one({"person_id": pid})
            if existing:
                pd["role"] = existing.get("role", "team_member")
                pd["role_source"] = "coo_corrected"
                pd["department"] = existing.get("department")
        elif pid in role_map:
            rd = role_map[pid]
            pd["role"] = rd.role
            pd["role_source"] = "ai_identified"
            pd["department"] = rd.department
        else:
            pd["role"] = "team_member"
            pd["role_source"] = "ai_identified"
            pd["department"] = "Unknown"

        pd["activity_data"] = activity_data.get(pid, {})
        enriched.append(pd)

    return enriched


async def _step4_calculate_activity(
    people: list[dict[str, Any]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[dict[str, Any]]:
    """Calculate activity levels based on engagement metrics and recency."""
    now = datetime.now(timezone.utc)

    for person in people:
        activity = person.get("activity_data", {})
        slack = activity.get("slack", {})
        jira = activity.get("jira", {})

        messages = slack.get("messages_sent", 0)
        threads = slack.get("threads_replied", 0)
        tasks_assigned = jira.get("tasks_assigned", 0)
        tasks_completed = jira.get("tasks_completed", 0)

        # Get last activity date
        last_active = activity.get("last_active_date")
        if last_active and isinstance(last_active, datetime):
            days_since_active = (now - last_active).days
        else:
            days_since_active = 999

        # Calculate activity score
        score = 0
        score += min(messages, 200) / 2  # Up to 100 points from messages
        score += min(threads, 50) * 2    # Up to 100 points from thread participation
        score += min(tasks_assigned, 30) * 3  # Up to 90 points from task assignment
        score += min(tasks_completed, 20) * 4  # Up to 80 points from task completion

        # Apply recency decay
        if days_since_active > 30:
            score *= 0.5
        elif days_since_active > 14:
            score *= 0.7
        elif days_since_active > 7:
            score *= 0.85

        # Map score to activity level
        if score >= 150:
            level = ActivityLevel.VERY_ACTIVE
        elif score >= 80:
            level = ActivityLevel.ACTIVE
        elif score >= 30:
            level = ActivityLevel.MODERATE
        elif score >= 5:
            level = ActivityLevel.QUIET
        else:
            level = ActivityLevel.INACTIVE

        person["activity_level"] = level.value
        person["last_active_date"] = last_active or now

        # Store engagement metrics
        person["engagement_metrics"] = {
            "messages_sent": messages,
            "threads_replied": threads,
            "reactions_given": slack.get("reactions_given", 0),
        }
        person["tasks_assigned"] = tasks_assigned
        person["tasks_completed"] = tasks_completed

    return people


async def _step5_persist(
    people: list[dict[str, Any]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[dict[str, Any]]:
    """Persist resolved people to MongoDB."""
    persisted: list[dict[str, Any]] = []

    for person in people:
        person_id = person["person_id"]

        # Clean up internal fields before persisting
        persist_doc = {
            "person_id": person_id,
            "name": person.get("name", "Unknown"),
            "email": person.get("email"),
            "slack_user_id": person.get("slack_user_id"),
            "jira_username": person.get("jira_username"),
            "avatar_url": person.get("avatar_url"),
            "source_ids": person.get("source_ids", []),
            "role": person.get("role", "team_member"),
            "role_source": person.get("role_source", "ai_identified"),
            "department": person.get("department"),
            "activity_level": person.get("activity_level", "moderate"),
            "last_active_date": person.get("last_active_date", utc_now()),
            "engagement_metrics": person.get("engagement_metrics", {
                "messages_sent": 0,
                "threads_replied": 0,
                "reactions_given": 0,
            }),
            "tasks_assigned": person.get("tasks_assigned", 0),
            "tasks_completed": person.get("tasks_completed", 0),
            "projects": person.get("projects", []),
            "updated_at": utc_now(),
        }

        existing = await db.people.find_one({"person_id": person_id})
        if existing:
            # Preserve COO corrections
            if existing.get("role_source") == "coo_corrected":
                persist_doc["role"] = existing["role"]
                persist_doc["role_source"] = "coo_corrected"
                if existing.get("department"):
                    persist_doc["department"] = existing["department"]

            # Preserve projects list
            existing_projects = existing.get("projects", [])
            if existing_projects:
                persist_doc["projects"] = existing_projects

            await db.people.update_one(
                {"person_id": person_id},
                {"$set": persist_doc},
            )
        else:
            persist_doc["created_at"] = utc_now()
            await db.people.insert_one(persist_doc)

        persisted.append(persist_doc)

    return persisted


async def _gather_activity_data(
    person: MergedPerson,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Gather activity data for a merged person from all sources."""
    activity: dict[str, Any] = {}

    # Slack activity
    if person.slack_user_id:
        pipeline = [
            {"$match": {"user_id": person.slack_user_id}},
            {"$group": {
                "_id": None,
                "messages_sent": {"$sum": 1},
                "threads_replied": {"$sum": {"$cond": [{"$ifNull": ["$thread_ts", False]}, 1, 0]}},
                "reactions_given": {"$sum": {"$size": {"$ifNull": ["$reactions", []]}}},
                "last_message": {"$max": "$timestamp"},
            }},
        ]
        async for agg in db.slack_messages.aggregate(pipeline):
            activity["slack"] = {
                "messages_sent": agg.get("messages_sent", 0),
                "threads_replied": agg.get("threads_replied", 0),
                "reactions_given": agg.get("reactions_given", 0),
            }
            if agg.get("last_message"):
                activity["last_active_date"] = agg["last_message"]

        # Get channels this person is active in
        channels = await db.slack_messages.distinct("channel", {"user_id": person.slack_user_id})
        activity["channels"] = channels

        # Get sample messages for role detection
        sample_cursor = db.slack_messages.find(
            {"user_id": person.slack_user_id},
            {"text": 1, "_id": 0},
        ).sort("timestamp", -1).limit(10)
        sample_messages = [doc["text"] async for doc in sample_cursor]
        activity["sample_messages"] = sample_messages

    # Jira activity
    jira_name = person.jira_username or person.name
    if jira_name:
        assigned_count = await db.jira_tasks.count_documents({"assignee": jira_name})
        completed_count = await db.jira_tasks.count_documents({
            "assignee": jira_name,
            "status": {"$in": ["done", "closed", "resolved"]},
        })

        task_types = await db.jira_tasks.distinct("issue_type", {"assignee": jira_name})
        statuses = await db.jira_tasks.distinct("status", {"assignee": jira_name})

        # Get last activity from Jira
        last_jira = await db.jira_tasks.find_one(
            {"assignee": jira_name},
            sort=[("updated_date", -1)],
        )

        activity["jira"] = {
            "tasks_assigned": assigned_count,
            "tasks_completed": completed_count,
            "task_types": task_types,
            "statuses": statuses,
        }

        if last_jira and last_jira.get("updated_date"):
            jira_last = last_jira["updated_date"]
            current_last = activity.get("last_active_date")
            if current_last is None or (isinstance(jira_last, datetime) and jira_last > current_last):
                activity["last_active_date"] = jira_last

    return activity
