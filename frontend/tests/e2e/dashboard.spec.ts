import { test, expect } from "@playwright/test";

const API_BASE = "**/api";

/** Sample projects for dashboard tests. */
const SAMPLE_PROJECTS = [
  {
    project_id: "proj-alpha",
    name: "Alpha Platform",
    description: "Core platform rebuild with microservices architecture",
    status: "on_track",
    health_score: 82,
    completion_percentage: 65,
    deadline: "2026-06-15",
    people_involved: [
      {
        person_id: "p-1",
        name: "Alice Chen",
        role: "Tech Lead",
        activity_level: "very_active",
      },
      {
        person_id: "p-2",
        name: "Bob Martinez",
        role: "Backend Engineer",
        activity_level: "active",
      },
    ],
    task_summary: {
      total: 40,
      completed: 26,
      in_progress: 8,
      blocked: 1,
      to_do: 5,
    },
    key_risks: ["API migration timeline tight"],
    last_analyzed_at: new Date().toISOString(),
    sprint_health: {
      completion_rate: 0.75,
      velocity_trend: "stable",
      blocker_count: 1,
      score: 78,
    },
    gap_analysis: null,
    technical_feasibility: null,
  },
  {
    project_id: "proj-beta",
    name: "Beta Mobile App",
    description: "Cross-platform mobile app for customer engagement",
    status: "at_risk",
    health_score: 54,
    completion_percentage: 35,
    deadline: "2026-04-30",
    people_involved: [
      {
        person_id: "p-3",
        name: "Carol Kim",
        role: "Product Manager",
        activity_level: "active",
      },
    ],
    task_summary: {
      total: 25,
      completed: 8,
      in_progress: 5,
      blocked: 3,
      to_do: 9,
    },
    key_risks: ["Design resources unavailable", "Third-party SDK unstable"],
    last_analyzed_at: new Date().toISOString(),
    sprint_health: {
      completion_rate: 0.45,
      velocity_trend: "declining",
      blocker_count: 3,
      score: 48,
    },
    gap_analysis: null,
    technical_feasibility: null,
  },
  {
    project_id: "proj-gamma",
    name: "Gamma Data Pipeline",
    description: "Real-time data ingestion and analytics pipeline",
    status: "completed",
    health_score: 95,
    completion_percentage: 100,
    deadline: "2026-01-31",
    people_involved: [
      {
        person_id: "p-4",
        name: "David Lee",
        role: "Data Engineer",
        activity_level: "moderate",
      },
    ],
    task_summary: {
      total: 20,
      completed: 20,
      in_progress: 0,
      blocked: 0,
      to_do: 0,
    },
    key_risks: [],
    last_analyzed_at: new Date().toISOString(),
    sprint_health: null,
    gap_analysis: null,
    technical_feasibility: null,
  },
];

/**
 * Set up standard route mocks for the app with pre-populated data
 * so the dashboard renders fully.
 */
async function setupDashboardRoutes(page: import("@playwright/test").Page) {
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
        projects: SAMPLE_PROJECTS,
        total: SAMPLE_PROJECTS.length,
      }),
    }),
  );

  await page.route(`${API_BASE}/v1/projects/proj-alpha`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SAMPLE_PROJECTS[0]),
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

  await page.route(`${API_BASE}/v1/dashboards?project_id=*`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ dashboards: [], total: 0 }),
    }),
  );
}

