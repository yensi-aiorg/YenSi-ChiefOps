#!/usr/bin/env python3
"""
Sample data seeder for ChiefOps.

Creates realistic sample people, projects, tasks, conversation history,
and memory data for demo and development environments. Safe to run
multiple times -- existing data is cleared before seeding.

Usage:
    python scripts/seed_data.py
    python scripts/seed_data.py --mongo-url mongodb://localhost:23102 --db chiefops
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("seed_data")


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


# ---------------------------------------------------------------------------
# Sample data generators
# ---------------------------------------------------------------------------


def _generate_people() -> list[dict]:
    """Generate sample person records."""
    return [
        {
            "person_id": "person-001",
            "name": "Sarah Chen",
            "email": "sarah.chen@yensi.dev",
            "role": "Engineering Lead",
            "role_source": "ai_identified",
            "department": "Platform Engineering",
            "activity_level": "very_active",
            "last_active_date": _days_ago(0),
            "avatar_url": None,
            "slack_user_id": "U01SARAH",
            "jira_username": "schen",
            "tasks_assigned": 5,
            "tasks_completed": 23,
            "engagement_metrics": {
                "messages_sent": 312,
                "threads_replied": 98,
                "reactions_given": 187,
            },
            "source_ids": [
                {"source": "slack", "source_id": "U01SARAH"},
                {"source": "jira", "source_id": "schen"},
            ],
            "projects": ["proj-001", "proj-002"],
            "created_at": _days_ago(90),
            "updated_at": _now(),
        },
        {
            "person_id": "person-002",
            "name": "Marcus Rivera",
            "email": "marcus.rivera@yensi.dev",
            "role": "Senior Backend Developer",
            "role_source": "ai_identified",
            "department": "Platform Engineering",
            "activity_level": "active",
            "last_active_date": _days_ago(1),
            "avatar_url": None,
            "slack_user_id": "U02MARCUS",
            "jira_username": "mrivera",
            "tasks_assigned": 3,
            "tasks_completed": 18,
            "engagement_metrics": {
                "messages_sent": 189,
                "threads_replied": 67,
                "reactions_given": 92,
            },
            "source_ids": [
                {"source": "slack", "source_id": "U02MARCUS"},
                {"source": "jira", "source_id": "mrivera"},
            ],
            "projects": ["proj-001"],
            "created_at": _days_ago(90),
            "updated_at": _now(),
        },
        {
            "person_id": "person-003",
            "name": "Aisha Patel",
            "email": "aisha.patel@yensi.dev",
            "role": "Frontend Developer",
            "role_source": "ai_identified",
            "department": "Product Engineering",
            "activity_level": "active",
            "last_active_date": _days_ago(0),
            "avatar_url": None,
            "slack_user_id": "U03AISHA",
            "jira_username": "apatel",
            "tasks_assigned": 4,
            "tasks_completed": 15,
            "engagement_metrics": {
                "messages_sent": 156,
                "threads_replied": 43,
                "reactions_given": 201,
            },
            "source_ids": [
                {"source": "slack", "source_id": "U03AISHA"},
                {"source": "jira", "source_id": "apatel"},
            ],
            "projects": ["proj-002", "proj-003"],
            "created_at": _days_ago(60),
            "updated_at": _now(),
        },
        {
            "person_id": "person-004",
            "name": "David Kim",
            "email": "david.kim@yensi.dev",
            "role": "DevOps Engineer",
            "role_source": "coo_corrected",
            "department": "Infrastructure",
            "activity_level": "moderate",
            "last_active_date": _days_ago(3),
            "avatar_url": None,
            "slack_user_id": "U04DAVID",
            "jira_username": "dkim",
            "tasks_assigned": 2,
            "tasks_completed": 11,
            "engagement_metrics": {
                "messages_sent": 87,
                "threads_replied": 31,
                "reactions_given": 45,
            },
            "source_ids": [
                {"source": "slack", "source_id": "U04DAVID"},
                {"source": "jira", "source_id": "dkim"},
            ],
            "projects": ["proj-001", "proj-003"],
            "created_at": _days_ago(120),
            "updated_at": _now(),
        },
        {
            "person_id": "person-005",
            "name": "Elena Vasquez",
            "email": "elena.vasquez@yensi.dev",
            "role": "Product Manager",
            "role_source": "ai_identified",
            "department": "Product",
            "activity_level": "active",
            "last_active_date": _days_ago(0),
            "avatar_url": None,
            "slack_user_id": "U05ELENA",
            "jira_username": "evasquez",
            "tasks_assigned": 1,
            "tasks_completed": 8,
            "engagement_metrics": {
                "messages_sent": 234,
                "threads_replied": 112,
                "reactions_given": 167,
            },
            "source_ids": [
                {"source": "slack", "source_id": "U05ELENA"},
            ],
            "projects": ["proj-001", "proj-002", "proj-003"],
            "created_at": _days_ago(90),
            "updated_at": _now(),
        },
    ]


def _generate_projects() -> list[dict]:
    """Generate sample project records."""
    return [
        {
            "project_id": "proj-001",
            "name": "Platform Migration",
            "description": "Migrate legacy monolithic services to cloud-native microservices on Kubernetes.",
            "status": "active",
            "health_score": "at_risk",
            "deadline": datetime(2026, 3, 15, tzinfo=timezone.utc),
            "team_members": ["person-001", "person-002", "person-004"],
            "open_tasks": 14,
            "completed_tasks": 28,
            "total_tasks": 42,
            "key_risks": [
                "Auth service v2 API contract not finalized",
                "Key engineer PTO during cutover window",
                "Staging environment capacity insufficient",
            ],
            "key_milestones": [
                {"name": "Phase 1: Planning", "target_date": "2025-12-01", "status": "completed"},
                {"name": "Phase 2: Data Migration", "target_date": "2026-02-01", "status": "completed"},
                {"name": "Phase 3: Service Cutover", "target_date": "2026-03-15", "status": "in_progress"},
            ],
            "recent_activity": [],
            "last_analysis_at": _now(),
            "created_at": _days_ago(120),
            "updated_at": _now(),
        },
        {
            "project_id": "proj-002",
            "name": "Customer Dashboard Redesign",
            "description": "Complete UX overhaul of the customer-facing analytics dashboard.",
            "status": "active",
            "health_score": "healthy",
            "deadline": datetime(2026, 4, 30, tzinfo=timezone.utc),
            "team_members": ["person-001", "person-003", "person-005"],
            "open_tasks": 8,
            "completed_tasks": 22,
            "total_tasks": 30,
            "key_risks": [
                "Design system migration may introduce visual regressions",
            ],
            "key_milestones": [
                {"name": "Design System Migration", "target_date": "2026-02-15", "status": "in_progress"},
                {"name": "Beta Launch", "target_date": "2026-03-30", "status": "pending"},
                {"name": "GA Release", "target_date": "2026-04-30", "status": "pending"},
            ],
            "recent_activity": [],
            "last_analysis_at": _now(),
            "created_at": _days_ago(60),
            "updated_at": _now(),
        },
        {
            "project_id": "proj-003",
            "name": "Data Pipeline Upgrade",
            "description": "Upgrade the real-time data pipeline from Kafka 2.x to Kafka 3.x with Schema Registry.",
            "status": "active",
            "health_score": "healthy",
            "deadline": datetime(2026, 5, 31, tzinfo=timezone.utc),
            "team_members": ["person-003", "person-004", "person-005"],
            "open_tasks": 6,
            "completed_tasks": 4,
            "total_tasks": 10,
            "key_risks": [],
            "key_milestones": [
                {"name": "Schema Registry Setup", "target_date": "2026-03-01", "status": "pending"},
                {"name": "Producer Migration", "target_date": "2026-04-15", "status": "pending"},
                {"name": "Consumer Migration", "target_date": "2026-05-31", "status": "pending"},
            ],
            "recent_activity": [],
            "last_analysis_at": _now(),
            "created_at": _days_ago(30),
            "updated_at": _now(),
        },
    ]


def _generate_jira_tasks() -> list[dict]:
    """Generate sample Jira task records."""
    return [
        {
            "task_key": "PLAT-401",
            "project_key": "PLAT",
            "summary": "Implement auth service v2 token validation",
            "description": "Update the token validation logic to support the new JWT format with Ed25519 signatures.",
            "status": "In Progress",
            "assignee": "Sarah Chen",
            "reporter": "Marcus Rivera",
            "priority": "High",
            "created_date": _days_ago(14),
            "updated_date": _days_ago(1),
            "story_points": 5.0,
            "sprint": "Sprint 14",
            "labels": ["backend", "auth", "migration"],
            "comments": ["Started implementation.", "Blocked on API contract."],
            "created_at": _days_ago(14),
            "updated_at": _days_ago(1),
        },
        {
            "task_key": "PLAT-415",
            "project_key": "PLAT",
            "summary": "Set up staging Kubernetes cluster for migration testing",
            "description": "Provision a dedicated staging K8s cluster with matching production specs.",
            "status": "Done",
            "assignee": "David Kim",
            "reporter": "Sarah Chen",
            "priority": "High",
            "created_date": _days_ago(21),
            "updated_date": _days_ago(5),
            "story_points": 8.0,
            "sprint": "Sprint 13",
            "labels": ["infra", "kubernetes"],
            "comments": ["Cluster provisioned.", "Load testing passed."],
            "created_at": _days_ago(21),
            "updated_at": _days_ago(5),
        },
        {
            "task_key": "PLAT-422",
            "project_key": "PLAT",
            "summary": "Write data migration rollback runbook",
            "description": "Document the step-by-step rollback procedure for the database schema migration.",
            "status": "To Do",
            "assignee": "Marcus Rivera",
            "reporter": "Elena Vasquez",
            "priority": "Critical",
            "created_date": _days_ago(7),
            "updated_date": _days_ago(7),
            "story_points": 3.0,
            "sprint": "Sprint 14",
            "labels": ["documentation", "migration"],
            "comments": [],
            "created_at": _days_ago(7),
            "updated_at": _days_ago(7),
        },
        {
            "task_key": "DASH-101",
            "project_key": "DASH",
            "summary": "Implement new chart component library",
            "description": "Replace Recharts with the new ECharts-based component library.",
            "status": "In Progress",
            "assignee": "Aisha Patel",
            "reporter": "Elena Vasquez",
            "priority": "Medium",
            "created_date": _days_ago(10),
            "updated_date": _days_ago(2),
            "story_points": 8.0,
            "sprint": "Sprint 14",
            "labels": ["frontend", "charts"],
            "comments": ["First prototype ready for review."],
            "created_at": _days_ago(10),
            "updated_at": _days_ago(2),
        },
        {
            "task_key": "PIPE-201",
            "project_key": "PIPE",
            "summary": "Evaluate Kafka 3.x compatibility with existing consumers",
            "description": "Run compatibility matrix tests against all production consumer groups.",
            "status": "To Do",
            "assignee": "David Kim",
            "reporter": "Aisha Patel",
            "priority": "Medium",
            "created_date": _days_ago(5),
            "updated_date": _days_ago(5),
            "story_points": 5.0,
            "sprint": "Sprint 15",
            "labels": ["pipeline", "kafka"],
            "comments": [],
            "created_at": _days_ago(5),
            "updated_at": _days_ago(5),
        },
    ]


def _generate_conversation_messages() -> list[dict]:
    """Generate sample conversation messages."""
    return [
        {
            "message_id": _uuid(),
            "role": "user",
            "content": "What's the status of the Platform Migration project?",
            "project_id": "proj-001",
            "created_at": _days_ago(1),
            "metadata": None,
        },
        {
            "message_id": _uuid(),
            "role": "assistant",
            "content": (
                "The Platform Migration project is currently at risk. Phase 2 (Data Migration) "
                "completed on schedule, but Phase 3 (Service Cutover) is delayed by approximately "
                "8 working days due to the unresolved auth service v2 API contract.\n\n"
                "Key concerns:\n"
                "- Auth service v2 API contract not finalized (5 days blocked)\n"
                "- Marcus Rivera has PTO scheduled during the cutover window\n"
                "- Staging capacity may be insufficient for full load testing\n\n"
                "I recommend escalating the API contract decision to VP Engineering today."
            ),
            "project_id": "proj-001",
            "created_at": _days_ago(1),
            "metadata": {
                "sources_used": [
                    {"source_type": "jira", "item_count": 14},
                    {"source_type": "slack", "item_count": 47},
                ],
            },
        },
        {
            "message_id": _uuid(),
            "role": "user",
            "content": "Marcus is actually a Staff Engineer, not Senior Backend Developer.",
            "project_id": None,
            "created_at": _days_ago(0),
            "metadata": None,
        },
        {
            "message_id": _uuid(),
            "role": "assistant",
            "content": (
                "Understood. I've updated Marcus Rivera's role from Senior Backend Developer "
                "to Staff Engineer. This correction has been saved and will persist through "
                "future reprocessing.\n\n"
                "Updated record:\n"
                "- Name: Marcus Rivera\n"
                "- Role: Staff Engineer (COO-corrected)\n"
                "- Department: Platform Engineering"
            ),
            "project_id": None,
            "created_at": _days_ago(0),
            "metadata": {
                "correction_applied": {
                    "entity": "person",
                    "person_id": "person-002",
                    "field": "role",
                    "old_value": "Senior Backend Developer",
                    "new_value": "Staff Engineer",
                },
            },
        },
    ]


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------


async def seed(mongo_url: str, db_name: str) -> None:
    """Seed the database with sample data."""
    client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_url)  # type: ignore[type-arg]
    db = client[db_name]

    logger.info("Seeding database: %s", db_name)

    # Clear existing data
    collections = ["people", "projects", "jira_tasks", "conversation_messages"]
    for coll_name in collections:
        count = await db[coll_name].count_documents({})
        if count > 0:
            await db[coll_name].delete_many({})
            logger.info("  Cleared %d documents from %s", count, coll_name)

    # Seed people
    people = _generate_people()
    await db["people"].insert_many(people)
    logger.info("  Inserted %d people", len(people))

    # Seed projects
    projects = _generate_projects()
    await db["projects"].insert_many(projects)
    logger.info("  Inserted %d projects", len(projects))

    # Seed Jira tasks
    tasks = _generate_jira_tasks()
    await db["jira_tasks"].insert_many(tasks)
    logger.info("  Inserted %d Jira tasks", len(tasks))

    # Seed conversation messages
    messages = _generate_conversation_messages()
    await db["conversation_messages"].insert_many(messages)
    logger.info("  Inserted %d conversation messages", len(messages))

    logger.info("Seeding complete.")
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ChiefOps database with sample data.")
    parser.add_argument(
        "--mongo-url",
        default="mongodb://localhost:23102",
        help="MongoDB connection URI (default: mongodb://localhost:23102)",
    )
    parser.add_argument(
        "--db",
        default="chiefops",
        help="Database name (default: chiefops)",
    )
    args = parser.parse_args()

    asyncio.run(seed(args.mongo_url, args.db))


if __name__ == "__main__":
    main()
