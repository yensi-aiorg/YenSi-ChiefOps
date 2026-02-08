import { test, expect } from "@playwright/test";

const API_BASE = "**/api";

test.describe("Onboarding Wizard", () => {
  test.describe("First-run experience", () => {
    test("wizard appears when no data exists", async ({ page }) => {
      // Mock settings endpoint to indicate onboarding not completed
      await page.route(`${API_BASE}/v1/settings`, (route) => {
        if (route.request().method() === "GET") {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              has_completed_onboarding: false,
              theme: "light",
              default_project_id: null,
            }),
          });
        }
        return route.continue();
      });

      // Mock empty projects to simulate first-run state
      await page.route(`${API_BASE}/v1/projects`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ projects: [], total: 0 }),
        }),
      );

      await page.goto("/");

      // The onboarding wizard should be visible with the Welcome step
      await expect(
        page.getByRole("heading", { name: "Welcome to ChiefOps" }),
      ).toBeVisible();

      // The step indicator should show "Welcome" as active
      await expect(page.getByText("Welcome", { exact: true })).toBeVisible();

      // Feature cards should be displayed
      await expect(page.getByText("AI Insights")).toBeVisible();
      await expect(page.getByText("Smart Dashboards")).toBeVisible();
      await expect(page.getByText("Unified Data")).toBeVisible();

      // Get Started button should be present
      await expect(
        page.getByRole("button", { name: /Get Started/i }),
      ).toBeVisible();
    });

    test('"Try with Sample Data" button loads sample data', async ({
      page,
    }) => {
      // Mock settings for first-run state
      await page.route(`${API_BASE}/v1/settings`, (route) => {
        if (route.request().method() === "GET") {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              has_completed_onboarding: false,
              theme: "light",
              default_project_id: null,
            }),
          });
        }
        if (route.request().method() === "PATCH") {
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

      await page.goto("/");

      // Step 1: Click "Get Started" to proceed to data source step
      await page.getByRole("button", { name: /Get Started/i }).click();

      // Step 2: Should show the data source selection
      await expect(
        page.getByRole("heading", { name: /Choose Your Data Source/i }),
      ).toBeVisible();

      // The "Try with Sample Data" option should be visible
      const sampleDataButton = page.getByRole("button", {
        name: /Try with Sample Data/i,
      });
      await expect(sampleDataButton).toBeVisible();

      // Click "Try with Sample Data"
      await sampleDataButton.click();

      // Should advance to the confirmation step after loading
      await expect(
        page.getByRole("heading", { name: /You're All Set/i }),
      ).toBeVisible({ timeout: 10000 });

      // The confirmation message should explain data was loaded
      await expect(
        page.getByText(/Your data has been loaded successfully/i),
      ).toBeVisible();
    });

    test("redirect to main dashboard after onboarding", async ({ page }) => {
      // Mock settings for first-run state that transitions to completed
      let onboardingCompleted = false;

      await page.route(`${API_BASE}/v1/settings`, (route) => {
        if (route.request().method() === "GET") {
          return route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              has_completed_onboarding: onboardingCompleted,
              theme: "light",
              default_project_id: null,
            }),
          });
        }
        if (route.request().method() === "PATCH") {
          onboardingCompleted = true;
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

      await page.goto("/");

      // Complete the full onboarding flow
      await page.getByRole("button", { name: /Get Started/i }).click();

      // Click "Try with Sample Data"
      await page
        .getByRole("button", { name: /Try with Sample Data/i })
        .click();

      // Wait for confirmation step
      await expect(
        page.getByRole("heading", { name: /You're All Set/i }),
      ).toBeVisible({ timeout: 10000 });

      // Click "Go to Dashboard"
      await page.getByRole("button", { name: /Go to Dashboard/i }).click();

      // The main dashboard heading should be visible, confirming redirect
      await expect(
        page.getByRole("heading", { name: "Dashboard", level: 1 }),
      ).toBeVisible({ timeout: 10000 });
    });

    test("onboarding does not appear on subsequent visits", async ({
      page,
    }) => {
      // Mock settings to indicate onboarding was already completed
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
          body: JSON.stringify({
            projects: [
              {
                project_id: "proj-1",
                name: "Alpha Project",
                description: "Test project",
                status: "on_track",
                health_score: 85,
                completion_percentage: 60,
                deadline: "2026-06-01",
                people_involved: [],
                task_summary: {
                  total: 10,
                  completed: 6,
                  in_progress: 2,
                  blocked: 0,
                  to_do: 2,
                },
                key_risks: [],
                last_analyzed_at: new Date().toISOString(),
                sprint_health: null,
                gap_analysis: null,
                technical_feasibility: null,
              },
            ],
            total: 1,
          }),
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

      await page.goto("/");

      // The onboarding wizard should NOT be visible
      await expect(
        page.getByRole("heading", { name: "Welcome to ChiefOps" }),
      ).not.toBeVisible({ timeout: 5000 });

      // The main dashboard should be shown instead
      await expect(
        page.getByRole("heading", { name: "Dashboard", level: 1 }),
      ).toBeVisible({ timeout: 10000 });
    });
  });
});
