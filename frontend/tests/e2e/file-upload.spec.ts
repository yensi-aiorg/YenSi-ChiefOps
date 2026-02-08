import { test, expect } from "@playwright/test";
import path from "path";

const API_BASE = "**/api";

/**
 * Helper to set up common route mocks so the app reaches the Upload Data page
 * without triggering the onboarding wizard.
 */
async function setupAppRoutes(page: import("@playwright/test").Page) {
  await page.route(`${API_BASE}/v1/settings`, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          has_completed_onboarding: true,
          theme: "light",
          default_project_id: null,
        }),
      });
    }
    return route.continue();
  });

  await page.route(`${API_BASE}/v1/projects`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ projects: [], total: 0 }),
    }),
  );

  await page.route(`${API_BASE}/v1/alerts/triggered`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ alerts: [], total: 0 }),
    }),
  );

  await page.route(`${API_BASE}/v1/dashboards`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ dashboards: [], total: 0 }),
    }),
  );
}

test.describe("File Upload", () => {
  test.describe("Drop zone and file selection", () => {
    test("drag-and-drop zone is visible on the upload page", async ({
      page,
    }) => {
      await setupAppRoutes(page);

      // Mock empty ingestion history
      await page.route(`${API_BASE}/v1/ingestion/jobs`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ jobs: [], total: 0 }),
        }),
      );

      await page.goto("/upload");

      // Page header
      await expect(
        page.getByRole("heading", { name: "Upload Data", level: 1 }),
      ).toBeVisible();

      // The drop zone prompt text should be visible
      await expect(
        page.getByText("Drag & drop files to upload"),
      ).toBeVisible();

      // Supported formats hint
      await expect(
        page.getByText(/or click to browse/i),
      ).toBeVisible();

      // File type badges
      await expect(page.getByText("Slack Export (.zip/.json)")).toBeVisible();
      await expect(page.getByText("Jira CSV (.csv)")).toBeVisible();
      await expect(page.getByText("Drive Docs (.txt/.json)")).toBeVisible();
    });

    test("file selection via file picker triggers upload", async ({
      page,
    }) => {
      await setupAppRoutes(page);

      const jobId = "job-upload-test-001";

      // Mock empty ingestion history initially
      await page.route(`${API_BASE}/v1/ingestion/jobs`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ jobs: [], total: 0 }),
        }),
      );

      // Mock the upload endpoint
      await page.route(`${API_BASE}/v1/ingestion/upload`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: jobId,
            status: "processing",
            created_at: new Date().toISOString(),
            started_at: new Date().toISOString(),
            completed_at: null,
            total_records: 0,
            error_count: 0,
            files: [
              {
                filename: "test-data.csv",
                file_type: "jira_csv",
                status: "processing",
                records_processed: 0,
                records_skipped: 0,
                error_message: null,
              },
            ],
          }),
        }),
      );

      await page.goto("/upload");

      // Wait for drop zone to appear
      await expect(
        page.getByText("Drag & drop files to upload"),
      ).toBeVisible();

      // Locate the hidden file input inside the drop zone
      const fileInput = page.locator('input[type="file"]');

      // Set a file via the file chooser (simulates file picker selection)
      await fileInput.setInputFiles({
        name: "test-data.csv",
        mimeType: "text/csv",
        buffer: Buffer.from("issue_key,summary,status\nTEST-1,Fix bug,Done"),
      });

      // The uploading state should be triggered -- verify the drop zone changes
      // to indicate upload activity or the upload endpoint was called
      await expect(
        page.getByText(/Uploading files|processing|complete/i).first(),
      ).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Upload progress and completion", () => {
    test("upload progress is displayed during processing", async ({
      page,
    }) => {
      await setupAppRoutes(page);

      const jobId = "job-progress-001";

      // Mock ingestion jobs to return a processing job
      await page.route(`${API_BASE}/v1/ingestion/jobs`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            jobs: [
              {
                job_id: jobId,
                status: "processing",
                created_at: new Date().toISOString(),
                started_at: new Date().toISOString(),
                completed_at: null,
                total_records: 150,
                error_count: 0,
                files: [
                  {
                    filename: "slack-export.json",
                    file_type: "slack_export",
                    status: "completed",
                    records_processed: 100,
                    records_skipped: 5,
                    error_message: null,
                  },
                  {
                    filename: "jira-tasks.csv",
                    file_type: "jira_csv",
                    status: "processing",
                    records_processed: 50,
                    records_skipped: 0,
                    error_message: null,
                  },
                ],
              },
            ],
            total: 1,
          }),
        }),
      );

      // Mock upload to set the active job
      await page.route(`${API_BASE}/v1/ingestion/upload`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            job_id: jobId,
            status: "processing",
            created_at: new Date().toISOString(),
            started_at: new Date().toISOString(),
            completed_at: null,
            total_records: 150,
            error_count: 0,
            files: [
              {
                filename: "slack-export.json",
                file_type: "slack_export",
                status: "completed",
                records_processed: 100,
                records_skipped: 5,
                error_message: null,
              },
              {
                filename: "jira-tasks.csv",
                file_type: "jira_csv",
                status: "processing",
                records_processed: 50,
                records_skipped: 0,
                error_message: null,
              },
            ],
          }),
        }),
      );

      await page.goto("/upload");

      // Trigger upload to create active job context
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: "slack-export.json",
        mimeType: "application/json",
        buffer: Buffer.from('{"messages": []}'),
      });

      // Progress should be visible -- the Active Ingestion Job card
      await expect(
        page.getByText(/Active Ingestion Job|Uploading files|processing/i).first(),
      ).toBeVisible({ timeout: 10000 });

      // File names should appear in progress detail
      await expect(page.getByText("slack-export.json")).toBeVisible({
        timeout: 5000,
      });
    });

    test("ingestion summary appears after completion", async ({ page }) => {
      await setupAppRoutes(page);

      const jobId = "job-complete-001";
      const completedJob = {
        job_id: jobId,
        status: "completed",
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        total_records: 250,
        error_count: 2,
        files: [
          {
            filename: "slack-export.json",
            file_type: "slack_export",
            status: "completed",
            records_processed: 150,
            records_skipped: 1,
            error_message: null,
          },
          {
            filename: "jira-tasks.csv",
            file_type: "jira_csv",
            status: "completed",
            records_processed: 100,
            records_skipped: 1,
            error_message: null,
          },
        ],
      };

      await page.route(`${API_BASE}/v1/ingestion/jobs`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ jobs: [completedJob], total: 1 }),
        }),
      );

      // Mock upload to immediately return a completed job
      await page.route(`${API_BASE}/v1/ingestion/upload`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(completedJob),
        }),
      );

      await page.goto("/upload");

      // Trigger upload
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: "slack-export.json",
        mimeType: "application/json",
        buffer: Buffer.from('{"messages": []}'),
      });

      // Ingestion Complete summary card should appear
      await expect(page.getByText("Ingestion Complete")).toBeVisible({
        timeout: 10000,
      });

      // Summary statistics should be displayed
      await expect(
        page.getByRole("paragraph").filter({ hasText: /^Files$/ }),
      ).toBeVisible();
      await expect(page.getByText("Records").first()).toBeVisible();
      await expect(page.getByText("Errors").first()).toBeVisible();
      await expect(page.getByText("Duration").first()).toBeVisible();
    });
  });

  test.describe("Upload history", () => {
    test("upload history table shows past jobs", async ({ page }) => {
      await setupAppRoutes(page);

      const pastJobs = [
        {
          job_id: "job-hist-001",
          status: "completed",
          created_at: "2026-01-15T10:30:00Z",
          started_at: "2026-01-15T10:30:01Z",
          completed_at: "2026-01-15T10:30:45Z",
          total_records: 500,
          error_count: 0,
          files: [
            {
              filename: "slack-jan.json",
              file_type: "slack_export",
              status: "completed",
              records_processed: 500,
              records_skipped: 0,
              error_message: null,
            },
          ],
        },
        {
          job_id: "job-hist-002",
          status: "failed",
          created_at: "2026-01-20T14:00:00Z",
          started_at: "2026-01-20T14:00:01Z",
          completed_at: "2026-01-20T14:00:10Z",
          total_records: 0,
          error_count: 1,
          files: [
            {
              filename: "bad-file.csv",
              file_type: "jira_csv",
              status: "failed",
              records_processed: 0,
              records_skipped: 0,
              error_message: "Invalid CSV format",
            },
          ],
        },
      ];

      await page.route(`${API_BASE}/v1/ingestion/jobs`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ jobs: pastJobs, total: 2 }),
        }),
      );

      await page.goto("/upload");

      // The Ingestion History section header should be visible
      await expect(page.getByText("Ingestion History")).toBeVisible();

      // The job count should be shown
      await expect(page.getByText("2 jobs")).toBeVisible();

      // Table headers
      await expect(page.getByText("Job ID")).toBeVisible();
      await expect(page.getByText("Date")).toBeVisible();
      await expect(
        page.getByRole("columnheader", { name: "Files" }),
      ).toBeVisible();
      await expect(
        page.getByRole("columnheader", { name: "Records" }),
      ).toBeVisible();
      await expect(
        page.getByRole("columnheader", { name: "Status" }),
      ).toBeVisible();

      // Job ID fragments should be visible (truncated)
      await expect(page.getByText("job-hist-001")).toBeVisible();
      await expect(page.getByText("job-hist-002")).toBeVisible();

      // Status badges
      await expect(page.getByText("Completed")).toBeVisible();
      await expect(page.getByText("Failed")).toBeVisible();
    });
  });
});
