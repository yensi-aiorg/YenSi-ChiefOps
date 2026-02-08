import { test, expect } from "@playwright/test";

const API_BASE = "http://localhost:23101";

/**
 * Set up standard route mocks so the app loads without onboarding.
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
      body: JSON.stringify({
        data: [
          {
            project_id: "proj-1",
            name: "Demo Project",
            description: "A sample project for testing",
            status: "on_track",
            health_score: 80,
            completion_percentage: 60,
            deadline: "2026-06-01",
            people_involved: [
              {
                person_id: "p-1",
                name: "Alice Chen",
                role: "Tech Lead",
                activity_level: "active",
              },
            ],
            task_summary: {
              total: 20,
              completed: 12,
              in_progress: 5,
              blocked: 0,
              to_do: 3,
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
      body: JSON.stringify({ data: [], total: 0 }),
    }),
  );

  await page.route(`${API_BASE}/v1/dashboards`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], total: 0 }),
    }),
  );
}

test.describe("Natural Language Query (AI Chat)", () => {
  test.describe("Chat sidebar interaction", () => {
    test("chat sidebar opens when AI Chat toggle is clicked", async ({
      page,
    }) => {
      await setupAppRoutes(page);
      await page.goto("/");

      // The AI Chat button in the top bar should be visible
      const chatToggle = page.getByRole("button", {
        name: /Open AI Chat/i,
      });
      await expect(chatToggle).toBeVisible();

      // Click to open chat sidebar
      await chatToggle.click();

      // The chat sidebar header should now be visible
      await expect(page.getByText("ChiefOps AI").first()).toBeVisible();

      // The empty state prompt should show
      await expect(page.getByText("AI Assistant Ready")).toBeVisible();
      await expect(
        page.getByText(/Ask questions about your team, projects/i),
      ).toBeVisible();

      // The chat input should be present
      await expect(
        page.getByPlaceholder("Ask ChiefOps AI anything..."),
      ).toBeVisible();

      // The send button should be visible
      await expect(
        page.getByRole("button", { name: "Send message" }),
      ).toBeVisible();
    });

    test("typing and sending a message adds it to the chat", async ({
      page,
    }) => {
      await setupAppRoutes(page);

      // Mock the chat/converse endpoint
      await page.route(`${API_BASE}/v1/chat/converse`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            turn_id: "turn-resp-001",
            role: "assistant",
            content:
              "Based on the current data, **Demo Project** is on track with 60% completion. The team has 12 out of 20 tasks completed with no blockers.",
            sources_used: [
              { source_type: "jira", item_count: 15 },
              { source_type: "slack", item_count: 8 },
            ],
            timestamp: new Date().toISOString(),
          }),
        }),
      );

      await page.goto("/");

      // Open chat sidebar
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Type a message
      const chatInput = page.getByPlaceholder("Ask ChiefOps AI anything...");
      await chatInput.fill("What is the status of Demo Project?");

      // Send the message
      await page.getByRole("button", { name: "Send message" }).click();

      // The user message should appear in the chat
      await expect(
        page.getByText("What is the status of Demo Project?"),
      ).toBeVisible({ timeout: 5000 });
    });

    test("AI response appears in chat after sending a message", async ({
      page,
    }) => {
      await setupAppRoutes(page);

      const assistantResponse =
        "Based on the current data, **Demo Project** is on track with 60% completion. The team has 12 out of 20 tasks completed with no blockers.";

      // Mock the chat/converse endpoint
      await page.route(`${API_BASE}/v1/chat/converse`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            turn_id: "turn-resp-002",
            role: "assistant",
            content: assistantResponse,
            sources_used: [
              { source_type: "jira", item_count: 15 },
              { source_type: "slack", item_count: 8 },
            ],
            timestamp: new Date().toISOString(),
          }),
        }),
      );

      await page.goto("/");

      // Open chat sidebar
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Send a message
      const chatInput = page.getByPlaceholder("Ask ChiefOps AI anything...");
      await chatInput.fill("Project status update please");
      await page.getByRole("button", { name: "Send message" }).click();

      // Wait for the assistant response to appear
      await expect(
        page.getByText(/Demo Project.*on track/i),
      ).toBeVisible({ timeout: 10000 });

      // The response should contain the key details
      await expect(
        page.getByText(/60% completion/i),
      ).toBeVisible();
    });

    test("source badges are displayed on AI responses", async ({ page }) => {
      await setupAppRoutes(page);

      // Mock chat endpoint with sources
      await page.route(`${API_BASE}/v1/chat/converse`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            turn_id: "turn-resp-003",
            role: "assistant",
            content: "Here is the project summary based on your data sources.",
            sources_used: [
              { source_type: "slack", item_count: 12 },
              { source_type: "jira", item_count: 25 },
              { source_type: "gdrive", item_count: 3 },
            ],
            timestamp: new Date().toISOString(),
          }),
        }),
      );

      await page.goto("/");

      // Open chat
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Send a message
      const chatInput = page.getByPlaceholder("Ask ChiefOps AI anything...");
      await chatInput.fill("Summarize all project data");
      await page.getByRole("button", { name: "Send message" }).click();

      // Wait for response
      await expect(
        page.getByText("Here is the project summary"),
      ).toBeVisible({ timeout: 10000 });

      // Source badges should appear below the message
      await expect(page.getByText("Slack")).toBeVisible();
      await expect(page.getByText("Jira")).toBeVisible();
      await expect(page.getByText("Drive")).toBeVisible();

      // Item counts should appear in the badges
      await expect(page.getByText("(12)")).toBeVisible();
      await expect(page.getByText("(25)")).toBeVisible();
      await expect(page.getByText("(3)")).toBeVisible();
    });

    test("chat history persists when sidebar is closed and reopened", async ({
      page,
    }) => {
      await setupAppRoutes(page);

      // Mock chat endpoint
      await page.route(`${API_BASE}/v1/chat/converse`, (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            turn_id: "turn-persist-001",
            role: "assistant",
            content: "This is a test response that should persist.",
            sources_used: [],
            timestamp: new Date().toISOString(),
          }),
        }),
      );

      await page.goto("/");

      // Open chat and send a message
      await page.getByRole("button", { name: /Open AI Chat/i }).click();
      const chatInput = page.getByPlaceholder("Ask ChiefOps AI anything...");
      await chatInput.fill("Hello, remember this message");
      await page.getByRole("button", { name: "Send message" }).click();

      // Wait for the user message and response to appear
      await expect(
        page.getByText("Hello, remember this message"),
      ).toBeVisible({ timeout: 5000 });
      await expect(
        page.getByText("This is a test response that should persist."),
      ).toBeVisible({ timeout: 10000 });

      // Close the chat sidebar
      await page.getByRole("button", { name: /Close chat/i }).click();

      // The chat content should no longer be visible
      await expect(
        page.getByText("This is a test response that should persist."),
      ).not.toBeVisible();

      // Reopen the chat sidebar
      await page.getByRole("button", { name: /Open AI Chat/i }).click();

      // Previous messages should still be there (persisted in Zustand store)
      await expect(
        page.getByText("Hello, remember this message"),
      ).toBeVisible({ timeout: 5000 });
      await expect(
        page.getByText("This is a test response that should persist."),
      ).toBeVisible();
    });
  });
});
