import { test, expect } from "@playwright/test";

const API_BASE = "**/api";

/** Reusable project data for widget tests. */
const PROJECT = {
  project_id: "proj-widget",
  name: "Widget Test Project",
  description: "Project for testing custom dashboard widgets",
  status: "on_track",
  health_score: 75,
  completion_percentage: 50,
  deadline: "2026-08-01",
  people_involved: [
    {
      person_id: "p-1",
      name: "Alice Chen",
      role: "Tech Lead",
      activity_level: "active",
    },
  ],
  task_summary: {
    total: 30,
    completed: 15,
    in_progress: 10,
    blocked: 2,
    to_do: 3,
  },
  key_risks: [],
  last_analyzed_at: new Date().toISOString(),
  sprint_health: {
    completion_rate: 0.65,
    velocity_trend: "stable",
    blocker_count: 2,
    score: 70,
  },
  gap_analysis: null,
  technical_feasibility: null,
};

/** Widget specs for testing. */
const SAMPLE_WIDGET_BAR = {
  widget_id: "w-bar-001",
  title: "Tasks by Status",
  widget_type: "bar_chart",
  data_query: {
    query_type: "aggregate",
    source: "tasks",
    filters: {},
    group_by: "status",
  },
  position: { row: 1, col: 1, width: 6, height: 1 },
  created_by: "ai",
};

const SAMPLE_WIDGET_KPI = {
  widget_id: "w-kpi-001",
  title: "Blocker Count",
  widget_type: "kpi_card",
  data_query: {
    query_type: "scalar",
    source: "tasks",
    filters: { status: "blocked" },
    group_by: null,
  },
  position: { row: 1, col: 7, width: 3, height: 1 },
  created_by: "ai",
};

const SAMPLE_DASHBOARD_EMPTY = {
  dashboard_id: "dash-001",
  project_id: "proj-widget",
  dashboard_type: "custom",
  title: "Custom Dashboard",
  widget_ids: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const SAMPLE_DASHBOARD_WITH_WIDGETS = {
  dashboard_id: "dash-001",
  project_id: "proj-widget",
  dashboard_type: "custom",
  title: "Custom Dashboard",
  widget_ids: ["w-bar-001", "w-kpi-001"],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

/**
 * Set up all required route mocks for widget management tests.
 */
async function setupWidgetRoutes(
  page: import("@playwright/test").Page,
  options: {
    dashboardHasWidgets?: boolean;
  } = {},
) {
  const { dashboardHasWidgets = false } = options;

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
      body: JSON.stringify({ projects: [PROJECT], total: 1 }),
    }),
  );

  await page.route(`${API_BASE}/v1/projects/proj-widget`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(PROJECT),
    }),
  );

  await page.route(`${API_BASE}/v1/alerts/triggered`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ alerts: [], total: 0 }),
    }),
  );

  // Dashboards endpoint -- serves the appropriate mock based on options
  await page.route(`${API_BASE}/v1/dashboards**`, (route) => {
    const dashboard = dashboardHasWidgets
      ? SAMPLE_DASHBOARD_WITH_WIDGETS
      : SAMPLE_DASHBOARD_EMPTY;

    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        dashboards: [dashboard],
        total: 1,
        widgets: dashboardHasWidgets
          ? [SAMPLE_WIDGET_BAR, SAMPLE_WIDGET_KPI]
          : [],
      }),
    });
  });

  // Individual widget data endpoints
  await page.route(`${API_BASE}/v1/widgets/w-bar-001/data`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        series: [
          {
            type: "bar",
            data: [15, 10, 2, 3],
          },
        ],
        xAxis: {
          type: "category",
          data: ["Completed", "In Progress", "Blocked", "To Do"],
        },
        yAxis: { type: "value" },
      }),
    }),
  );

  await page.route(`${API_BASE}/v1/widgets/w-kpi-001/data`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        value: 2,
        label: "Blocked Tasks",
        change: "+1 from last sprint",
        trend: "up",
      }),
    }),
  );

  // Chat/converse for NL widget creation (SSE endpoint)
  await page.route(`${API_BASE}/v1/conversation/message*`, (route) => {
    const sseBody = [
      `data: ${JSON.stringify({ content: 'I\'ve created a "Tasks by Status" bar chart widget on your custom dashboard. It shows the breakdown of tasks across different statuses.' })}\n\n`,
      `data: ${JSON.stringify({ done: true, turn_id: "turn-widget-001", sources_used: [{ source_type: "jira", item_count: 30 }] })}\n\n`,
    ].join("");
    return route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: { "Cache-Control": "no-cache" },
      body: sseBody,
    });
  });

  // Widget CRUD endpoints
  await page.route(`${API_BASE}/v1/widgets`, (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(SAMPLE_WIDGET_BAR),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data: dashboardHasWidgets
          ? [SAMPLE_WIDGET_BAR, SAMPLE_WIDGET_KPI]
          : [],
        total: dashboardHasWidgets ? 2 : 0,
      }),
    });
  });

  await page.route(`${API_BASE}/v1/widgets/w-bar-001`, (route) => {
    if (route.request().method() === "DELETE") {
      return route.fulfill({ status: 204 });
    }
    if (route.request().method() === "PATCH") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...SAMPLE_WIDGET_BAR,
          title: "Updated Tasks Chart",
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SAMPLE_WIDGET_BAR),
    });
  });

  await page.route(`${API_BASE}/v1/widgets/w-kpi-001`, (route) => {
    if (route.request().method() === "DELETE") {
      return route.fulfill({ status: 204 });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SAMPLE_WIDGET_KPI),
    });
  });
}

