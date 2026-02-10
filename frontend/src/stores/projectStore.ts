import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { Project, ProjectFileInfo } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface ProjectState {
  projects: Project[];
  selectedProject: Project | null;
  analysis: unknown | null;
  isLoading: boolean;
  error: string | null;

  // Analysis job polling
  analysisJobId: string | null;
  analysisStatus: string | null;

  // Per-project files
  projectFiles: ProjectFileInfo[];
  isUploadingFiles: boolean;
  uploadError: string | null;
  isSubmittingNote: boolean;
  noteError: string | null;
  lastNoteResult: {
    status: string;
    document_id?: string | null;
    insights_created: number;
    error_message?: string | null;
  } | null;
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

  /** Upload files to a project. */
  uploadProjectFiles: (projectId: string, files: File[]) => Promise<void>;

  /** Fetch files for a project. */
  fetchProjectFiles: (projectId: string) => Promise<void>;

  /** Delete a file from a project. */
  deleteProjectFile: (projectId: string, fileId: string) => Promise<void>;

  /** Submit a free-form project note/transcript. */
  submitProjectNote: (
    projectId: string,
    payload: { title: string; content: string },
  ) => Promise<{
    status: string;
    document_id?: string | null;
    insights_created: number;
    error_message?: string | null;
  }>;

  /** Clear note submission status/error. */
  clearNoteStatus: () => void;
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
      analysisJobId: null,
      analysisStatus: null,
      projectFiles: [],
      isUploadingFiles: false,
      uploadError: null,
      isSubmittingNote: false,
      noteError: null,
      lastNoteResult: null,

      // -- actions --

      fetchProjects: async () => {
        set({ isLoading: true, error: null }, false, "fetchProjects/start");
        try {
          const { data } = await api.get<
            Project[] | { projects: Project[] } | { items: Project[] }
          >("/v1/projects");
          const projects = Array.isArray(data)
            ? data
            : (data as { projects?: Project[]; items?: Project[] }).projects ??
              (data as { items?: Project[] }).items ??
              [];

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
        set(
          { error: null, analysisJobId: null, analysisStatus: null },
          false,
          "triggerAnalysis/start",
        );
        try {
          const { data } = await api.post<{
            job_id: string;
            status: string;
          }>(`/v1/projects/${projectId}/analyze`);

          const jobId = data.job_id;
          set(
            { analysisJobId: jobId, analysisStatus: "pending" },
            false,
            "triggerAnalysis/queued",
          );

          // Poll every 3 seconds for completion.
          const poll = setInterval(async () => {
            try {
              const { data: job } = await api.get<{
                status: string;
                error_message?: string | null;
              }>(`/v1/projects/${projectId}/analysis-jobs/${jobId}`);

              set(
                { analysisStatus: job.status },
                false,
                "triggerAnalysis/poll",
              );

              if (job.status === "completed") {
                clearInterval(poll);
                set(
                  { analysisJobId: null, analysisStatus: null },
                  false,
                  "triggerAnalysis/done",
                );
                // Refetch the project to pick up updated analysis fields.
                await get().fetchProjectDetail(projectId);
              } else if (job.status === "failed") {
                clearInterval(poll);
                set(
                  {
                    analysisJobId: null,
                    analysisStatus: null,
                    error: job.error_message ?? "Analysis failed",
                  },
                  false,
                  "triggerAnalysis/failed",
                );
              }
            } catch {
              // Swallow network errors during poll — keep retrying.
            }
          }, 3000);
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to trigger project analysis";
          set(
            { error: message, analysisJobId: null, analysisStatus: null },
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

      uploadProjectFiles: async (projectId, files) => {
        set(
          { isUploadingFiles: true, uploadError: null },
          false,
          "uploadProjectFiles/start",
        );
        try {
          const formData = new FormData();
          for (const file of files) {
            formData.append("files", file);
          }
          await api.post(
            `/v1/projects/${projectId}/files/upload`,
            formData,
            { headers: { "Content-Type": "multipart/form-data" } },
          );
          set({ isUploadingFiles: false }, false, "uploadProjectFiles/success");
          // Refetch files to get updated list
          await get().fetchProjectFiles(projectId);
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to upload files";
          set(
            { uploadError: message, isUploadingFiles: false },
            false,
            "uploadProjectFiles/error",
          );
          throw err;
        }
      },

      fetchProjectFiles: async (projectId) => {
        try {
          const { data } = await api.get<
            { files: ProjectFileInfo[] } | ProjectFileInfo[]
          >(`/v1/projects/${projectId}/files`);
          const files = Array.isArray(data)
            ? data
            : (data as { files?: ProjectFileInfo[] }).files ?? [];
          set({ projectFiles: files }, false, "fetchProjectFiles/success");
        } catch {
          // Non-critical: silently set empty
          set({ projectFiles: [] }, false, "fetchProjectFiles/error");
        }
      },

      deleteProjectFile: async (projectId, fileId) => {
        try {
          await api.delete(`/v1/projects/${projectId}/files/${fileId}`);
          // Refetch files to get updated list
          await get().fetchProjectFiles(projectId);
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to delete file";
          set(
            { uploadError: message },
            false,
            "deleteProjectFile/error",
          );
          throw err;
        }
      },

      submitProjectNote: async (projectId, payload) => {
        set(
          { isSubmittingNote: true, noteError: null, lastNoteResult: null },
          false,
          "submitProjectNote/start",
        );
        try {
          const { data } = await api.post<{
            status: string;
            document_id?: string | null;
            insights_created: number;
            error_message?: string | null;
          }>(`/v1/projects/${projectId}/files/notes`, payload);

          const responseError =
            data.status === "failed"
              ? data.error_message ?? "Failed to process note"
              : null;
          set(
            {
              isSubmittingNote: false,
              lastNoteResult: data,
              noteError: responseError,
            },
            false,
            "submitProjectNote/success",
          );
          return data;
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to submit note";
          set(
            { isSubmittingNote: false, noteError: message },
            false,
            "submitProjectNote/error",
          );
          throw err;
        }
      },

      clearNoteStatus: () => {
        set(
          { noteError: null, lastNoteResult: null },
          false,
          "clearNoteStatus",
        );
      },
    }),
    { name: "ProjectStore" },
  ),
);
