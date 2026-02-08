import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { Alert, AlertTriggered } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface AlertState {
  alerts: Alert[];
  triggeredAlerts: AlertTriggered[];
  isLoading: boolean;
  error: string | null;
}

interface AlertActions {
  /** Create a new alert rule from a natural-language description. */
  createAlert: (message: string) => Promise<void>;

  /** Fetch all alert rule definitions. */
  fetchAlerts: () => Promise<void>;

  /** Fetch all triggered (fired) alerts. */
  fetchTriggeredAlerts: () => Promise<void>;

  /** Update an existing alert rule (e.g. enable / disable, rename). */
  updateAlert: (alertId: string, updates: Partial<Alert>) => Promise<void>;

  /** Delete an alert rule. */
  deleteAlert: (alertId: string) => Promise<void>;

  /** Dismiss a single triggered alert. */
  dismissAlert: (triggerId: string) => Promise<void>;

  /** Clear the error state. */
  clearError: () => void;
}

type AlertStore = AlertState & AlertActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAlertStore = create<AlertStore>()(
  devtools(
    (set) => ({
      // -- state --
      alerts: [],
      triggeredAlerts: [],
      isLoading: false,
      error: null,

      // -- actions --

      createAlert: async (message) => {
        set({ isLoading: true, error: null }, false, "createAlert/start");
        try {
          const { data } = await api.post<Alert>("/v1/alerts", { message });

          set(
            (s) => ({
              alerts: [...s.alerts, data],
              isLoading: false,
            }),
            false,
            "createAlert/success",
          );
        } catch (err) {
          const errorMessage =
            err instanceof Error ? err.message : "Failed to create alert";
          set(
            { error: errorMessage, isLoading: false },
            false,
            "createAlert/error",
          );
          throw err;
        }
      },

      fetchAlerts: async () => {
        set({ isLoading: true, error: null }, false, "fetchAlerts/start");
        try {
          const { data } = await api.get<Alert[] | { alerts: Alert[] }>(
            "/v1/alerts",
          );

          const alerts = Array.isArray(data)
            ? data
            : (data as { alerts?: Alert[] }).alerts ?? [];

          set(
            { alerts, isLoading: false },
            false,
            "fetchAlerts/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch alerts";
          set(
            { error: message, isLoading: false },
            false,
            "fetchAlerts/error",
          );
          throw err;
        }
      },

      fetchTriggeredAlerts: async () => {
        set({ isLoading: true, error: null }, false, "fetchTriggeredAlerts/start");
        try {
          const { data } = await api.get<
            AlertTriggered[] | { alerts: AlertTriggered[] }
          >("/v1/alerts/triggered");

          const alerts = Array.isArray(data)
            ? data
            : (data as { alerts?: AlertTriggered[] }).alerts ?? [];

          set(
            { triggeredAlerts: alerts, isLoading: false },
            false,
            "fetchTriggeredAlerts/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch triggered alerts";
          set(
            { error: message, isLoading: false },
            false,
            "fetchTriggeredAlerts/error",
          );
          throw err;
        }
      },

      updateAlert: async (alertId, updates) => {
        set({ isLoading: true, error: null }, false, "updateAlert/start");
        try {
          const { data } = await api.patch<Alert>(
            `/v1/alerts/${alertId}`,
            updates,
          );

          set(
            (s) => ({
              alerts: s.alerts.map((a) =>
                a.alert_id === alertId ? data : a,
              ),
              isLoading: false,
            }),
            false,
            "updateAlert/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to update alert";
          set(
            { error: message, isLoading: false },
            false,
            "updateAlert/error",
          );
          throw err;
        }
      },

      deleteAlert: async (alertId) => {
        set({ isLoading: true, error: null }, false, "deleteAlert/start");
        try {
          await api.delete(`/v1/alerts/${alertId}`);

          set(
            (s) => ({
              alerts: s.alerts.filter((a) => a.alert_id !== alertId),
              isLoading: false,
            }),
            false,
            "deleteAlert/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to delete alert";
          set(
            { error: message, isLoading: false },
            false,
            "deleteAlert/error",
          );
          throw err;
        }
      },

      dismissAlert: async (triggerId) => {
        set({ error: null }, false, "dismissAlert/start");
        try {
          await api.patch(`/v1/alerts/triggered/${triggerId}/dismiss`);

          set(
            (s) => ({
              triggeredAlerts: s.triggeredAlerts.map((t) =>
                t.trigger_id === triggerId
                  ? { ...t, acknowledged: true }
                  : t,
              ),
            }),
            false,
            "dismissAlert/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to dismiss alert";
          set({ error: message }, false, "dismissAlert/error");
          throw err;
        }
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "AlertStore" },
  ),
);
