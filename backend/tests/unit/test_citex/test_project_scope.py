from __future__ import annotations

from app.citex.project_scope import derive_citex_project_id


def test_derive_uses_explicit_config_first() -> None:
    resolved = derive_citex_project_id(
        configured_project_id="chiefops1",
        api_key="ctx_other_abc",
        fallback_project_id="proj-123",
    )
    assert resolved == "chiefops1"


def test_derive_from_ctx_key_prefix() -> None:
    resolved = derive_citex_project_id(
        configured_project_id="",
        api_key="ctx_chiefops1_zLgMmBPybGndFtNcMpPbPaNOyCmIvB4E",
        fallback_project_id="proj-123",
    )
    assert resolved == "chiefops1"


def test_derive_falls_back_to_project_id() -> None:
    resolved = derive_citex_project_id(
        configured_project_id="",
        api_key="invalid-key-format",
        fallback_project_id="proj-123",
    )
    assert resolved == "proj-123"
