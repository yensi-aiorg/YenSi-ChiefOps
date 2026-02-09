from __future__ import annotations

from httpx import AsyncClient


class TestProjectSemanticApi:
    async def test_submit_note_then_get_snapshot_and_insights(self, async_client: AsyncClient):
        create_resp = await async_client.post(
            "/api/v1/projects",
            json={"name": "Semantic Project", "description": "semantic test project"},
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["project_id"]

        note_resp = await async_client.post(
            f"/api/v1/projects/{project_id}/files/notes",
            json={
                "title": "Weekly COO Note",
                "content": (
                    "Decision: shift launch by two weeks. "
                    "The project is not going well and this is a major red flag."
                ),
            },
        )
        assert note_resp.status_code == 200
        note_data = note_resp.json()
        assert note_data["status"] == "completed"
        assert note_data["insights_created"] >= 1

        snapshot_resp = await async_client.get(f"/api/v1/projects/{project_id}/snapshot")
        assert snapshot_resp.status_code == 200
        snapshot = snapshot_resp.json()
        assert snapshot["project_id"] == project_id
        assert snapshot["executive_summary"]
        assert snapshot["summary"]
        assert snapshot["detailed_understanding"]

        insights_resp = await async_client.get(f"/api/v1/projects/{project_id}/insights")
        assert insights_resp.status_code == 200
        insights_data = insights_resp.json()
        assert insights_data["project_id"] == project_id
        assert insights_data["total"] >= 1
