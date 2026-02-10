from __future__ import annotations


def derive_citex_project_id(*, configured_project_id: str, api_key: str, fallback_project_id: str) -> str:
    """
    Resolve the Citex project_id used for API-key-scoped requests.

    Priority:
    1. Explicit configuration (CITEX_PROJECT_ID)
    2. API key prefix convention: ctx_<project_id>_<secret>
    3. Fallback to caller-provided project id
    """
    explicit = (configured_project_id or "").strip()
    if explicit:
        return explicit

    key = (api_key or "").strip()
    if key.startswith("ctx_"):
        parts = key.split("_", 2)
        if len(parts) >= 3 and parts[1].strip():
            return parts[1].strip()

    return (fallback_project_id or "").strip()
