from __future__ import annotations

import pytest

from app.citex.client import CitexClient


class _DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.status_code = 200

    def json(self) -> dict:
        return self._payload


@pytest.mark.asyncio
async def test_query_new_api_sends_required_context(monkeypatch: pytest.MonkeyPatch) -> None:
    client = CitexClient(
        "http://citex.local",
        api_key="test-key",
        user_id="chiefops-user",
        scope_id="project:alpha",
    )

    calls: list[tuple[str, str, dict]] = []

    async def _fake_request(method: str, path: str, **kwargs):
        calls.append((method, path, kwargs))
        return _DummyResponse(
            {
                "query": "status",
                "results": [
                    {
                        "chunkId": "c1",
                        "text": "Project status is on track",
                        "score": 0.91,
                        "metadata": {"source": "jira", "source_ref": "ALPHA"},
                    }
                ],
            }
        )

    async def _fake_variant() -> str:
        return "new"

    monkeypatch.setattr(client, "_request_with_retry", _fake_request)
    monkeypatch.setattr(client, "_get_api_variant", _fake_variant)

    chunks = await client.query(project_id="alpha", query_text="status", top_k=3)

    assert chunks
    assert len(calls) == 1
    method, path, kwargs = calls[0]
    assert method == "POST"
    assert path == "/api/retrieval/query"

    headers = kwargs["headers"]
    assert headers["X-Citex-API-Key"] == "test-key"
    assert headers["X-Citex-User-Id"] == "chiefops-user"
    assert headers["X-Citex-Scope-Id"] == "project:alpha"

    payload = kwargs["json_body"]
    assert payload["project_id"] == "alpha"
    assert payload["user_id"] == "chiefops-user"
    assert payload["scope_id"] == "project:alpha"


@pytest.mark.asyncio
async def test_ingest_new_api_posts_ingest_with_context(monkeypatch: pytest.MonkeyPatch) -> None:
    client = CitexClient(
        "http://citex.local",
        api_key="test-key",
        user_id="chiefops-user",
        scope_id="project:alpha",
    )

    calls: list[tuple[str, str, dict]] = []

    async def _fake_request(method: str, path: str, **kwargs):
        calls.append((method, path, kwargs))
        return _DummyResponse({"job": {"jobId": "job-123", "status": "queued"}})

    async def _fake_variant() -> str:
        return "new"

    async def _fake_poll(**kwargs):
        return {"jobId": kwargs["job_id"], "status": "completed"}

    monkeypatch.setattr(client, "_request_with_retry", _fake_request)
    monkeypatch.setattr(client, "_get_api_variant", _fake_variant)
    monkeypatch.setattr(client, "_poll_job_status", _fake_poll)

    result = await client.ingest_document(
        project_id="alpha",
        content="hello world",
        metadata={"source": "slack", "source_ref": "#alpha"},
        filename="alpha.txt",
    )

    assert result["jobId"] == "job-123"
    assert len(calls) == 1

    method, path, kwargs = calls[0]
    assert method == "POST"
    assert path == "/api/ingest"

    headers = kwargs["headers"]
    assert headers["X-Citex-API-Key"] == "test-key"
    assert headers["X-Citex-User-Id"] == "chiefops-user"
    assert headers["X-Citex-Scope-Id"] == "project:alpha"

    data = kwargs["data"]
    assert data["project_id"] == "alpha"
    assert data["user_id"] == "chiefops-user"
    assert data["scope_id"] == "project:alpha"


@pytest.mark.asyncio
async def test_delete_prefers_project_delete_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    client = CitexClient(
        "http://citex.local",
        api_key="test-key",
        user_id="chiefops-user",
        scope_id="project:alpha",
    )

    calls: list[tuple[str, str, dict]] = []

    async def _fake_request(method: str, path: str, **kwargs):
        calls.append((method, path, kwargs))
        return _DummyResponse({"status": "deleted"})

    monkeypatch.setattr(client, "_request_with_retry", _fake_request)

    ok = await client.delete_project_documents("alpha")

    assert ok is True
    assert len(calls) == 1
    method, path, kwargs = calls[0]
    assert method == "DELETE"
    assert path == "/api/projects/alpha"
    assert kwargs["params"]["confirmProjectId"] == "alpha"
    assert kwargs["headers"]["X-Citex-API-Key"] == "test-key"
