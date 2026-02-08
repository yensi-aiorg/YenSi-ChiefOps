import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { Project } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface ProjectState {
  projects: Project[];
  selectedProject: Project | null;
  analysis: unknown | null;
  isLoading: boolean;
  error: string | null;
}

interface ProjectActions {
  /** Fetch all projects. */
  fetchProjects: () => Promise<void>;

  /** Fetch a single project by ID. */
  fetchProjectDetail: (projectId: string) => Promise<void>;

  /** Create a new project. */
  createProject: (
    data: Pick<Project, "name" | "description"> & Partial<Project>,
  ) => Promise<void>;

  /** Update an existing project. */
  updateProject: (projectId: string, data: Partial<Project>) => Promise<void>;

  /** Trigger AI analysis for a project. */
  triggerAnalysis: (projectId: string) => Promise<void>;

  /** Set the selected project in local state. */
  setSelectedProject: (project: Project | null) => void;

  /** Clear the error state. */
  clearError: () => void;
}

type ProjectStore = ProjectState & ProjectActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useProjectStore = create<ProjectStore>()(
  devtools(
    (set, get) => ({
      // -- state --
      projects: [],
      selectedProject: null,
      analysis: null,
      isLoading: false,
      error: null,

      // -- actions --

      fetchProjects: async () => {
        set({ isLoading: true, error: null }, false, "fetchProjects/start");
        try {
          const { data } = await api.get<Project[] | { items: Project[] }>(
            "/v1/projects",
          );
          const projects = Array.isArray(data)
            ? data
            : (data as { items: Project[] }).items ?? [];

          set(
            { projects, isLoading: false },
            false,
            "fetchProjects/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch projects";
          set(
            { error: message, isLoading: false },
            false,
            "fetchProjects/error",
          );
          throw err;
        }
      },

      fetchProjectDetail: async (projectId) => {
        set({ isLoading: true, error: null }, false, "fetchProjectDetail/start");
        try {
          const { data } = await api.get<Project>(`/v1/projects/${projectId}`);

          set(
            { selectedProject: data, isLoading: false },
            false,
            "fetchProjectDetail/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch project details";
          set(
            { error: message, isLoading: false },
            false,
            "fetchProjectDetail/error",
          );
          throw err;
        }
      },

      createProject: async (projectData) => {
        set({ isLoading: true, error: null }, false, "createProject/start");
        try {
          const { data } = await api.post<Project>("/v1/projects", projectData);

          set(
            (s) => ({
              projects: [...s.projects, data],
              selectedProject: data,
              isLoading: false,
            }),
            false,
            "createProject/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to create project";
          set(
            { error: message, isLoading: false },
            false,
            "createProject/error",
          );
          throw err;
        }
      },

      updateProject: async (projectId, projectData) => {
        set({ isLoading: true, error: null }, false, "updateProject/start");
        try {
          const { data } = await api.patch<Project>(
            `/v1/projects/${projectId}`,
            projectData,
          );

          set(
            (s) => ({
              projects: s.projects.map((p) =>
                p.project_id === projectId ? data : p,
              ),
              selectedProject:
                s.selectedProject?.project_id === projectId
                  ? data
                  : s.selectedProject,
              isLoading: false,
            }),
            false,
            "updateProject/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to update project";
          set(
            { error: message, isLoading: false },
            false,
            "updateProject/error",
          );
          throw err;
        }
      },

      triggerAnalysis: async (projectId) => {
        set({ isLoading: true, error: null }, false, "triggerAnalysis/start");
        try {
          const { data } = await api.post<unknown>(
            `/v1/projects/${projectId}/analyze`,
          );

          set(
            { analysis: data, isLoading: false },
            false,
            "triggerAnalysis/success",
          );

          // Refetch the project to pick up updated analysis fields.
          await get().fetchProjectDetail(projectId);
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to trigger project analysis";
          set(
            { error: message, isLoading: false },
            false,
            "triggerAnalysis/error",
          );
          throw err;
        }
      },

      setSelectedProject: (project) => {
        set({ selectedProject: project }, false, "setSelectedProject");
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "ProjectStore" },
  ),
);
