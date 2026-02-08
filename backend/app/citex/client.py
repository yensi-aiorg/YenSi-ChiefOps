"""
Async HTTP client for the Citex RAG extraction service.

Provides document ingestion, semantic querying, and project-level document
deletion with retry logic and graceful degradation when the Citex service
is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.citex.models import (
    CitexIngestRequest,
    CitexQueryRequest,
    CitexQueryResponse,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5  # seconds
_DEFAULT_TIMEOUT = 30.0  # seconds


class CitexClient:
    """Async HTTP client for the Citex REST API.

    Wraps ``httpx.AsyncClient`` with automatic retry logic using
    exponential backoff. All public methods degrade gracefully: if
    the Citex service is unreachable, they return empty results or
    ``False`` rather than raising exceptions.

    Usage::

        client = CitexClient("http://localhost:23100")
        ok = await client.ping()
        result = await client.ingest_document("proj-1", "text ...", {}, "doc.txt")
        chunks = await client.query("proj-1", "How is the project going?")
        await client.close()
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(_DEFAULT_TIMEOUT),
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        """Shut down the underlying HTTP client."""
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response | None:
        """Execute an HTTP request with exponential-backoff retry.

        Returns the ``httpx.Response`` on success or ``None`` after
        all retries are exhausted.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._http.request(
                    method,
                    path,
                    json=json_body,
                    params=params,
                )
                response.raise_for_status()
                return response

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "Citex request %s %s failed (attempt %d/%d): %s – retrying in %.1fs",
                    method,
                    path,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        logger.error(
            "Citex request %s %s failed after %d attempts: %s",
            method,
            path,
            _MAX_RETRIES,
            last_exc,
        )
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """Check whether the Citex service is reachable.

        Returns:
            ``True`` if the ``/health`` endpoint responds with 200,
            ``False`` otherwise.
        """
        response = await self._request_with_retry("GET", "/health")
        if response is not None and response.status_code == 200:
            logger.debug("Citex ping: OK")
            return True
        logger.warning("Citex ping failed – service may be unavailable")
        return False

    async def ingest_document(
        self,
        project_id: str,
        content: str,
        metadata: dict[str, Any],
        filename: str,
    ) -> dict[str, Any]:
        """Ingest a document into Citex for semantic indexing.

        Args:
            project_id: Project scope for the document.
            content: Full text content to ingest.
            metadata: Arbitrary metadata dict (source, author, etc.).
            filename: Original filename.

        Returns:
            The JSON response body from Citex on success, or an empty
            dict if the request failed.
        """
        request = CitexIngestRequest(
            project_id=project_id,
            content=content,
            metadata=metadata,
            filename=filename,
        )
        response = await self._request_with_retry(
            "POST",
            "/api/v1/documents",
            json_body=request.model_dump(),
        )
        if response is not None:
            logger.info(
                "Document ingested into Citex: project=%s filename=%s",
                project_id,
                filename,
            )
            return response.json()

        logger.error(
            "Failed to ingest document into Citex: project=%s filename=%s",
            project_id,
            filename,
        )
        return {}

    async def query(
        self,
        project_id: str,
        query_text: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Perform a semantic search against Citex.

        Args:
            project_id: Project scope for the query.
            query_text: Natural-language query.
            filters: Optional metadata filters.
            top_k: Maximum number of result chunks.

        Returns:
            A list of chunk dicts on success, or an empty list if
            the request failed.
        """
        request = CitexQueryRequest(
            project_id=project_id,
            query=query_text,
            filters=filters,
            top_k=top_k,
        )
        response = await self._request_with_retry(
            "POST",
            "/api/v1/query",
            json_body=request.model_dump(),
        )
        if response is not None:
            data = response.json()
            parsed = CitexQueryResponse(**data)
            logger.debug(
                "Citex query returned %d chunks for project=%s",
                len(parsed.chunks),
                project_id,
            )
            return [chunk.model_dump() for chunk in parsed.chunks]

        logger.warning(
            "Citex query failed; returning empty results for project=%s",
            project_id,
        )
        return []

    async def delete_project_documents(self, project_id: str) -> bool:
        """Delete all documents for a project from Citex.

        Args:
            project_id: Project whose documents should be removed.

        Returns:
            ``True`` if deletion succeeded, ``False`` otherwise.
        """
        response = await self._request_with_retry(
            "DELETE",
            "/api/v1/documents",
            params={"project_id": project_id},
        )
        if response is not None:
            logger.info("Deleted Citex documents for project=%s", project_id)
            return True

        logger.error("Failed to delete Citex documents for project=%s", project_id)
        return False
