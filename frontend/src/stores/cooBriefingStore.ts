import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { COOBriefing, COOBriefingStatus, FileSummaryInfo } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface COOBriefingState {
  briefing: COOBriefing | null;
  status: COOBriefingStatus | null;
  fileSummaries: FileSummaryInfo[];
  isLoading: boolean;
  isExporting: boolean;
  isStuck: boolean;
  error: string | null;
}

interface COOBriefingActions {
  fetchBriefing: (projectId: string) => Promise<void>;
  fetchBriefingStatus: (projectId: string) => Promise<void>;
  fetchFileSummaries: (projectId: string) => Promise<void>;
  regenerateBriefing: (projectId: string) => Promise<void>;
  exportBriefingPdf: (projectId: string) => Promise<void>;
  startPolling: (projectId: string) => void;
  stopPolling: () => void;
  reset: () => void;
}

type COOBriefingStore = COOBriefingState & COOBriefingActions;

let pollInterval: ReturnType<typeof setInterval> | null = null;
let pollCount = 0;
const MAX_POLL_ATTEMPTS = 100; // 100 × 3s = 5 minutes

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useCooBriefingStore = create<COOBriefingStore>()(
  devtools(
    (set, get) => ({
      // -- state --
      briefing: null,
      status: null,
      fileSummaries: [],
      isLoading: false,
      isExporting: false,
      isStuck: false,
      error: null,

      // -- actions --

      fetchBriefing: async (projectId) => {
        try {
          const { data } = await api.get<COOBriefing>(
            `/v1/projects/${projectId}/coo-briefing`,
          );
          // Normalize: CLI may return envelope with structured_output nested
          if (data?.briefing && "structured_output" in (data.briefing as Record<string, unknown>)) {
            data.briefing = (data.briefing as Record<string, unknown>).structured_output as COOBriefing["briefing"];
          }
          set({ briefing: data, error: null }, false, "fetchBriefing/success");
        } catch (err) {
          // 404 is expected when no briefing exists yet
          const status = (err as { response?: { status?: number } })?.response?.status;
          if (status === 404) {
            set({ briefing: null }, false, "fetchBriefing/not-found");
          } else {
            const message =
              err instanceof Error ? err.message : "Failed to fetch briefing";
            set({ error: message }, false, "fetchBriefing/error");
          }
        }
      },

      fetchBriefingStatus: async (projectId) => {
        try {
          const { data } = await api.get<COOBriefingStatus>(
            `/v1/projects/${projectId}/coo-briefing/status`,
          );
          set({ status: data }, false, "fetchBriefingStatus/success");
        } catch {
          // Non-critical
        }
      },

      fetchFileSummaries: async (projectId) => {
        try {
          const { data } = await api.get<
            { summaries: FileSummaryInfo[] } | FileSummaryInfo[]
          >(`/v1/projects/${projectId}/file-summaries`);
          const summaries = Array.isArray(data)
            ? data
            : (data as { summaries?: FileSummaryInfo[] }).summaries ?? [];
          set({ fileSummaries: summaries }, false, "fetchFileSummaries/success");
        } catch {
          set({ fileSummaries: [] }, false, "fetchFileSummaries/error");
        }
      },

      regenerateBriefing: async (projectId) => {
        try {
          await api.post(`/v1/projects/${projectId}/coo-briefing/regenerate`);
          // Start polling to pick up the new briefing
          get().startPolling(projectId);
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to regenerate briefing";
          set({ error: message }, false, "regenerateBriefing/error");
        }
      },

      exportBriefingPdf: async (projectId) => {
        set({ isExporting: true, error: null }, false, "exportBriefingPdf/start");
        try {
          const response = await api.get<Blob>(
            `/v1/projects/${projectId}/coo-briefing/export/pdf`,
            { responseType: "blob" },
          );

          const url = window.URL.createObjectURL(response.data);
          const link = document.createElement("a");
          link.href = url;

          const disposition = response.headers["content-disposition"] as
            | string
            | undefined;
          let filename = `coo_briefing_${projectId}.pdf`;
          if (disposition) {
            const match = /filename="?([^";\n]+)"?/.exec(disposition);
            if (match?.[1]) {
              filename = match[1];
            }
          }

          link.setAttribute("download", filename);
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);

          set({ isExporting: false }, false, "exportBriefingPdf/success");
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to export PDF";
          set(
            { error: message, isExporting: false },
            false,
            "exportBriefingPdf/error",
          );
          throw err;
        }
      },

      startPolling: (projectId) => {
        const store = get();
        store.stopPolling();

        // Reset timeout tracking
        pollCount = 0;

        // Initial fetch
        set({ isLoading: true, isStuck: false }, false, "startPolling/init");
        Promise.all([
          store.fetchBriefingStatus(projectId),
          store.fetchBriefing(projectId),
          store.fetchFileSummaries(projectId),
        ]).then(() => {
          set({ isLoading: false }, false, "startPolling/loaded");
        });

        pollInterval = setInterval(async () => {
          pollCount++;

          // Timeout: stop polling and mark as stuck
          if (pollCount >= MAX_POLL_ATTEMPTS) {
            set({ isStuck: true }, false, "startPolling/stuck");
            get().stopPolling();
            return;
          }

          const s = get();
          await s.fetchBriefingStatus(projectId);

          const currentStatus = get().status;
          if (
            currentStatus?.pipeline_status === "completed" ||
            currentStatus?.pipeline_status === "failed"
          ) {
            // Final fetch of briefing + summaries, then stop polling
            await Promise.all([
              get().fetchBriefing(projectId),
              get().fetchFileSummaries(projectId),
            ]);
            get().stopPolling();
          } else if (currentStatus?.pipeline_status === "processing") {
            // Update summaries to show progress
            await get().fetchFileSummaries(projectId);
          }
        }, 3000);
      },

      stopPolling: () => {
        if (pollInterval) {
          clearInterval(pollInterval);
          pollInterval = null;
        }
      },

      reset: () => {
        get().stopPolling();
        set(
          {
            briefing: null,
            status: null,
            fileSummaries: [],
            isLoading: false,
            isExporting: false,
            isStuck: false,
            error: null,
          },
          false,
          "reset",
        );
      },
    }),
    { name: "COOBriefingStore" },
  ),
);