test.describe("Widget Management", () => {
  test.describe("Empty custom dashboard", () => {
    test("empty custom dashboard shows prompt to add widgets", async ({
      page,
    }) => {
      await setupWidgetRoutes(page, { dashboardHasWidgets: false });

      await page.goto("/projects/proj-widget/custom");

      // Page heading
      await expect(
        page.getByRole("heading", { name: "Custom Dashboard", level: 1 }),
      ).toBeVisible({ timeout: 10000 });

      // Empty state prompt
      await expect(
        page.getByText("Ask ChiefOps to add a chart"),
      ).toBeVisible();

      await expect(
        page.getByText(
          /Use the chat to describe what you want to see/i,
        ),
      ).toBeVisible();

      // Example prompts should be listed
      await expect(page.getByText("Example prompts")).toBeVisible();
      await expect(
        page.getByText(
          /Show me a velocity chart for the last 4 sprints/i,
        ),
      ).toBeVisible();
      await expect(
        page.getByText(/Add a pie chart of tasks by assignee/i),
      ).toBeVisible();

      // Back to Project link should work
      await expect(page.getByText("Back to Project")).toBeVisible();
    });
  });

  test.describe("Widget creation via NL", () => {
    test("widget can be created through chat interaction", async ({
      page,
    }) => {
      await setupWidgetRoutes(page, { dashboardHasWidgets: false });

      await page.goto("/projects/proj-widget/custom");

      // Verify empty state is shown
      await expect(
        page.getByText("Ask ChiefOps to add a chart"),
      ).toBeVisible({ timeout: 10000 });

      // Open chat sidebar
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Type a widget creation request
      const chatInput = page.locator(
        'textarea[placeholder*="Ask"], input[placeholder*="Ask"]',
      );
      await chatInput.fill(
        "Add a bar chart showing tasks by status for this project",
      );

      // Send the message
      await page.getByRole("button", { name: "Send message" }).click();

      // The AI should respond confirming the widget was created
      await expect(
        page.getByText(/I've created a.*Tasks by Status/i),
      ).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Widget rendering", () => {
    test("widgets render after creation on the custom dashboard", async ({
      page,
    }) => {
      await setupWidgetRoutes(page, { dashboardHasWidgets: true });

      await page.goto("/projects/proj-widget/custom");

      // Dashboard header with widget count badge
      await expect(
        page.getByRole("heading", { name: "Custom Dashboard", level: 1 }),
      ).toBeVisible({ timeout: 10000 });

      await expect(page.getByText("2 widgets")).toBeVisible();

      // Widget titles should be rendered in their cards
      await expect(page.getByText("Tasks by Status")).toBeVisible();
      await expect(page.getByText("Blocker Count")).toBeVisible();

      // Each widget should have a refresh button
      const refreshButtons = page.getByRole("button", {
        name: /Refresh/i,
      });
      await expect(refreshButtons.first()).toBeVisible();
    });
  });

  test.describe("Widget editing via NL", () => {
    test("widget can be edited through chat interaction", async ({
      page,
    }) => {
      await setupWidgetRoutes(page, { dashboardHasWidgets: true });

      // Override chat response for edit scenario (SSE endpoint)
      await page.route(`${API_BASE}/v1/conversation/message*`, (route) => {
        const sseBody = [
          `data: ${JSON.stringify({ content: 'I\'ve updated the "Tasks by Status" widget. The chart title has been changed to "Updated Tasks Chart" and the visualization has been refreshed.' })}\n\n`,
          `data: ${JSON.stringify({ done: true, turn_id: "turn-edit-001", sources_used: [{ source_type: "jira", item_count: 30 }] })}\n\n`,
        ].join("");
        return route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          headers: { "Cache-Control": "no-cache" },
          body: sseBody,
        });
      });

      await page.goto("/projects/proj-widget/custom");

      // Widgets should be visible
      await expect(page.getByText("Tasks by Status")).toBeVisible({
        timeout: 10000,
      });

      // Open chat sidebar
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Send an edit request
      const chatInput = page.locator(
        'textarea[placeholder*="Ask"], input[placeholder*="Ask"]',
      );
      await chatInput.fill(
        'Rename the "Tasks by Status" widget to "Updated Tasks Chart"',
      );
      await page.getByRole("button", { name: "Send message" }).click();

      // The AI should confirm the edit
      await expect(
        page.getByText(/I've updated the.*Tasks by Status/i),
      ).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Widget deletion", () => {
    test("widget can be deleted from the dashboard", async ({ page }) => {
      // Start with widgets, then simulate deletion via chat
      await setupWidgetRoutes(page, { dashboardHasWidgets: true });

      // Override chat response for delete scenario (SSE endpoint)
      await page.route(`${API_BASE}/v1/conversation/message*`, (route) => {
        const sseBody = [
          `data: ${JSON.stringify({ content: 'I\'ve removed the "Blocker Count" widget from your custom dashboard. You now have 1 widget remaining.' })}\n\n`,
          `data: ${JSON.stringify({ done: true, turn_id: "turn-delete-001", sources_used: [] })}\n\n`,
        ].join("");
        return route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          headers: { "Cache-Control": "no-cache" },
          body: sseBody,
        });
      });

      await page.goto("/projects/proj-widget/custom");

      // Both widgets should initially be visible
      await expect(page.getByText("Tasks by Status")).toBeVisible({
        timeout: 10000,
      });
      await expect(page.getByText("Blocker Count")).toBeVisible();

      // Open chat sidebar
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Send a delete request via chat
      const chatInput = page.locator(
        'textarea[placeholder*="Ask"], input[placeholder*="Ask"]',
      );
      await chatInput.fill("Remove the Blocker Count widget");
      await page.getByRole("button", { name: "Send message" }).click();

      // The AI should confirm the deletion
      await expect(
        page.getByText(/removed the.*Blocker Count.*widget/i),
      ).toBeVisible({ timeout: 10000 });
    });
  });
});
