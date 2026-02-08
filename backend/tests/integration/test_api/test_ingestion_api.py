"""
Integration tests for the ingestion API endpoints.

Tests file upload, job listing, and job detail retrieval
using the test FastAPI application with a test MongoDB instance.
"""

from __future__ import annotations

import io
import json

import pytest
from httpx import AsyncClient

from app.models.base import generate_uuid, utc_now


class TestUploadFile:
    """Test the file upload endpoint."""

    async def test_upload_file(self, async_client: AsyncClient, test_db):
        """POST /api/v1/ingest/upload should accept valid files and create a job."""
        # Create a mock CSV file with Jira-like content
        csv_content = (
            "Issue Key,Summary,Status,Priority,Assignee\n"
            "PROJ-1,Fix login bug,In Progress,High,Alice\n"
            "PROJ-2,Add search,To Do,Medium,Bob\n"
        )

        response = await async_client.post(
            "/api/v1/ingest/upload",
            files=[
                ("files", ("jira_export.csv", io.BytesIO(csv_content.encode()), "text/csv")),
            ],
        )

        assert response.status_code == 201
        data = response.json()
        assert "ingestion_job_id" in data
        assert data["files_accepted"] == 1
        assert data["total_size_bytes"] > 0
        assert "message" in data

    async def test_upload_empty_file_rejected(self, async_client: AsyncClient):
        """Uploading an empty file should return 422."""
        response = await async_client.post(
            "/api/v1/ingest/upload",
            files=[
                ("files", ("empty.csv", io.BytesIO(b""), "text/csv")),
            ],
        )

        assert response.status_code == 422

    async def test_upload_disallowed_extension(self, async_client: AsyncClient):
        """Uploading a file with a disallowed extension should return 422."""
        response = await async_client.post(
            "/api/v1/ingest/upload",
            files=[
                ("files", ("malware.exe", io.BytesIO(b"bad content"), "application/octet-stream")),
            ],
        )

        assert response.status_code == 422

    async def test_upload_multiple_files(self, async_client: AsyncClient):
        """Uploading multiple valid files should succeed."""
        csv1 = b"Issue Key,Summary,Status\nPROJ-1,Task A,Done\n"
        csv2 = b"name,value\nalpha,100\n"

        response = await async_client.post(
            "/api/v1/ingest/upload",
            files=[
                ("files", ("export1.csv", io.BytesIO(csv1), "text/csv")),
                ("files", ("data.csv", io.BytesIO(csv2), "text/csv")),
            ],
        )

        assert response.status_code == 201
        data = response.json()
        assert data["files_accepted"] == 2


class TestListJobs:
    """Test the ingestion jobs listing endpoint."""

    async def test_list_jobs(self, async_client: AsyncClient, test_db):
        """GET /api/v1/ingest/jobs should return a paginated list of jobs."""
        # First, create a job by uploading a file
        csv_content = b"Issue Key,Summary,Status\nPROJ-1,Task,Done\n"
        await async_client.post(
            "/api/v1/ingest/upload",
            files=[("files", ("test.csv", io.BytesIO(csv_content), "text/csv"))],
        )

        # List jobs
        response = await async_client.get("/api/v1/ingest/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert isinstance(data["jobs"], list)
        assert data["total"] >= 1

    async def test_list_jobs_pagination(self, async_client: AsyncClient, test_db):
        """Job listing should support skip and limit parameters."""
        response = await async_client.get(
            "/api/v1/ingest/jobs",
            params={"skip": 0, "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["skip"] == 0

    async def test_list_jobs_empty(self, async_client: AsyncClient):
        """Job listing with no jobs should return an empty list."""
        response = await async_client.get("/api/v1/ingest/jobs")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["jobs"], list)


class TestGetJobDetail:
    """Test retrieving a single ingestion job by ID."""

    async def test_get_job_detail(self, async_client: AsyncClient, test_db):
        """GET /api/v1/ingest/jobs/{job_id} should return the full job detail."""
        # Create a job
        csv_content = b"Issue Key,Summary,Status\nPROJ-1,Task,Done\n"
        upload_response = await async_client.post(
            "/api/v1/ingest/upload",
            files=[("files", ("detail_test.csv", io.BytesIO(csv_content), "text/csv"))],
        )
        job_id = upload_response.json()["ingestion_job_id"]

        # Retrieve the job detail
        response = await async_client.get(f"/api/v1/ingest/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "files" in data
        assert "created_at" in data

    async def test_get_job_detail_not_found(self, async_client: AsyncClient):
        """Requesting a non-existent job should return 404."""
        response = await async_client.get(
            f"/api/v1/ingest/jobs/{generate_uuid()}"
        )

        assert response.status_code == 404
