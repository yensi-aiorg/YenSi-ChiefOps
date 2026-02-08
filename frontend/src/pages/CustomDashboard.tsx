import { useEffect, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import {
  BarChart3,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import ReactEChartsCore from "echarts-for-react";
import { useDashboardStore, type WidgetPayload } from "@/stores/dashboardStore";
import { cn } from "@/lib/utils";
import type { WidgetSpec, WidgetType } from "@/types";

/* ================================================================== */
/*  Widget Content by Type                                             */
/* ================================================================== */

function WidgetContent({
  type,
  payload,
}: {
  type: WidgetType;
  payload: unknown;
}) {
  switch (type) {
    case "bar_chart":
    case "line_chart":
    case "pie_chart":
    case "scatter_chart":
    case "area_chart": {
      const option =
        typeof payload === "object" && payload !== null && "series" in payload
          ? payload
          : {
              tooltip: { trigger: "axis" },
              grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
              xAxis: {
                type: "category",
                data: Array.isArray(payload)
                  ? payload.map((_: unknown, i: number) => `Item ${i + 1}`)
                  : [],
              },
              yAxis: { type: "value" },
              series: [
                {
                  type: type.replace("_chart", ""),
                  data: Array.isArray(payload) ? payload : [],
                  smooth: type === "line_chart" || type === "area_chart",
                  areaStyle: type === "area_chart" ? {} : undefined,
                },
              ],
            };

      return (
        <ReactEChartsCore
          option={option as Record<string, unknown>}
          style={{ width: "100%", height: "100%", minHeight: "200px" }}
          notMerge
          lazyUpdate
        />
      );
    }

    case "metric_card": {
      const metric = payload as {
        value?: string | number;
        label?: string;
        change?: string;
        trend?: string;
      };
      return (
        <div className="flex h-full flex-col items-center justify-center text-center">
          <p className="text-3xl font-bold text-slate-900 dark:text-white">
            {metric.value ?? "--"}
          </p>
          {metric.label && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {metric.label}
            </p>
          )}
          {metric.change && (
            <p
              className={cn(
                "mt-1 text-xs font-medium",
                metric.trend === "up"
                  ? "text-green-600 dark:text-green-400"
                  : metric.trend === "down"
                    ? "text-red-600 dark:text-red-400"
                    : "text-slate-500",
              )}
            >
              {metric.change}
            </p>
          )}
        </div>
      );
    }

    case "table": {
      const tableData = payload as {
        headers?: string[];
        rows?: (string | number)[][];
      };
      if (!tableData.headers || !tableData.rows) {
        return (
          <p className="text-xs text-slate-400">Invalid table data format</p>
        );
      }
      return (
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                {tableData.headers.map((h, i) => (
                  <th
                    key={i}
                    className="pb-2 pr-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {tableData.rows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="py-2 pr-3 text-sm text-slate-700 dark:text-slate-300"
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    case "markdown":
    case "summary_text": {
      return (
        <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {String(payload)}
        </div>
      );
    }

    default: {
      return (
        <pre className="overflow-auto text-xs text-slate-600 dark:text-slate-400">
          {JSON.stringify(payload, null, 2)}
        </pre>
      );
    }
  }
}

/* ================================================================== */
/*  Widget Renderer                                                    */
/* ================================================================== */

function WidgetRenderer({
  widget,
  data,
  onRefresh,
}: {
  widget: WidgetSpec;
  data: WidgetPayload | undefined;
  onRefresh: () => void;
}) {
  const isLoading = data?.loading ?? true;
  const hasError = !!data?.error;
  const payload = data?.payload;

  return (
    <div
      className="card flex flex-col overflow-hidden"
      style={{
        gridRow: `${widget.position.row} / span ${widget.position.height}`,
        gridColumn: `${widget.position.col} / span ${widget.position.width}`,
      }}
    >
      {/* Widget header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 dark:border-slate-800">
        <h4 className="truncate text-sm font-semibold text-slate-900 dark:text-white">
          {widget.title}
        </h4>
        <button
          onClick={onRefresh}
          className="rounded p-1 text-slate-400 transition-colors hover:text-slate-600 dark:hover:text-slate-300"
          aria-label={`Refresh ${widget.title}`}
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5", isLoading && "animate-spin")}
          />
        </button>
      </div>

      {/* Widget body */}
      <div className="flex-1 p-4">
        {isLoading && !payload && (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
          </div>
        )}

        {hasError && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <AlertCircle className="mb-2 h-6 w-6 text-red-400" />
            <p className="text-xs text-red-600 dark:text-red-400">
              {data?.error}
            </p>
            <button
              onClick={onRefresh}
              className="mt-2 text-xs font-medium text-teal-600 hover:text-teal-700 dark:text-teal-400"
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !hasError && payload && (
          <WidgetContent type={widget.widget_type} payload={payload} />
        )}

        {!isLoading && !hasError && !payload && (
          <div className="flex h-full items-center justify-center text-xs text-slate-400">
            No data available
          </div>
        )}
      </div>

      {data?.lastUpdated && (
        <div className="border-t border-slate-100 px-4 py-1.5 dark:border-slate-800">
          <p className="text-2xs text-slate-400 dark:text-slate-500">
            Updated{" "}
            {new Date(data.lastUpdated).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      )}
    </div>
  );
}

/* ================================================================== */
/*  Empty State                                                        */
/* ================================================================== */

function EmptyCustomDashboard() {
  const prompts = [
    '"Show me a velocity chart for the last 4 sprints"',
    '"Add a pie chart of tasks by assignee"',
    '"Create a metric card showing our blocker count"',
    '"Add a table of overdue tasks sorted by priority"',
  ];

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
        <Sparkles className="h-10 w-10 text-teal-600 dark:text-teal-400" />
      </div>
      <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
        Ask ChiefOps to add a chart
      </h2>
      <p className="mb-6 max-w-md text-sm text-slate-500 dark:text-slate-400">
        Use the chat to describe what you want to see. ChiefOps will
        automatically create and position widgets on your dashboard.
      </p>
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Example prompts
        </p>
        <div className="flex flex-col gap-2">
          {prompts.map((prompt) => (
            <div
              key={prompt}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm italic text-slate-600 dark:border-slate-700 dark:bg-surface-dark-card dark:text-slate-400"
            >
              {prompt}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Custom Dashboard Page                                              */
/* ================================================================== */

export function CustomDashboard() {
  const { projectId } = useParams<{ projectId: string }>();
  const {
    dashboard,
    widgetData,
    isLoading,
    error,
    fetchDashboard,
    fetchWidgetData,
  } = useDashboardStore();

  // Load dashboard for this project
  useEffect(() => {
    if (projectId) {
      fetchDashboard(projectId);
    }
  }, [projectId, fetchDashboard]);

  // Load widget data when dashboard loads
  useEffect(() => {
    if (dashboard?.widgets) {
      dashboard.widgets.forEach((w) => {
        if (!widgetData[w.widget_id]) {
          fetchWidgetData(w.widget_id);
        }
      });
    }
  }, [dashboard, widgetData, fetchWidgetData]);

  const widgets = dashboard?.widgets ?? [];

  // Compute the grid row count from widget positions
  const maxRow = useMemo(() => {
    if (widgets.length === 0) return 1;
    return Math.max(
      ...widgets.map((w) => w.position.row + w.position.height - 1),
    );
  }, [widgets]);

  if (isLoading && !dashboard) {
    return (
      <div className="animate-fade-in space-y-6">
        <div className="flex items-center gap-3">
          <div className="skeleton h-6 w-6 rounded" />
          <div className="skeleton h-7 w-48" />
        </div>
        <div className="grid grid-cols-12 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className={cn(
                "card space-y-3",
                i <= 2 ? "col-span-6" : "col-span-4",
              )}
            >
              <div className="skeleton h-5 w-32" />
              <div className="skeleton h-40 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Back link */}
      <Link
        to={`/projects/${projectId}`}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Project
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart3 className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Custom Dashboard
        </h1>
        {dashboard && (
          <span className="badge-neutral">
            {widgets.length} widget{widgets.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && widgets.length === 0 && <EmptyCustomDashboard />}

      {/* Widget grid -- 12-column CSS Grid */}
      {widgets.length > 0 && (
        <div
          className="grid grid-cols-12 gap-4"
          style={{
            gridTemplateRows: `repeat(${maxRow}, minmax(200px, auto))`,
          }}
        >
          {widgets.map((widget) => (
            <WidgetRenderer
              key={widget.widget_id}
              widget={widget}
              data={widgetData[widget.widget_id]}
              onRefresh={() => fetchWidgetData(widget.widget_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
