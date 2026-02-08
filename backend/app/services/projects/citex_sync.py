"""
Citex synchronisation and retrieval helpers for project analysis.

This module ensures project-relevant Jira, Slack, and document data are
ingested into Citex before AI analysis runs, and provides a unified context
bundle retrieved from Citex for downstream prompts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.citex.client import CitexClient
from app.config import get_settings
from app.models.base import utc_now
from app.services.ingestion.hasher import compute_hash

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_NON_PROJECT_SOURCES = {"jira", "slack", "slack_api"}


def _doc_id(doc: dict[str, Any]) -> str:
    """Build a stable identifier for ingestion state tracking."""
    explicit_id = doc.get("document_id")
    if explicit_id:
        return str(explicit_id)
    source = str(doc.get("source", "unknown"))
    source_ref = str(doc.get("source_ref", "unknown"))
    return f"{source}:{source_ref}"


def _doc_hash(doc: dict[str, Any]) -> str:
    """Return content hash for a text document, computing one if missing."""
    existing = doc.get("content_hash")
    if isinstance(existing, str) and existing:
        return existing
    content = str(doc.get("content", ""))
    return compute_hash(content.encode("utf-8"))


def _is_doc_relevant_to_project(doc: dict[str, Any], tokens: list[str]) -> bool:
    """Heuristic relevance check for project documentation."""
    haystack = " ".join(
        [
            str(doc.get("title", "")),
            str(doc.get("source_ref", "")),
            str(doc.get("filename", "")),
            str(doc.get("content", ""))[:6000],  # cap scan size for speed
        ]
    ).lower()
    return any(token in haystack for token in tokens if len(token) >= 3)


async def _load_project_documents(
    project: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> list[dict[str, Any]]:
    """Load project-related documentation from text_documents."""
    project_name = str(project.get("name", "")).lower()
    jira_keys = [str(k).lower() for k in project.get("jira_project_keys", []) if k]
    slack_channels = [str(c).lower() for c in project.get("slack_channels", []) if c]
    tokens = [project_name, *jira_keys, *slack_channels]

    docs = await (
        db.text_documents.find({"source": {"$nin": list(_NON_PROJECT_SOURCES)}})
        .sort("created_at", -1)
        .limit(200)
        .to_list(length=200)
    )
    if not tokens:
        return docs[:25]

    relevant = [doc for doc in docs if _is_doc_relevant_to_project(doc, tokens)]
    if relevant:
        return relevant[:50]
    return docs[:25]


async def _ingest_group(
    *,
    project_id: str,
    group_name: str,
    docs: list[dict[str, Any]],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
    citex_client: CitexClient,
) -> dict[str, Any]:
    """Ingest one source group and record detailed ingestion state."""
    state_col = db["citex_ingestion_state"]
    ingested = 0
    skipped = 0
    failed = 0
    errors: list[str] = []

    for doc in docs:
        content = str(doc.get("content", "")).strip()
        if not content:
            skipped += 1
            continue

        source = str(doc.get("source", "unknown"))
        source_ref = str(doc.get("source_ref", "unknown"))
        document_id = _doc_id(doc)
        content_hash = _doc_hash(doc)
        filename = str(doc.get("title") or doc.get("filename") or document_id)

        state_key = {
            "project_id": project_id,
            "source_group": group_name,
            "document_id": document_id,
        }
        existing_state = await state_col.find_one(state_key)

        if (
            existing_state
            and existing_state.get("content_hash") == content_hash
            and existing_state.get("status") == "ingested"
        ):
            skipped += 1
            continue

        metadata = {
            "source_group": group_name,
            "source": source,
            "source_ref": source_ref,
            "title": str(doc.get("title", "")),
            "content_hash": content_hash,
            "synced_at": utc_now().isoformat(),
        }

        response = await citex_client.ingest_document(
            project_id=project_id,
            content=content,
            metadata=metadata,
            filename=filename,
        )

        if response:
            ingested += 1
            await state_col.update_one(
                state_key,
                {
                    "$set": {
                        "project_id": project_id,
                        "source_group": group_name,
                        "source": source,
                        "source_ref": source_ref,
                        "document_id": document_id,
                        "content_hash": content_hash,
                        "status": "ingested",
                        "citex_response": response,
                        "last_ingested_at": utc_now(),
                        "updated_at": utc_now(),
                    },
                    "$setOnInsert": {"created_at": utc_now()},
                },
                upsert=True,
            )

            # Mark text doc as indexed in Citex (best-effort metadata).
            if doc.get("document_id"):
                await db.text_documents.update_one(
                    {"document_id": doc["document_id"]},
                    {
                        "$set": {
                            "indexed_in_citex": True,
                            "citex_last_ingested_at": utc_now(),
                            "updated_at": utc_now(),
                        }
                    },
                )
            continue

        failed += 1
        error_msg = f"{group_name}:{document_id} ingestion failed"
        errors.append(error_msg)
        await state_col.update_one(
            state_key,
            {
                "$set": {
                    "project_id": project_id,
                    "source_group": group_name,
                    "source": source,
                    "source_ref": source_ref,
                    "document_id": document_id,
                    "content_hash": content_hash,
                    "status": "failed",
                    "last_error": error_msg,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )

    return {
        "group": group_name,
        "total": len(docs),
        "ingested": ingested,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }


async def sync_project_to_citex(
    project_id: str,
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Ensure project data is ingested into Citex in the required order.

    Ingestion order is strict:
    1. Jira
    2. Slack
    3. Project documents

    Returns:
        A summary dict with per-group counts and health flags.
    """
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        return {
            "status": "project_not_found",
            "citex_available": False,
            "groups": [],
            "errors": [f"Project '{project_id}' not found"],
            "synced_at": utc_now(),
        }

    jira_keys = [k for k in project.get("jira_project_keys", []) if k]
    slack_channels = [c for c in project.get("slack_channels", []) if c]

    jira_docs = await db.text_documents.find(
        {"source": "jira", "source_ref": {"$in": jira_keys}}
    ).to_list(length=500)
    slack_docs = await db.text_documents.find(
        {"source": {"$in": ["slack", "slack_api"]}, "source_ref": {"$in": slack_channels}}
    ).to_list(length=500)
    doc_files = await _load_project_documents(project, db)

    # Include files uploaded directly to this project via the Files tab.
    project_uploaded_docs = await db.text_documents.find(
        {"project_id": project_id}
    ).to_list(length=200)
    if project_uploaded_docs:
        existing_ids = {_doc_id(d) for d in doc_files}
        for pdoc in project_uploaded_docs:
            if _doc_id(pdoc) not in existing_ids:
                doc_files.append(pdoc)

    settings = get_settings()
    citex_client = CitexClient(settings.CITEX_API_URL)
    groups: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        citex_available = await citex_client.ping()
        if not citex_available:
            summary = {
                "status": "citex_unavailable",
                "citex_available": False,
                "groups": [
                    {"group": "jira", "total": len(jira_docs), "ingested": 0, "skipped": 0, "failed": 0},
                    {"group": "slack", "total": len(slack_docs), "ingested": 0, "skipped": 0, "failed": 0},
                    {"group": "docs", "total": len(doc_files), "ingested": 0, "skipped": 0, "failed": 0},
                ],
                "errors": ["Citex service is unavailable"],
                "synced_at": utc_now(),
            }
            await db.projects.update_one(
                {"project_id": project_id},
                {"$set": {"citex_ingestion": summary, "updated_at": utc_now()}},
            )
            return summary

        # Required order: Jira -> Slack -> Docs.
        groups.append(
            await _ingest_group(
                project_id=project_id,
                group_name="jira",
                docs=jira_docs,
                db=db,
                citex_client=citex_client,
            )
        )
        groups.append(
            await _ingest_group(
                project_id=project_id,
                group_name="slack",
                docs=slack_docs,
                db=db,
                citex_client=citex_client,
            )
        )
        groups.append(
            await _ingest_group(
                project_id=project_id,
                group_name="docs",
                docs=doc_files,
                db=db,
                citex_client=citex_client,
            )
        )

        for group in groups:
            errors.extend(group.get("errors", []))

        failed_total = sum(int(group.get("failed", 0)) for group in groups)
        status = "ready" if failed_total == 0 else "completed_with_errors"
        summary = {
            "status": status,
            "citex_available": True,
            "groups": groups,
            "errors": errors,
            "synced_at": utc_now(),
        }

        await db.projects.update_one(
            {"project_id": project_id},
            {"$set": {"citex_ingestion": summary, "updated_at": utc_now()}},
        )
        return summary

    finally:
        await citex_client.close()


