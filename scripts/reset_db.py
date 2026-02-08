#!/usr/bin/env python3
"""
Database reset script for ChiefOps.

Drops all collections in the specified MongoDB database. This is a
destructive operation intended for development and testing environments.
Prompts for confirmation before proceeding unless --force is specified.

Usage:
    python scripts/reset_db.py
    python scripts/reset_db.py --mongo-url mongodb://localhost:27017 --db chiefops
    python scripts/reset_db.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reset_db")

# Collections managed by ChiefOps
MANAGED_COLLECTIONS = [
    "people",
    "projects",
    "jira_tasks",
    "slack_messages",
    "slack_channels",
    "drive_files",
    "ingestion_jobs",
    "ingestion_file_store",
    "ingestion_hashes",
    "conversation_messages",
    "conversation_turns",
    "memory_streams",
    "hard_facts",
    "compacted_summaries",
    "reports",
    "report_history",
    "dashboards",
    "dashboard_widgets",
    "project_analyses",
    "alerts",
    "settings",
]


async def reset(mongo_url: str, db_name: str, force: bool = False) -> None:
    """Drop all managed collections from the database.

    Args:
        mongo_url: MongoDB connection URI.
        db_name: Database name to reset.
        force: If True, skip confirmation prompt.
    """
    if not force:
        print(f"\nThis will DROP ALL COLLECTIONS in database '{db_name}' at {mongo_url}")
        print("This action is irreversible.\n")
        confirmation = input("Type the database name to confirm: ").strip()
        if confirmation != db_name:
            print("Confirmation failed. Aborting.")
            sys.exit(1)

    client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_url)  # type: ignore[type-arg]
    db = client[db_name]

    logger.info("Resetting database: %s", db_name)

    # Get all existing collections
    existing_collections = await db.list_collection_names()

    dropped_count = 0
    for collection_name in MANAGED_COLLECTIONS:
        if collection_name in existing_collections:
            doc_count = await db[collection_name].count_documents({})
            await db[collection_name].drop()
            logger.info("  Dropped collection: %s (%d documents)", collection_name, doc_count)
            dropped_count += 1

    # Also drop any other collections that may exist
    remaining = set(existing_collections) - set(MANAGED_COLLECTIONS)
    for collection_name in sorted(remaining):
        if collection_name.startswith("system."):
            continue  # Skip MongoDB system collections
        doc_count = await db[collection_name].count_documents({})
        await db[collection_name].drop()
        logger.info("  Dropped extra collection: %s (%d documents)", collection_name, doc_count)
        dropped_count += 1

    logger.info("Reset complete. Dropped %d collections from '%s'.", dropped_count, db_name)
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset the ChiefOps database by dropping all collections."
    )
    parser.add_argument(
        "--mongo-url",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI (default: mongodb://localhost:27017)",
    )
    parser.add_argument(
        "--db",
        default="chiefops",
        help="Database name (default: chiefops)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    args = parser.parse_args()

    asyncio.run(reset(args.mongo_url, args.db, args.force))


if __name__ == "__main__":
    main()
