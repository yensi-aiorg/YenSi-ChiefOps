import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { Dashboard, WidgetSpec } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface DashboardState {
  dashboards: Dashboard[];
  activeDashboard: Dashboard | null;
  widgets: Map<string, WidgetSpec>;
  widgetData: Map<string, unknown>;
  isLoading: boolean;
  error: string | null;
}

interface DashboardActions {
  /** Fetch all dashboards, optionally scoped to a project. */
  fetchDashboards: (projectId?: string) => Promise<void>;

  /** Fetch a single dashboard by ID and set it as active. */
  fetchDashboard: (dashboardId: string) => Promise<void>;

  /** Add a widget to a dashboard. */
  addWidget: (
    dashboardId: string,
    widgetSpec: Omit<WidgetSpec, "widget_id" | "dashboard_id" | "created_at" | "updated_at">,
  ) => Promise<void>;

  /** Update an existing widget. */
  updateWidget: (widgetId: string, updates: Partial<WidgetSpec>) => Promise<void>;

  /** Remove a widget from its dashboard. */
  removeWidget: (widgetId: string) => Promise<void>;

  /** Fetch data for a specific widget. */
  fetchWidgetData: (widgetId: string) => Promise<void>;

  /** Use NL to generate a new widget from a description. */
  generateWidget: (description: string, dashboardId: string) => Promise<void>;

  /** Use NL to edit an existing widget by sending a free-text instruction. */
  nlEditWidget: (widgetId: string, message: string) => Promise<void>;

  /** Set the active dashboard in local state. */
  setActiveDashboard: (dashboard: Dashboard | null) => void;

  /** Clear the error state. */
  clearError: () => void;
}

