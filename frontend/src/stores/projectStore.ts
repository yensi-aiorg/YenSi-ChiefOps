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
  /** Resume polling an in-flight upload job for a project (if any). */
  resumeUploadPolling: (projectId: string) => Promise<void>;
  /** Cancel an in-flight upload/processing job for a project. */
  cancelUploadProcessing: (projectId: string) => Promise<void>;

  /** Fetch files for a project. */
  fetchProjectFiles: (projectId: string) => Promise<void>;

  /** Delete a file from a project. */
  deleteProjectFile: (projectId: string, fileId: string) => Promise<void>;
  /** Retry Citex indexing for an uploaded file. */
  retryProjectFileIndex: (projectId: string, fileId: string) => Promise<void>;

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

const uploadPollers = new Map<string, Promise<void>>();
const uploadCancelRequests = new Set<string>();
const uploadJobStorageKey = (projectId: string) => `chiefops.uploadJob.${projectId}`;

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
          const { data } = await api.post<{
            job_id: string;
            status: string;
          }>(
            `/v1/projects/${projectId}/files/upload`,
            formData,
            {
              headers: { "Content-Type": "multipart/form-data" },
              // Upload + queueing can exceed default timeout on slower links.
              timeout: 0,
            },
          );
          const jobId = data.job_id;
          if (typeof window !== "undefined") {
            window.localStorage.setItem(uploadJobStorageKey(projectId), jobId);
          }
          set(
            { isUploadingFiles: true, uploadError: null },
            false,
            "uploadProjectFiles/queued",
          );
          await get().resumeUploadPolling(projectId);
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

      resumeUploadPolling: async (projectId) => {
        const existing = uploadPollers.get(projectId);
        if (existing) {
          await existing;
          return;
        }

        const jobId =
          typeof window !== "undefined"
            ? window.localStorage.getItem(uploadJobStorageKey(projectId))
            : null;
        if (!jobId) {
          return;
        }

        const pollPromise = (async () => {
          set(
            { isUploadingFiles: true, uploadError: null },
            false,
            "resumeUploadPolling/start",
          );

          for (let attempt = 0; attempt < 600; attempt += 1) {
            if (uploadCancelRequests.has(projectId)) {
              uploadCancelRequests.delete(projectId);
              if (typeof window !== "undefined") {
                window.localStorage.removeItem(uploadJobStorageKey(projectId));
              }
              set(
                { isUploadingFiles: false, uploadError: null },
                false,
                "resumeUploadPolling/cancelled-local",
              );
              return;
            }

            try {
              const { data: job } = await api.get<{
                status: string;
                error_message?: string | null;
              }>(`/v1/projects/${projectId}/files/upload-jobs/${jobId}`);

              if (job.status === "completed") {
                if (typeof window !== "undefined") {
                  window.localStorage.removeItem(uploadJobStorageKey(projectId));
                }
                set(
                  { isUploadingFiles: false, uploadError: null },
                  false,
                  "resumeUploadPolling/completed",
                );
                await get().fetchProjectFiles(projectId);
                return;
              }

              if (job.status === "failed") {
                const message = job.error_message ?? "File upload processing failed.";
                if (typeof window !== "undefined") {
                  window.localStorage.removeItem(uploadJobStorageKey(projectId));
                }
                set(
                  { isUploadingFiles: false, uploadError: message },
                  false,
                  "resumeUploadPolling/failed",
                );
                return;
              }

              if (job.status === "cancelled") {
                if (typeof window !== "undefined") {
                  window.localStorage.removeItem(uploadJobStorageKey(projectId));
                }
                set(
                  { isUploadingFiles: false, uploadError: null },
                  false,
                  "resumeUploadPolling/cancelled-remote",
                );
                await get().fetchProjectFiles(projectId);
                return;
              }
            } catch (err) {
              const message = err instanceof Error ? err.message : "";
              if (message.includes("404")) {
                if (typeof window !== "undefined") {
                  window.localStorage.removeItem(uploadJobStorageKey(projectId));
                }
                set(
                  { isUploadingFiles: false },
                  false,
                  "resumeUploadPolling/not-found",
                );
                return;
              }
              // Keep polling on transient errors.
            }

            await new Promise((resolve) => setTimeout(resolve, 1500));
          }

          set(
            {
              isUploadingFiles: false,
              uploadError: "Upload processing timed out while polling status.",
            },
            false,
            "resumeUploadPolling/timeout",
          );
        })();

        uploadPollers.set(projectId, pollPromise);
        try {
          await pollPromise;
        } finally {
          uploadCancelRequests.delete(projectId);
          uploadPollers.delete(projectId);
        }
      },

      cancelUploadProcessing: async (projectId) => {
        const jobId =
          typeof window !== "undefined"
            ? window.localStorage.getItem(uploadJobStorageKey(projectId))
            : null;

        uploadCancelRequests.add(projectId);

        if (jobId) {
          try {
            await api.post(`/v1/projects/${projectId}/files/upload-jobs/${jobId}/cancel`);
          } catch {
            // Ignore cancel errors; local poll-stop still applies.
          }
        }

        if (typeof window !== "undefined") {
          window.localStorage.removeItem(uploadJobStorageKey(projectId));
        }
        set(
          { isUploadingFiles: false, uploadError: null },
          false,
          "cancelUploadProcessing/done",
        );
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

      retryProjectFileIndex: async (projectId, fileId) => {
        try {
          await api.post(`/v1/projects/${projectId}/files/${fileId}/retry-index`);
          await get().fetchProjectFiles(projectId);
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to retry indexing in Citex";
          set(
            { uploadError: message },
            false,
            "retryProjectFileIndex/error",
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
