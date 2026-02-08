import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { AppSettings } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface SettingsState {
  settings: AppSettings | null;
  isLoading: boolean;
  error: string | null;
}

interface SettingsActions {
  /** Fetch the current application settings. */
  fetchSettings: () => Promise<void>;

  /** Update settings with a partial patch. */
  updateSettings: (updates: Partial<AppSettings>) => Promise<void>;

  /** Export all application data. Triggers a JSON file download. */
  exportData: () => Promise<void>;

  /** Permanently clear all application data (projects, people, etc.). */
  clearAllData: () => Promise<void>;

  /** Clear the error state. */
  clearError: () => void;
}

type SettingsStore = SettingsState & SettingsActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSettingsStore = create<SettingsStore>()(
  devtools(
    (set) => ({
      // -- state --
      settings: null,
      isLoading: false,
      error: null,

      // -- actions --

      fetchSettings: async () => {
        set({ isLoading: true, error: null }, false, "fetchSettings/start");
        try {
          const { data } = await api.get<AppSettings>("/v1/settings");

          set(
            { settings: data, isLoading: false },
            false,
            "fetchSettings/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch settings";
          set(
            { error: message, isLoading: false },
            false,
            "fetchSettings/error",
          );
          throw err;
        }
      },

      updateSettings: async (updates) => {
        set({ isLoading: true, error: null }, false, "updateSettings/start");
        try {
          const { data } = await api.patch<AppSettings>(
            "/v1/settings",
            updates,
          );

          set(
            { settings: data, isLoading: false },
            false,
            "updateSettings/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to update settings";
          set(
            { error: message, isLoading: false },
            false,
            "updateSettings/error",
          );
          throw err;
        }
      },

      exportData: async () => {
        set({ isLoading: true, error: null }, false, "exportData/start");
        try {
          const response = await api.post("/v1/settings/data/export", null, {
            responseType: "blob",
          });

          // Trigger browser download.
          const url = window.URL.createObjectURL(response.data);
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute(
            "download",
            `chiefops-export-${new Date().toISOString().slice(0, 10)}.json`,
          );
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);

          set({ isLoading: false }, false, "exportData/success");
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to export data";
          set(
            { error: message, isLoading: false },
            false,
            "exportData/error",
          );
          throw err;
        }
      },

      clearAllData: async () => {
        set({ isLoading: true, error: null }, false, "clearAllData/start");
        try {
          await api.delete("/v1/settings/data", { params: { confirm: true } });

          set(
            { settings: null, isLoading: false },
            false,
            "clearAllData/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to clear application data";
          set(
            { error: message, isLoading: false },
            false,
            "clearAllData/error",
          );
          throw err;
        }
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "SettingsStore" },
  ),
);