type DashboardStore = DashboardState & DashboardActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useDashboardStore = create<DashboardStore>()(
  devtools(
    (set, get) => ({
      // -- state --
      dashboards: [],
      activeDashboard: null,
      widgets: new Map<string, WidgetSpec>(),
      widgetData: new Map<string, unknown>(),
      isLoading: false,
      error: null,

      // -- actions --

      fetchDashboards: async (projectId?) => {
        set({ isLoading: true, error: null }, false, "fetchDashboards/start");
        try {
          const params: Record<string, string> = {};
          if (projectId) params.project_id = projectId;

          const { data } = await api.get<Dashboard[]>("/v1/dashboards", {
            params,
          });

          set(
            { dashboards: data, isLoading: false },
            false,
            "fetchDashboards/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch dashboards";
          set(
            { error: message, isLoading: false },
            false,
            "fetchDashboards/error",
          );
          throw err;
        }
      },

      fetchDashboard: async (dashboardId) => {
        set({ isLoading: true, error: null }, false, "fetchDashboard/start");
        try {
          const { data } = await api.get<Dashboard>(
            `/v1/dashboards/${dashboardId}`,
          );

          set(
            { activeDashboard: data, isLoading: false },
            false,
            "fetchDashboard/success",
          );
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch dashboard details";
          set(
            { error: message, isLoading: false },
            false,
            "fetchDashboard/error",
          );
          throw err;
        }
      },

      addWidget: async (dashboardId, widgetSpec) => {
        set({ isLoading: true, error: null }, false, "addWidget/start");
        try {
          const { data } = await api.post<WidgetSpec>(
            `/v1/dashboards/${dashboardId}/widgets`,
            widgetSpec,
          );

          const widgetsMap = new Map(get().widgets);
          widgetsMap.set(data.widget_id, data);

          // Append the new widget ID to the active dashboard if it matches.
          const active = get().activeDashboard;
          const updatedActive =
            active && active.dashboard_id === dashboardId
              ? {
                  ...active,
                  widget_ids: [...active.widget_ids, data.widget_id],
                }
              : active;

          set(
            {
              widgets: widgetsMap,
              activeDashboard: updatedActive,
              isLoading: false,
            },
            false,
            "addWidget/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to add widget";
          set(
            { error: message, isLoading: false },
            false,
            "addWidget/error",
          );
          throw err;
        }
      },

      updateWidget: async (widgetId, updates) => {
        set({ isLoading: true, error: null }, false, "updateWidget/start");
        try {
          const { data } = await api.patch<WidgetSpec>(
            `/v1/widgets/${widgetId}`,
            updates,
          );

          const widgetsMap = new Map(get().widgets);
          widgetsMap.set(widgetId, data);

          set(
            { widgets: widgetsMap, isLoading: false },
            false,
            "updateWidget/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to update widget";
          set(
            { error: message, isLoading: false },
            false,
            "updateWidget/error",
          );
          throw err;
        }
      },

      removeWidget: async (widgetId) => {
        set({ isLoading: true, error: null }, false, "removeWidget/start");
        try {
          await api.delete(`/v1/widgets/${widgetId}`);

          const widgetsMap = new Map(get().widgets);
          widgetsMap.delete(widgetId);

          const widgetDataMap = new Map(get().widgetData);
          widgetDataMap.delete(widgetId);

          // Remove the widget ID from the active dashboard.
          const active = get().activeDashboard;
          const updatedActive = active
            ? {
                ...active,
                widget_ids: active.widget_ids.filter(
                  (wid) => wid !== widgetId,
                ),
              }
            : null;

          set(
            {
              widgets: widgetsMap,
              widgetData: widgetDataMap,
              activeDashboard: updatedActive,
              isLoading: false,
            },
            false,
            "removeWidget/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to remove widget";
          set(
            { error: message, isLoading: false },
            false,
            "removeWidget/error",
          );
          throw err;
        }
      },

      fetchWidgetData: async (widgetId) => {
        set({ error: null }, false, "fetchWidgetData/start");
        try {
          const { data } = await api.get<unknown>(
            `/v1/widgets/${widgetId}/data`,
          );

          const widgetDataMap = new Map(get().widgetData);
          widgetDataMap.set(widgetId, data);

          set({ widgetData: widgetDataMap }, false, "fetchWidgetData/success");
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch widget data";
          set({ error: message }, false, "fetchWidgetData/error");
          throw err;
        }
      },

      generateWidget: async (description, dashboardId) => {
        set({ isLoading: true, error: null }, false, "generateWidget/start");
        try {
          const { data } = await api.post<WidgetSpec>(
            `/v1/dashboards/${dashboardId}/widgets/generate`,
            { description },
          );

          const widgetsMap = new Map(get().widgets);
          widgetsMap.set(data.widget_id, data);

          const active = get().activeDashboard;
          const updatedActive =
            active && active.dashboard_id === dashboardId
              ? {
                  ...active,
                  widget_ids: [...active.widget_ids, data.widget_id],
                }
              : active;

          set(
            {
              widgets: widgetsMap,
              activeDashboard: updatedActive,
              isLoading: false,
            },
            false,
            "generateWidget/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to generate widget";
          set(
            { error: message, isLoading: false },
            false,
            "generateWidget/error",
          );
          throw err;
        }
      },

      nlEditWidget: async (widgetId, message) => {
        set({ isLoading: true, error: null }, false, "nlEditWidget/start");
        try {
          const { data } = await api.post<WidgetSpec>(
            `/v1/widgets/${widgetId}/nl-edit`,
            { message },
          );

          const widgetsMap = new Map(get().widgets);
          widgetsMap.set(widgetId, data);

          set(
            { widgets: widgetsMap, isLoading: false },
            false,
            "nlEditWidget/success",
          );
        } catch (err) {
          const errorMessage =
            err instanceof Error
              ? err.message
              : "Failed to apply NL edit to widget";
          set(
            { error: errorMessage, isLoading: false },
            false,
            "nlEditWidget/error",
          );
          throw err;
        }
      },

      setActiveDashboard: (dashboard) => {
        set({ activeDashboard: dashboard }, false, "setActiveDashboard");
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "DashboardStore" },
  ),
);
