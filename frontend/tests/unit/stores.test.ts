import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock axios before importing stores
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from "@/lib/api";
import { useProjectStore } from "@/stores/projectStore";
import { usePeopleStore } from "@/stores/peopleStore";
import { useAlertStore } from "@/stores/alertStore";
import { useSettingsStore } from "@/stores/settingsStore";

describe("projectStore", () => {
  beforeEach(() => {
    useProjectStore.setState({
      projects: [],
      selectedProject: null,
      analysis: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("has correct initial state", () => {
    const state = useProjectStore.getState();
    expect(state.projects).toEqual([]);
    expect(state.selectedProject).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("sets loading state during fetch", async () => {
    const mockProjects = [
      { project_id: "1", name: "Alpha", status: "on_track" },
    ];
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockProjects });

    const promise = useProjectStore.getState().fetchProjects();
    expect(useProjectStore.getState().isLoading).toBe(true);

    await promise;
    expect(useProjectStore.getState().isLoading).toBe(false);
    expect(useProjectStore.getState().projects).toEqual(mockProjects);
  });

  it("handles fetch error", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

    await useProjectStore.getState().fetchProjects().catch(() => {});
    expect(useProjectStore.getState().error).toBeTruthy();
  });
});

describe("peopleStore", () => {
  beforeEach(() => {
    usePeopleStore.setState({
      people: [],
      selectedPerson: null,
      filters: {},
      total: 0,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("has correct initial state", () => {
    const state = usePeopleStore.getState();
    expect(state.people).toEqual([]);
    expect(state.selectedPerson).toBeNull();
    expect(state.total).toBe(0);
  });

  it("sets filters", () => {
    usePeopleStore.getState().setFilters({ department: "Engineering" });
    expect(usePeopleStore.getState().filters).toEqual({
      department: "Engineering",
    });
  });
});

describe("alertStore", () => {
  beforeEach(() => {
    useAlertStore.setState({
      alerts: [],
      triggeredAlerts: [],
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("has correct initial state", () => {
    const state = useAlertStore.getState();
    expect(state.alerts).toEqual([]);
    expect(state.triggeredAlerts).toEqual([]);
  });
});

describe("settingsStore", () => {
  beforeEach(() => {
    useSettingsStore.setState({
      settings: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("has correct initial state", () => {
    const state = useSettingsStore.getState();
    expect(state.settings).toBeNull();
  });
});
