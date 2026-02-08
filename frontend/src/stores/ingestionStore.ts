import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import { WebSocketClient } from "@/lib/websocket";
import type { IngestionJob } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface IngestionState {
  jobs: IngestionJob[];
  activeJobId: string | null;
  uploadProgress: Map<string, number>;
  isUploading: boolean;
  error: string | null;
}

interface IngestionActions {
  /** Upload one or more files via multipart/form-data. */
  uploadFiles: (files: File[]) => Promise<void>;

  /** Fetch all ingestion jobs. */
  fetchJobs: () => Promise<void>;

  /** Fetch a single ingestion job by ID. */
  fetchJob: (jobId: string) => Promise<void>;

  /** Delete an ingestion job. */
  deleteJob: (jobId: string) => Promise<void>;

  /**
   * Connect a WebSocket to receive real-time progress updates for a job.
   * Returns a cleanup function that disconnects the WebSocket.
   */
  connectWebSocket: (jobId: string) => () => void;

  /** Set the active job ID. */
  setActiveJob: (jobId: string | null) => void;

  /** Clear the error state. */
  clearError: () => void;
}

type IngestionStore = IngestionState & IngestionActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useIngestionStore = create<IngestionStore>()(
  devtools(
    (set, get) => ({
      // -- state --
      jobs: [],
      activeJobId: null,
      uploadProgress: new Map<string, number>(),
      isUploading: false,
      error: null,

      // -- actions --

      uploadFiles: async (files) => {
        set(
          { isUploading: true, error: null },
          false,
          "uploadFiles/start",
        );

        try {
          const formData = new FormData();
          for (const file of files) {
            formData.append("files", file);
          }

          // Initialise per-file progress tracking.
          const progressMap = new Map<string, number>();
          for (const file of files) {
            progressMap.set(file.name, 0);
          }
          set({ uploadProgress: progressMap }, false, "uploadFiles/progressInit");

          const { data } = await api.post<IngestionJob>(
            "/v1/ingestion/upload",
            formData,
            {
              headers: { "Content-Type": "multipart/form-data" },
              onUploadProgress: (progressEvent) => {
                if (progressEvent.total) {
                  const pct = Math.round(
                    (progressEvent.loaded / progressEvent.total) * 100,
                  );
                  // Update all file entries with the aggregate progress.
                  const updated = new Map(get().uploadProgress);
                  for (const file of files) {
                    updated.set(file.name, pct);
                  }
                  set(
                    { uploadProgress: updated },
                    false,
                    "uploadFiles/progress",
                  );
                }
              },
            },
          );

          // Add the new job to the list and set it as active.
          set(
            (s) => ({
              jobs: [data, ...s.jobs],
              activeJobId: data.job_id,
              isUploading: false,
            }),
            false,
            "uploadFiles/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to upload files";
          set(
            { error: message, isUploading: false },
            false,
            "uploadFiles/error",
          );
          throw err;
        }
      },

      fetchJobs: async () => {
        set({ error: null }, false, "fetchJobs/start");
        try {
          const { data } = await api.get<
            IngestionJob[] | { jobs: IngestionJob[] }
          >("/v1/ingestion/jobs");

          const jobs = Array.isArray(data)
            ? data
            : (data as Record<string, unknown>).jobs as IngestionJob[] ??
              (data as Record<string, unknown>).items as IngestionJob[] ??
              [];

          set({ jobs }, false, "fetchJobs/success");
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch ingestion jobs";
          set({ error: message }, false, "fetchJobs/error");
          throw err;
        }
      },

      fetchJob: async (jobId) => {
        set({ error: null }, false, "fetchJob/start");
        try {
          const { data } = await api.get<IngestionJob>(
            `/v1/ingestion/jobs/${jobId}`,
          );

          set(
            (s) => ({
              jobs: s.jobs.some((j) => j.job_id === jobId)
                ? s.jobs.map((j) => (j.job_id === jobId ? data : j))
                : [data, ...s.jobs],
              activeJobId: data.job_id,
            }),
            false,
            "fetchJob/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch ingestion job";
          set({ error: message }, false, "fetchJob/error");
          throw err;
        }
      },

      deleteJob: async (jobId) => {
        set({ error: null }, false, "deleteJob/start");
        try {
          await api.delete(`/v1/ingestion/jobs/${jobId}`);

          set(
            (s) => ({
              jobs: s.jobs.filter((j) => j.job_id !== jobId),
              activeJobId:
                s.activeJobId === jobId ? null : s.activeJobId,
            }),
            false,
            "deleteJob/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to delete ingestion job";
          set({ error: message }, false, "deleteJob/error");
          throw err;
        }
      },

      connectWebSocket: (jobId) => {
        // Build the WebSocket URL for this specific job.
        const protocol =
          window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl =
          import.meta.env.VITE_WS_URL ??
          `${protocol}//${window.location.host}/ws`;

        const ws = new WebSocketClient({
          url: `${wsUrl}/ingestion/${jobId}`,
          maxReconnectAttempts: 5,
          reconnectBaseDelay: 2000,
        });

        // Listen for progress updates.
        ws.on("progress", (rawData) => {
          const update = rawData as Partial<IngestionJob>;
          set(
            (s) => ({
              jobs: s.jobs.map((j) =>
                j.job_id === jobId ? { ...j, ...update } : j,
              ),
            }),
            false,
            "ws/progress",
          );
        });

        // Listen for completion.
        ws.on("completed", (rawData) => {
          const finalJob = rawData as IngestionJob;
          set(
            (s) => ({
              jobs: s.jobs.map((j) =>
                j.job_id === jobId ? finalJob : j,
              ),
            }),
            false,
            "ws/completed",
          );
        });

        // Listen for errors.
        ws.on("error", (rawData) => {
          const errData = rawData as { message?: string };
          set(
            { error: errData.message ?? "Ingestion job encountered an error" },
            false,
            "ws/error",
          );
        });

        ws.connect();

        // Return a cleanup function.
        return () => {
          ws.destroy();
        };
      },

      setActiveJob: (jobId) => {
        set({ activeJobId: jobId }, false, "setActiveJob");
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "IngestionStore" },
  ),
);