def _format_chunks(chunks: list[dict[str, Any]]) -> str:
    """Format Citex chunks into prompt-ready text."""
    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source") or chunk.get("source", "unknown")
        source_ref = metadata.get("source_ref", "")
        content = str(chunk.get("content", "")).strip()
        if not content:
            continue
        header = f"[{idx}] {source}"
        if source_ref:
            header += f" ({source_ref})"
        lines.append(header)
        lines.append(content[:1000])
        lines.append("")
    return "\n".join(lines).strip()


async def get_project_citex_context(
    project_id: str,
    *,
    top_k_per_query: int = 6,
) -> dict[str, Any]:
    """Retrieve unified Citex context for project analysis prompts."""
    settings = get_settings()
    citex_client = CitexClient(settings.CITEX_API_URL)

    queries = [
        "Summarize project scope, client goals, technical architecture, and key constraints.",
        "What happened in Slack in the last week? Include blockers, decisions, owners, and commitments.",
        "List Jira owners, currently in-progress tasks, blocked tasks, backlog pipeline, and due dates.",
        "Extract project deadline, milestones, and timeline dependencies from all available documents.",
    ]

    try:
        if not await citex_client.ping():
            return {
                "available": False,
                "chunk_count": 0,
                "text": "",
                "queries": queries,
            }

        dedup: dict[str, dict[str, Any]] = {}
        for query in queries:
            chunks = await citex_client.query(
                project_id=project_id,
                query_text=query,
                top_k=top_k_per_query,
            )
            for chunk in chunks:
                chunk_key = str(chunk.get("chunk_id") or compute_hash(str(chunk).encode("utf-8")))
                dedup[chunk_key] = chunk

        ordered_chunks = sorted(
            dedup.values(),
            key=lambda c: float(c.get("score", 0.0)),
            reverse=True,
        )
        formatted = _format_chunks(ordered_chunks[:40])
        return {
            "available": True,
            "chunk_count": len(ordered_chunks),
            "text": formatted,
            "queries": queries,
        }
    finally:
        await citex_client.close()
