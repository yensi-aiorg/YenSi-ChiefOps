from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.memory import manager


@pytest.mark.asyncio
async def test_retrieve_rag_chunks_skips_when_project_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        CITEX_API_URL="http://citex.local",
        CITEX_API_KEY="test-key",
        CITEX_USER_ID="user1",
    )
    monkeypatch.setattr(manager, "get_settings", lambda: settings)

    class _FailIfConstructed:
        def __init__(self, *args, **kwargs):
            raise AssertionError("CitexClient should not be constructed when project_id is missing")

    monkeypatch.setattr(manager, "CitexClient", _FailIfConstructed)

    chunks = await manager._retrieve_rag_chunks("status update", project_id="")
    assert chunks == []


@pytest.mark.asyncio
async def test_retrieve_rag_chunks_uses_project_scoped_context(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        CITEX_API_URL="http://citex.local",
        CITEX_API_KEY="test-key",
        CITEX_PROJECT_ID="",
        CITEX_USER_ID="user1",
    )
    monkeypatch.setattr(manager, "get_settings", lambda: settings)

    captured: dict = {}

    class _FakeCitexClient:
        def __init__(self, base_url: str, *, api_key: str | None = None, user_id: str = "", scope_id: str = ""):
            captured["init"] = {
                "base_url": base_url,
                "api_key": api_key,
                "user_id": user_id,
                "scope_id": scope_id,
            }

        async def query(self, *, project_id: str, query_text: str, top_k: int):
            captured["query"] = {
                "project_id": project_id,
                "query_text": query_text,
                "top_k": top_k,
            }
            return [
                {
                    "content": "Sprint is on track",
                    "source": "jira",
                    "metadata": {"source_ref": "ALPHA"},
                }
            ]

        async def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(manager, "CitexClient", _FakeCitexClient)

    chunks = await manager._retrieve_rag_chunks("status update", project_id="proj-123")

    assert chunks
    assert captured["init"]["scope_id"] == "project:proj-123"
    assert captured["query"]["project_id"] == "proj-123"
    assert captured.get("closed") is True
