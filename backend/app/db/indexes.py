from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
    """Create all MongoDB indexes required by the application.

    This function is idempotent -- calling it multiple times is safe because
    ``create_indexes`` is a no-op when the index already exists.
    """
    logger.info("Creating MongoDB indexes")

    # ---- people ----
    await db.people.create_indexes(
        [
            IndexModel([("person_id", ASCENDING)], unique=True, name="uq_person_id"),
            IndexModel([("name", TEXT)], name="text_name"),
            IndexModel([("email", ASCENDING)], name="idx_email"),
            IndexModel([("activity_level", ASCENDING)], name="idx_activity_level"),
            IndexModel([("department", ASCENDING)], name="idx_department"),
        ]
    )

    # ---- projects ----
    await db.projects.create_indexes(
        [
            IndexModel([("project_id", ASCENDING)], unique=True, name="uq_project_id"),
            IndexModel([("name", TEXT)], name="text_project_name"),
            IndexModel([("status", ASCENDING)], name="idx_project_status"),
        ]
    )

    # ---- ingestion_jobs ----
    await db.ingestion_jobs.create_indexes(
        [
            IndexModel([("status", ASCENDING)], name="idx_ingest_status"),
            IndexModel([("created_at", DESCENDING)], name="idx_ingest_created"),
        ]
    )

    # ---- analysis_jobs ----
    await db.analysis_jobs.create_indexes(
        [
            IndexModel([("job_id", ASCENDING)], unique=True, name="uq_analysis_job_id"),
            IndexModel([("project_id", ASCENDING)], name="idx_analysis_project"),
        ]
    )

    # ---- conversation_turns ----
    await db.conversation_turns.create_indexes(
        [
            IndexModel([("project_id", ASCENDING)], name="idx_turn_project"),
            IndexModel([("turn_number", ASCENDING)], name="idx_turn_number"),
            IndexModel(
                [("project_id", ASCENDING), ("turn_number", ASCENDING)],
                name="idx_turn_project_number",
            ),
        ]
    )

    # ---- conversation_facts ----
    await db.conversation_facts.create_indexes(
        [
            IndexModel([("project_id", ASCENDING)], name="idx_fact_project"),
            IndexModel([("category", ASCENDING)], name="idx_fact_category"),
            IndexModel([("active", ASCENDING)], name="idx_fact_active"),
            IndexModel(
                [("project_id", ASCENDING), ("category", ASCENDING), ("active", ASCENDING)],
                name="idx_fact_project_cat_active",
            ),
        ]
    )

    # ---- dashboards ----
    await db.dashboards.create_indexes(
        [
            IndexModel([("project_id", ASCENDING)], name="idx_dash_project"),
            IndexModel([("dashboard_type", ASCENDING)], name="idx_dash_type"),
            IndexModel(
                [("project_id", ASCENDING), ("dashboard_type", ASCENDING)],
                name="idx_dash_project_type",
            ),
        ]
    )

    # ---- widgets ----
    await db.widgets.create_indexes(
        [
            IndexModel([("dashboard_id", ASCENDING)], name="idx_widget_dashboard"),
        ]
    )

    # ---- reports ----
    await db.reports.create_indexes(
        [
            IndexModel([("report_type", ASCENDING)], name="idx_report_type"),
            IndexModel([("created_at", DESCENDING)], name="idx_report_created"),
        ]
    )

    # ---- alerts ----
    await db.alerts.create_indexes(
        [
            IndexModel([("active", ASCENDING)], name="idx_alert_active"),
            IndexModel([("alert_type", ASCENDING)], name="idx_alert_type"),
            IndexModel(
                [("active", ASCENDING), ("alert_type", ASCENDING)],
                name="idx_alert_active_type",
            ),
        ]
    )

    # ---- jira_tasks ----
    await db.jira_tasks.create_indexes(
        [
            IndexModel([("task_key", ASCENDING)], unique=True, name="uq_task_key"),
            IndexModel([("project_key", ASCENDING)], name="idx_jira_project"),
            IndexModel([("assignee", ASCENDING)], name="idx_jira_assignee"),
            IndexModel([("status", ASCENDING)], name="idx_jira_status"),
        ]
    )

    # ---- slack_messages ----
    await db.slack_messages.create_indexes(
        [
            IndexModel([("channel", ASCENDING)], name="idx_slack_msg_channel"),
            IndexModel([("timestamp", DESCENDING)], name="idx_slack_msg_ts"),
            IndexModel(
                [("channel", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_slack_msg_channel_ts",
            ),
        ]
    )

    # ---- slack_channels ----
    await db.slack_channels.create_indexes(
        [
            IndexModel([("channel_id", ASCENDING)], unique=True, name="uq_slack_channel_id"),
        ]
    )

    # ---- project_files ----
    await db.project_files.create_indexes(
        [
            IndexModel([("file_id", ASCENDING)], unique=True, name="uq_pf_file_id"),
            IndexModel([("project_id", ASCENDING)], name="idx_pf_project"),
            IndexModel(
                [("project_id", ASCENDING), ("content_hash", ASCENDING)],
                name="idx_pf_project_hash",
            ),
            IndexModel(
                [("project_id", ASCENDING), ("created_at", DESCENDING)],
                name="idx_pf_project_created",
            ),
        ]
    )

    # ---- text_documents (project_id sparse) ----
    await db.text_documents.create_indexes(
        [
            IndexModel(
                [("project_id", ASCENDING)],
                sparse=True,
                name="idx_textdoc_project",
            ),
        ]
    )

    # ---- drive_files ----
    await db.drive_files.create_indexes(
        [
            IndexModel([("file_hash", ASCENDING)], name="idx_drive_file_hash"),
        ]
    )

    # ---- ingestion_hashes ----
    await db.ingestion_hashes.create_indexes(
        [
            IndexModel([("content_hash", ASCENDING)], unique=True, name="uq_content_hash"),
        ]
    )

    # ---- citex_ingestion_state ----
    await db.citex_ingestion_state.create_indexes(
        [
            IndexModel(
                [("project_id", ASCENDING), ("document_id", ASCENDING)],
                unique=True,
                name="uq_citex_project_document",
            ),
            IndexModel(
                [("project_id", ASCENDING), ("source_group", ASCENDING)],
                name="idx_citex_project_group",
            ),
            IndexModel([("updated_at", DESCENDING)], name="idx_citex_updated"),
        ]
    )

    # ---- health_scores ----
    await db.health_scores.create_indexes(
        [
            IndexModel([("project_id", ASCENDING)], name="idx_health_project"),
            IndexModel([("created_at", DESCENDING)], name="idx_health_created"),
            IndexModel(
                [("project_id", ASCENDING), ("created_at", DESCENDING)],
                name="idx_health_project_created",
            ),
        ]
    )

    # ---- briefings ----
    await db.briefings.create_indexes(
        [
            IndexModel([("created_at", DESCENDING)], name="idx_briefing_created"),
        ]
    )

    # ---- audit_log ----
    await db.audit_log.create_indexes(
        [
            IndexModel([("request_id", ASCENDING)], name="idx_audit_request_id"),
            IndexModel([("created_at", DESCENDING)], name="idx_audit_created"),
        ]
    )

    # ---- settings ----
    await db.settings.create_indexes(
        [
            IndexModel([("key", ASCENDING)], unique=True, name="uq_settings_key"),
        ]
    )

    logger.info("MongoDB indexes created successfully")
