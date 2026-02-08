import { useEffect, useRef, useCallback, useState } from "react";
import { useDashboardStore } from "@/stores/dashboardStore";

/* ------------------------------------------------------------------ */
/*  useWidgetData – fetch & auto-refresh data for a single widget      */
/* ------------------------------------------------------------------ */

export interface UseWidgetDataOptions {
  /** Whether to poll on an interval (default: false) */
  autoRefresh?: boolean;
  /** Polling interval in milliseconds (default: 60000 = 1 minute) */
  refreshInterval?: number;
}

export interface UseWidgetDataReturn {
  /** The widget data payload (type is unknown – cast at the consumer) */
  data: unknown;
  /** Whether data is currently being fetched */
  isLoading: boolean;
  /** Error message if the last fetch failed */
  error: string | null;
  /** Manually trigger a data refresh */
  refresh: () => Promise<void>;
}

export function useWidgetData(
  widgetId: string,
  options: UseWidgetDataOptions = {},
): UseWidgetDataReturn {
  const { autoRefresh = false, refreshInterval = 60_000 } = options;

  const fetchWidgetData = useDashboardStore((s) => s.fetchWidgetData);
  const widgetDataMap = useDashboardStore((s) => s.widgetData);
  const storeError = useDashboardStore((s) => s.error);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  const data = widgetDataMap.get(widgetId) ?? null;

  const refresh = useCallback(async () => {
    if (!isMountedRef.current) return;
    setIsLoading(true);
    setError(null);

    try {
      await fetchWidgetData(widgetId);
    } catch (err) {
      if (isMountedRef.current) {
        const msg =
          err instanceof Error ? err.message : "Failed to fetch widget data";
        setError(msg);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [fetchWidgetData, widgetId]);

  // Initial fetch on mount
  useEffect(() => {
    isMountedRef.current = true;
    void refresh();

    return () => {
      isMountedRef.current = false;
    };
    // Only run on mount or when widgetId changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [widgetId]);

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh || refreshInterval <= 0) return;

    intervalRef.current = setInterval(() => {
      void refresh();
    }, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval, refresh]);

  return {
    data,
    isLoading,
    error: error ?? storeError,
    refresh,
  };
}