test.describe("Dashboard", () => {
  test.describe("Main dashboard", () => {
    test("main dashboard loads with correct heading", async ({ page }) => {
      await setupDashboardRoutes(page);
      await page.goto("/");

      // Page heading
      await expect(
        page.getByRole("heading", { name: "Dashboard", level: 1 }),
      ).toBeVisible();

      // Sidebar should be present with navigation
      await expect(page.getByText("ChiefOps")).toBeVisible();
      await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
      await expect(
        page.getByRole("link", { name: "Upload Data" }),
      ).toBeVisible();
    });

    test("health score ring is visible with computed value", async ({
      page,
    }) => {
      await setupDashboardRoutes(page);
      await page.goto("/");

      // Organization Health label should be visible
      await expect(page.getByText("Organization Health")).toBeVisible();

      // The score "/ 100" indicator should be present
      await expect(page.getByText("/ 100")).toBeVisible();

      // AI Briefing section should be rendered
      await expect(page.getByText("AI Briefing")).toBeVisible();
    });

    test("project cards are displayed for all projects", async ({ page }) => {
      await setupDashboardRoutes(page);
      await page.goto("/");

      // Project Overview section
      await expect(page.getByText("Project Overview")).toBeVisible();

      // Each project name should appear as a card
      await expect(page.getByText("Alpha Platform")).toBeVisible();
      await expect(page.getByText("Beta Mobile App")).toBeVisible();
      await expect(page.getByText("Gamma Data Pipeline")).toBeVisible();

      // Status badges
      await expect(page.getByText("On Track")).toBeVisible();
      await expect(page.getByText("At Risk")).toBeVisible();
      // "Completed" should appear for the gamma project
      await expect(page.getByText("Completed").first()).toBeVisible();

      // KPI cards
      await expect(page.getByText("Total Projects")).toBeVisible();
      await expect(page.getByText("Team Members").first()).toBeVisible();
      await expect(page.getByText("Open Tasks")).toBeVisible();
    });

    test("navigation to project dashboard works via card click", async ({
      page,
    }) => {
      await setupDashboardRoutes(page);
      await page.goto("/");

      // Click on a project card
      await page.getByText("Alpha Platform").click();

      // Should navigate to project detail page
      await expect(page).toHaveURL(/\/projects\/proj-alpha/);

      // The project detail page should show the project name
      await expect(
        page.getByRole("heading", { name: "Alpha Platform" }),
      ).toBeVisible({ timeout: 10000 });

      // Status badge should be visible
      await expect(page.getByText("On Track")).toBeVisible();

      // Back to Dashboard link should be present
      await expect(page.getByText("Back to Dashboard")).toBeVisible();
    });
  });

  test.describe("Project dashboard", () => {
    test("widget sections render on project dashboard overview tab", async ({
      page,
    }) => {
      await setupDashboardRoutes(page);
      await page.goto("/projects/proj-alpha");

      // Project heading
      await expect(
        page.getByRole("heading", { name: "Alpha Platform" }),
      ).toBeVisible({ timeout: 10000 });

      // Tab buttons should be visible
      await expect(
        page.getByRole("button", { name: "Overview" }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Custom Dashboard" }),
      ).toBeVisible();

      // Sprint Health section
      await expect(page.getByText("Sprint Health")).toBeVisible();
      await expect(page.getByText("Sprint Completion")).toBeVisible();
      await expect(page.getByText("Velocity")).toBeVisible();
      await expect(page.getByText("Blockers")).toBeVisible();

      // Team Members section
      await expect(page.getByText("Team Members").first()).toBeVisible();
      await expect(page.getByText("Alice Chen")).toBeVisible();
      await expect(page.getByText("Bob Martinez")).toBeVisible();

      // Overall Completion bar
      await expect(page.getByText("Overall Completion")).toBeVisible();

      // Analyze button
      await expect(
        page.getByRole("button", { name: /Analyze/i }),
      ).toBeVisible();
    });
  });

  test.describe("Responsive layout", () => {
    test("layout adapts to mobile viewport", async ({ page }) => {
      await setupDashboardRoutes(page);

      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto("/");

      // Dashboard heading should still be visible
      await expect(
        page.getByRole("heading", { name: "Dashboard", level: 1 }),
      ).toBeVisible();

      // Project cards should still be present
      await expect(page.getByText("Alpha Platform")).toBeVisible();

      // The mobile menu toggle button should be present
      await expect(
        page.getByRole("button", { name: /Toggle mobile menu/i }),
      ).toBeVisible();
    });

    test("layout adapts to tablet viewport", async ({ page }) => {
      await setupDashboardRoutes(page);

      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto("/");

      // Dashboard should load correctly
      await expect(
        page.getByRole("heading", { name: "Dashboard", level: 1 }),
      ).toBeVisible();

      // Project overview should be visible
      await expect(page.getByText("Project Overview")).toBeVisible();
      await expect(page.getByText("Alpha Platform")).toBeVisible();
    });

    test("layout adapts to desktop viewport", async ({ page }) => {
      await setupDashboardRoutes(page);

      // Set desktop viewport
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("/");

      // Dashboard should fully load
      await expect(
        page.getByRole("heading", { name: "Dashboard", level: 1 }),
      ).toBeVisible();

      // Sidebar labels should be visible on wide screens
      await expect(page.getByText("ChiefOps")).toBeVisible();
      await expect(
        page.getByText("AI Chief of Staff"),
      ).toBeVisible();

      // Search bar should be visible on desktop
      await expect(
        page.getByPlaceholder("Search people, projects, reports..."),
      ).toBeVisible();
    });
  });
});
