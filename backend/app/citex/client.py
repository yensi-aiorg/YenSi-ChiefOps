"""
Async HTTP client for the Citex RAG extraction service.

Provides document ingestion, semantic querying, and project-level document
delete with retry logic and graceful degradation when the Citex service
is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

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

        client = CitexClient("http://localhost:20161")
        ok = await client.ping()
        result = await client.ingest_document("proj-1", "text ...", {}, "doc.txt")
        chunks = await client.query("proj-1", "How is the project going?")
        await client.close()
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        user_id: str = "default_user",
        scope_id: str = "default_scope",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(_DEFAULT_TIMEOUT),
        )
        self._api_key = (api_key or "").strip()
        self._default_user_id = user_id.strip() or "default_user"
        self._default_scope_id = scope_id.strip() or "default_scope"

    async def close(self) -> None:
        """Shut down the underlying HTTP client."""
        await self._http.aclose()

    def _resolve_user_id(self, user_id: str | None = None) -> str:
        if user_id and user_id.strip():
            return user_id.strip()
        return self._default_user_id

    def _resolve_scope_id(self, scope_id: str | None = None) -> str:
        if scope_id and scope_id.strip():
            return scope_id.strip()
        return self._default_scope_id

    def _build_headers(
        self,
        *,
        user_id: str | None = None,
        scope_id: str | None = None,
        include_api_key: bool = True,
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "X-Citex-User-Id": self._resolve_user_id(user_id),
            "X-Citex-Scope-Id": self._resolve_scope_id(scope_id),
        }
        if include_api_key and self._api_key:
            headers["X-Citex-API-Key"] = self._api_key
        return headers

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
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response | None:
        """Execute an HTTP request with exponential-backoff retry.

        Returns the ``httpx.Response`` on success or ``None`` after
        all retries are exhausted.
        """
        last_exc: Exception | None = None
        attempts_made = 0

        for attempt in range(_MAX_RETRIES):
            attempts_made = attempt + 1
            try:
                response = await self._http.request(
                    method,
                    path,
                    json=json_body,
                    params=params,
                    data=data,
                    files=files,
                    headers=headers,
                )
                response.raise_for_status()
                return response

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                if isinstance(exc, httpx.HTTPStatusError):
                    status_code = exc.response.status_code
                    response_detail = ""
                    try:
                        payload = exc.response.json()
                        detail = payload.get("detail") if isinstance(payload, dict) else ""
                        response_detail = str(detail or "")
                    except Exception:
                        response_detail = ""
                    # Do not retry deterministic client errors.
                    if status_code in {400, 401, 403, 404, 409, 422}:
                        logger.warning(
                            "Citex request %s %s returned non-retriable status %d: %s",
                            method,
                            path,
                            status_code,
                            exc,
                        )
                        break
                    # Some Citex routes currently return 500 for deterministic validation errors.
                    if status_code == 500 and "Project not found" in response_detail:
                        logger.warning(
                            "Citex request %s %s returned deterministic 500 (%s); not retrying",
                            method,
                            path,
                            response_detail,
                        )
                        break
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "Citex request %s %s failed (attempt %d/%d): %s - retrying in %.1fs",
                    method,
                    path,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        logger.error(
            "Citex request %s %s failed after %d attempt(s): %s",
            method,
            path,
            attempts_made,
            last_exc,
        )
        return None

    async def _poll_job_status(
        self,
        *,
        job_id: str,
        user_id: str,
        scope_id: str,
        timeout_seconds: float = 8.0,
        interval_seconds: float = 1.0,
    ) -> dict[str, Any] | None:
        """Poll ingestion job status briefly and return the latest job payload."""
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        headers = self._build_headers(user_id=user_id, scope_id=scope_id)

        latest: dict[str, Any] | None = None
        while asyncio.get_running_loop().time() < deadline:
            response = await self._request_with_retry(
                "GET",
                f"/api/ingest/jobs/{job_id}",
                headers=headers,
            )
            if response is None:
                break

            payload = response.json()
            job = payload.get("job") if isinstance(payload, dict) else None
            if isinstance(job, dict):
                latest = job
                status = str(job.get("status", "")).lower()
                if status in {"completed", "failed", "cancelled"}:
                    return latest

            await asyncio.sleep(interval_seconds)

        return latest

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
        logger.warning("Citex ping failed - service may be unavailable")
        return False

    async def ingest_document(
        self,
        project_id: str,
        content: str,
        metadata: dict[str, Any],
        filename: str,
        *,
        file_bytes: bytes | None = None,
        content_type: str | None = None,
        user_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        """Ingest a document into Citex for semantic indexing.

        Args:
            project_id: Project scope for the document.
            content: Full text content to ingest.
            metadata: Arbitrary metadata dict (source, author, etc.).
            filename: Original filename.
            file_bytes: Optional raw file bytes to upload directly. When
                provided, ``content`` is ignored for upload payload.
            content_type: Optional MIME type for ``file_bytes`` uploads.
            user_id: Optional user context override.
            scope_id: Optional scope context override.

        Returns:
            The JSON response body from Citex on success, or an empty
            dict if the request failed.
        """
        resolved_user_id = self._resolve_user_id(user_id)
        resolved_scope_id = self._resolve_scope_id(scope_id)

        form_data = {
            "project_id": project_id,
            "user_id": resolved_user_id,
            "scope_id": resolved_scope_id,
        }
        if metadata:
            tags = [
                f"{k}:{v}"
                for k, v in metadata.items()
                if isinstance(v, str) and v
            ]
            if tags:
                form_data["tags"] = json.dumps(tags[:20])

        upload_bytes = file_bytes if file_bytes is not None else content.encode("utf-8")
        upload_content_type = content_type or (
            "application/octet-stream" if file_bytes is not None else "text/plain"
        )

        response = await self._request_with_retry(
            "POST",
            "/api/ingest",
            data=form_data,
            files={"file": (filename, upload_bytes, upload_content_type)},
            headers=self._build_headers(user_id=resolved_user_id, scope_id=resolved_scope_id),
        )
        if response is not None:
            body = response.json()
            job = body.get("job") if isinstance(body, dict) else None
            job_id = str(job.get("jobId", "")) if isinstance(job, dict) else ""
            if job_id:
                polled = await self._poll_job_status(
                    job_id=job_id,
                    user_id=resolved_user_id,
                    scope_id=resolved_scope_id,
                )
                if polled and str(polled.get("status", "")).lower() == "failed":
                    logger.error(
                        "Citex ingestion job failed: project=%s filename=%s job=%s",
                        project_id,
                        filename,
                        job_id,
                    )
                    return {}
                logger.info(
                    "Document queued in Citex ingest API: project=%s filename=%s jobId=%s",
                    project_id,
                    filename,
                    job_id,
                )
                return {
                    "job": polled or job,
                    "jobId": job_id,
                }

            logger.info(
                "Document queued in Citex ingest API: project=%s filename=%s",
                project_id,
                filename,
            )
            return body

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
        *,
        user_id: str | None = None,
        scope_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform a semantic search against Citex.

        Args:
            project_id: Project scope for the query.
            query_text: Natural-language query.
            filters: Optional metadata filters.
            top_k: Maximum number of result chunks.
            user_id: Optional user context override.
            scope_id: Optional scope context override.

        Returns:
            A list of chunk dicts on success, or an empty list if
            the request failed.
        """
        resolved_user_id = self._resolve_user_id(user_id)
        resolved_scope_id = self._resolve_scope_id(scope_id)
        query_payload: dict[str, Any] = {
            "project_id": project_id,
            "query": query_text,
            "top_k": top_k,
            "score_threshold": 0.0,
            "user_id": resolved_user_id,
            "scope_id": resolved_scope_id,
        }
        if filters:
            query_payload["filters"] = {
                **filters,
                "user_id": resolved_user_id,
                "scope_id": resolved_scope_id,
            }

        response = await self._request_with_retry(
            "POST",
            "/api/retrieval/query",
            json_body=query_payload,
            headers=self._build_headers(user_id=resolved_user_id, scope_id=resolved_scope_id),
        )
        if response is not None:
            normalized: list[dict[str, Any]] = []
            data = response.json()
            for item in data.get("results", []):
                if not isinstance(item, dict):
                    continue
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                content = (
                    item.get("content")
                    or item.get("text")
                    or item.get("chunk_text")
                    or item.get("snippet")
                    or ""
                )
                normalized.append(
                    {
                        "chunk_id": item.get("chunk_id")
                        or item.get("chunkId")
                        or item.get("id")
                        or item.get("doc_id")
                        or item.get("docId")
                        or "",
                        "content": str(content),
                        "score": float(item.get("score") or item.get("fused_score") or 0.0),
                        "metadata": metadata,
                        "source": (
                            item.get("source")
                            or item.get("file_name")
                            or item.get("fileName")
                            or metadata.get("source", "")
                        ),
                    }
                )

            logger.debug(
                "Citex query returned %d chunks for project=%s",
                len(normalized),
                project_id,
            )
            return normalized

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
            f"/api/projects/{project_id}",
            params={"confirmProjectId": project_id},
            headers=self._build_headers(),
        )
        if response is not None:
            logger.info("Deleted Citex project data for project=%s", project_id)
            return True

        logger.error("Failed to delete Citex documents for project=%s", project_id)
        return False
