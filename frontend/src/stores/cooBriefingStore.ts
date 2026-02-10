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
  error: string | null;
}

interface COOBriefingActions {
  fetchBriefing: (projectId: string) => Promise<void>;
  fetchBriefingStatus: (projectId: string) => Promise<void>;
  fetchFileSummaries: (projectId: string) => Promise<void>;
  startPolling: (projectId: string) => void;
  stopPolling: () => void;
  reset: () => void;
}

type COOBriefingStore = COOBriefingState & COOBriefingActions;

let pollInterval: ReturnType<typeof setInterval> | null = null;

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
      error: null,

      // -- actions --

      fetchBriefing: async (projectId) => {
        try {
          const { data } = await api.get<COOBriefing>(
            `/v1/projects/${projectId}/coo-briefing`,
          );
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

      startPolling: (projectId) => {
        const store = get();
        store.stopPolling();

        // Initial fetch
        set({ isLoading: true }, false, "startPolling/init");
        Promise.all([
          store.fetchBriefingStatus(projectId),
          store.fetchBriefing(projectId),
          store.fetchFileSummaries(projectId),
        ]).then(() => {
          set({ isLoading: false }, false, "startPolling/loaded");
        });

        pollInterval = setInterval(async () => {
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
