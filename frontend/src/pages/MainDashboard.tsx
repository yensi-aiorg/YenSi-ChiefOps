import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  Users,
  CheckSquare,
  AlertTriangle,
  Clock,
  TrendingUp,
  Sparkles,
  ArrowRight,
  XCircle,
  RefreshCw,
  Loader2,
} from "lucide-react";
import ReactEChartsCore from "echarts-for-react";
import { useProjectStore } from "@/stores/projectStore";
import { useAlertStore } from "@/stores/alertStore";
import { useDashboardStore } from "@/stores/dashboardStore";
import { cn } from "@/lib/utils";
import {
  formatRelativeTime,
  getHealthScoreBadge,
  getHealthScoreColor,
} from "@/lib/utils";
import {
  transformWidgetData,
  mapBackendWidgetType,
} from "@/lib/widgetDataTransformer";
import type { Project, AlertTriggered, WidgetSpec } from "@/types";
import { WidgetType } from "@/types";

/* ================================================================== */
/*  API → Dashboard adapters                                           */
/* ================================================================== */

/** Map backend health_score string enum to a 0-100 number for the ring. */
function healthToNumber(h: unknown): number | null {
  if (typeof h === "number") return h;
  const map: Record<string, number | null> = {
    healthy: 80,
    at_risk: 45,
    critical: 20,
    unknown: null,
  };
  return typeof h === "string" ? (map[h] ?? null) : null;
}

/** Safely get team_size from a project (API may return team_size or people_involved). */
function getTeamSize(p: Project): number {
  if (typeof (p as Record<string, unknown>).team_size === "number")
    return (p as Record<string, unknown>).team_size as number;
  if (Array.isArray(p.people_involved)) return p.people_involved.length;
  return 0;
}

/** Safely get open tasks count. */
function getOpenTasks(p: Project): number {
  if (typeof (p as Record<string, unknown>).open_tasks === "number")
    return (p as Record<string, unknown>).open_tasks as number;
  if (p.task_summary)
    return p.task_summary.to_do + p.task_summary.in_progress + p.task_summary.blocked;
  return 0;
}

/** Safely get completed tasks count. */
function getCompletedTasks(p: Project): number {
  if (typeof (p as Record<string, unknown>).completed_tasks === "number")
    return (p as Record<string, unknown>).completed_tasks as number;
  if (p.task_summary) return p.task_summary.completed;
  return 0;
}

/** Compute completion percentage from task counts. */
function getCompletionPct(p: Project): number {
  if (typeof p.completion_percentage === "number") return p.completion_percentage;
  const done = getCompletedTasks(p);
  const open = getOpenTasks(p);
  const total = done + open;
  return total > 0 ? (done / total) * 100 : 0;
}

/** Map backend status strings to display labels/colors. */
const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  on_track: "On Track",
  at_risk: "At Risk",
  on_hold: "On Hold",
  behind: "Behind",
  completed: "Completed",
  cancelled: "Cancelled",
};

const STATUS_COLORS: Record<string, string> = {
  active: "badge-teal",
  on_track: "badge-teal",
  at_risk: "badge-warm",
  on_hold: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  behind: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  completed: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  cancelled: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
};

/* ================================================================== */
/*  Section labels for the widget grid                                 */
/* ================================================================== */

const SECTION_LABELS: { minY: number; maxY: number; label: string }[] = [
  { minY: 0, maxY: 1, label: "Executive Summary" },
  { minY: 2, maxY: 9, label: "Project Health & Status" },
  { minY: 10, maxY: 17, label: "Execution & Delivery" },
  { minY: 18, maxY: 21, label: "Team & Capacity" },
  { minY: 22, maxY: 29, label: "Risk & Gap Analysis" },
  { minY: 30, maxY: 99, label: "Forward Planning" },
];

function getSectionLabel(y: number): string {
  return SECTION_LABELS.find((s) => y >= s.minY && y <= s.maxY)?.label ?? "";
}

/* ================================================================== */
/*  Skeleton helpers                                                   */
/* ================================================================== */

function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("card space-y-3", className)}>
      <div className="skeleton h-4 w-24" />
      <div className="skeleton h-8 w-16" />
      <div className="skeleton h-3 w-32" />
    </div>
  );
}

function SkeletonProjectCard() {
  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div className="skeleton h-5 w-40" />
        <div className="skeleton h-6 w-16 rounded-full" />
      </div>
      <div className="skeleton h-3 w-full" />
      <div className="skeleton h-2 w-full rounded-full" />
      <div className="flex items-center justify-between">
        <div className="skeleton h-3 w-20" />
        <div className="skeleton h-3 w-24" />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Widget Content (renders transformed data)                          */
/* ================================================================== */

function WidgetContent({
  type,
  payload,
}: {
  type: string;
  payload: unknown;
}) {
  // Map backend types to frontend types
  const frontendType = mapBackendWidgetType(type);

  switch (frontendType) {
    case WidgetType.BAR_CHART:
    case WidgetType.LINE_CHART:
    case WidgetType.PIE_CHART: {
      // payload is already an ECharts option from the transformer
      const option = payload as Record<string, unknown>;
      return (
        <ReactEChartsCore
          option={option}
          style={{ width: "100%", height: "100%", minHeight: "200px" }}
          notMerge
          lazyUpdate
        />
      );
    }

    case WidgetType.KPI_CARD: {
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

    case WidgetType.TABLE: {
      const tableData = payload as {
        headers?: string[];
        rows?: (string | number)[][];
      };
      if (!tableData.headers || !tableData.rows) {
        return (
          <p className="text-xs text-slate-400">No table data available</p>
        );
      }
      if (tableData.rows.length === 0) {
        return (
          <p className="py-4 text-center text-xs text-slate-400">No data</p>
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

    case WidgetType.SUMMARY_TEXT: {
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
/*  DB-backed Widget Card                                              */
/* ================================================================== */

function DbWidgetCard({
  widget,
  rawData,
  isDataLoading,
  onRefresh,
}: {
  widget: WidgetSpec;
  rawData: unknown;
  isDataLoading: boolean;
  onRefresh: () => void;
}) {
  // Get the backend widget type (stored in the widget spec)
  const backendType =
    (widget as unknown as Record<string, unknown>).widget_type as string;
  const transformed = rawData
    ? transformWidgetData(backendType, rawData)
    : undefined;

  // Read position from widget doc (backend stores as { x, y, w, h })
  const pos = (widget as unknown as Record<string, unknown>).position as
    | { x: number; y: number; w: number; h: number }
    | undefined;

  const style = pos
    ? {
        gridColumn: `${pos.x + 1} / span ${pos.w}`,
        gridRow: `${pos.y + 1} / span ${pos.h}`,
      }
    : {};

  return (
    <div className="card flex flex-col overflow-hidden" style={style}>
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
            className={cn("h-3.5 w-3.5", isDataLoading && "animate-spin")}
          />
        </button>
      </div>

      {/* Widget body */}
      <div className="flex-1 p-4">
        {isDataLoading && transformed === undefined && (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
          </div>
        )}

        {transformed !== undefined && (
          <WidgetContent type={backendType} payload={transformed} />
        )}

        {!isDataLoading && transformed === undefined && (
          <div className="flex h-full items-center justify-center text-xs text-slate-400">
            No data available
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  DB-Backed Default Dashboard View                                   */
/* ================================================================== */

function DefaultDashboardView() {
  const {
    activeDashboard,
    widgets: widgetMap,
    widgetData,
    isLoading: dashboardLoading,
    fetchWidgetData,
  } = useDashboardStore();

  // Resolve widget specs from the active dashboard's widget_ids
  const resolvedWidgets: WidgetSpec[] = useMemo(() => {
    if (!activeDashboard) return [];
    return activeDashboard.widget_ids
      .map((id) => widgetMap.get(id))
      .filter((w): w is WidgetSpec => w !== undefined);
  }, [activeDashboard, widgetMap]);

  // Load widget data when widgets are resolved
  useEffect(() => {
    resolvedWidgets.forEach((w) => {
      if (!widgetData.has(w.widget_id)) {
        fetchWidgetData(w.widget_id);
      }
    });
  }, [resolvedWidgets, widgetData, fetchWidgetData]);

  // Group widgets by section for section headers
  const widgetsBySection = useMemo(() => {
    const sections: { label: string; widgets: WidgetSpec[] }[] = [];
    let currentLabel = "";

    // Sort by y position first
    const sorted = [...resolvedWidgets].sort((a, b) => {
      const posA = (a as unknown as Record<string, unknown>).position as
        | { y: number }
        | undefined;
      const posB = (b as unknown as Record<string, unknown>).position as
        | { y: number }
        | undefined;
      return (posA?.y ?? 0) - (posB?.y ?? 0);
    });

    for (const w of sorted) {
      const pos = (w as unknown as Record<string, unknown>).position as
        | { y: number }
        | undefined;
      const sectionLabel = getSectionLabel(pos?.y ?? 0);
      if (sectionLabel !== currentLabel) {
        currentLabel = sectionLabel;
        sections.push({ label: sectionLabel, widgets: [] });
      }
      sections[sections.length - 1]!.widgets.push(w);
    }

    return sections;
  }, [resolvedWidgets]);

  return (
    <div className="space-y-8">
      {widgetsBySection.map((section) => (
        <div key={section.label}>
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
            {section.label}
          </h2>
          <div
            className="grid grid-cols-12 gap-4"
            style={{ gridAutoRows: "minmax(80px, auto)" }}
          >
            {section.widgets.map((widget) => (
              <DbWidgetCard
                key={widget.widget_id}
                widget={widget}
                rawData={widgetData.get(widget.widget_id)}
                isDataLoading={dashboardLoading}
                onRefresh={() => fetchWidgetData(widget.widget_id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ================================================================== */
/*  Health Score Ring (large)                                           */
/* ================================================================== */

function HealthScoreRing({ score }: { score: number | null }) {
  const safeScore = score ?? 0;
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (safeScore / 100) * circumference;
  const badge = getHealthScoreBadge(score);

  return (
    <div className="card flex items-center gap-6 p-6">
      <div className="relative flex-shrink-0">
        <svg width="128" height="128" viewBox="0 0 128 128">
          <circle
            cx="64"
            cy="64"
            r="54"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-slate-200 dark:text-slate-700"
          />
          <circle
            cx="64"
            cy="64"
            r="54"
            fill="none"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform="rotate(-90 64 64)"
            className={cn(
              "transition-all duration-1000 ease-out",
              safeScore >= 70
                ? "stroke-teal-500"
                : safeScore >= 40
                  ? "stroke-yellow-500"
                  : "stroke-red-500",
            )}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("text-3xl font-bold", getHealthScoreColor(safeScore))}>
            {score !== null ? safeScore : "--"}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            / 100
          </span>
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Organization Health
        </h2>
        <span
          className={cn(
            "badge mt-1",
            badge.bg,
            badge.text,
          )}
        >
          {badge.label}
        </span>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Aggregated across all active projects and team activity signals.
        </p>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  KPI Card                                                           */
/* ================================================================== */

interface KpiCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}

function KpiCard({ label, value, icon, color, subtitle }: KpiCardProps) {
  return (
    <div className="card flex items-start gap-4 p-5">
      <div
        className={cn(
          "flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl",
          color,
        )}
      >
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
          {label}
        </p>
        <p className="mt-0.5 text-2xl font-bold text-slate-900 dark:text-white">
          {value}
        </p>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Alert Banner                                                       */
/* ================================================================== */

function AlertBanner({
  alerts,
  onDismiss,
}: {
  alerts: AlertTriggered[];
  onDismiss: (id: string) => void;
}) {
  if (alerts.length === 0) return null;

  const severityStyles: Record<string, string> = {
    critical:
      "border-red-300 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300",
    warning:
      "border-yellow-300 bg-yellow-50 text-yellow-800 dark:border-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
    info: "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  };

  return (
    <div className="space-y-2">
      {alerts.slice(0, 3).map((alert) => (
        <div
          key={alert.trigger_id}
          className={cn(
            "flex items-center gap-3 rounded-lg border px-4 py-3",
            severityStyles[alert.severity] ?? severityStyles.info,
          )}
        >
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1 text-sm font-medium">{alert.message}</span>
          <span className="text-xs opacity-75">
            {formatRelativeTime(alert.triggered_at)}
          </span>
          <button
            onClick={() => onDismiss(alert.trigger_id)}
            className="flex-shrink-0 rounded-md p-1 opacity-60 transition-opacity hover:opacity-100"
            aria-label="Dismiss alert"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      ))}
      {alerts.length > 3 && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          +{alerts.length - 3} more alert{alerts.length - 3 > 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
}

/* ================================================================== */
/*  AI Briefing Panel                                                  */
/* ================================================================== */

function AiBriefingPanel({ projects }: { projects: Project[] }) {
  const activeCount = projects.filter(
    (p) => p.status !== "completed" && p.status !== "cancelled",
  ).length;
  const atRiskCount = projects.filter(
    (p) => p.status === "at_risk" || p.status === "behind",
  ).length;
  const totalPeople = useMemo(() => {
    return projects.reduce((sum, p) => sum + getTeamSize(p), 0);
  }, [projects]);

  return (
    <div className="card border-l-4 border-l-teal-500 p-5">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-teal-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          AI Briefing
        </h3>
        <span className="badge-teal ml-auto text-2xs">Auto-generated</span>
      </div>
      <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
        {projects.length === 0 ? (
          "No projects detected yet. Upload your Slack exports, Jira CSVs, or Google Drive documents to get started."
        ) : (
          <>
            You have <strong>{activeCount}</strong> active project
            {activeCount !== 1 ? "s" : ""} with{" "}
            <strong>{totalPeople}</strong> team member
            {totalPeople !== 1 ? "s" : ""} involved.
            {atRiskCount > 0 && (
              <>
                {" "}
                <span className="font-semibold text-warm-600 dark:text-warm-400">
                  {atRiskCount} project{atRiskCount !== 1 ? "s" : ""}{" "}
                  {atRiskCount !== 1 ? "need" : "needs"} attention
                </span>{" "}
                -- review the flagged items below for recommended actions.
              </>
            )}
            {atRiskCount === 0 &&
              " All projects are tracking within healthy parameters."}
          </>
        )}
      </p>
    </div>
  );
}

/* ================================================================== */
/*  Project Overview Card                                              */
/* ================================================================== */

function ProjectOverviewCard({ project }: { project: Project }) {
  const healthNum = healthToNumber(project.health_score);
  const completionPct = getCompletionPct(project);
  const teamSize = getTeamSize(project);

  const daysUntilDeadline = project.deadline
    ? Math.ceil(
        (new Date(project.deadline).getTime() - Date.now()) /
          (1000 * 60 * 60 * 24),
      )
    : null;

  return (
    <Link
      to={`/projects/${project.project_id}`}
      className="card-interactive group block space-y-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-slate-900 group-hover:text-teal-700 dark:text-white dark:group-hover:text-teal-400">
            {project.name}
          </h3>
          <p className="mt-1 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
            {project.description || "No description available"}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={cn("badge", STATUS_COLORS[project.status] ?? "badge-teal")}>
            {STATUS_LABELS[project.status] ?? project.status}
          </span>
          <span
            className={cn(
              "text-lg font-bold tabular-nums",
              getHealthScoreColor(healthNum),
            )}
          >
            {healthNum !== null ? healthNum : "--"}
          </span>
        </div>
      </div>

      {/* Completion bar */}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Completion</span>
          <span className="font-medium">
            {completionPct.toFixed(0)}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              completionPct >= 80
                ? "bg-teal-500"
                : completionPct >= 50
                  ? "bg-chief-500"
                  : "bg-warm-500",
            )}
            style={{
              width: `${Math.min(completionPct, 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <Users className="h-3.5 w-3.5" />
          {teamSize} member{teamSize !== 1 ? "s" : ""}
        </span>
        {daysUntilDeadline !== null && (
          <span
            className={cn(
              "flex items-center gap-1 font-medium",
              daysUntilDeadline < 0
                ? "text-red-600 dark:text-red-400"
                : daysUntilDeadline < 7
                  ? "text-warm-600 dark:text-warm-400"
                  : "text-slate-500 dark:text-slate-400",
            )}
          >
            <Clock className="h-3.5 w-3.5" />
            {daysUntilDeadline < 0
              ? `${Math.abs(daysUntilDeadline)}d overdue`
              : daysUntilDeadline === 0
                ? "Due today"
                : `${daysUntilDeadline}d remaining`}
          </span>
        )}
        {daysUntilDeadline === null && (
          <span className="text-slate-400">No deadline set</span>
        )}
      </div>
    </Link>
  );
}

/* ================================================================== */
/*  Team Quick Link                                                    */
/* ================================================================== */

function TeamQuickLink({ totalPeople }: { totalPeople: number }) {
  if (totalPeople === 0) return null;

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <Users className="h-4 w-4 text-teal-500" />
          Team ({totalPeople} member{totalPeople !== 1 ? "s" : ""})
        </h3>
        <Link
          to="/people"
          className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
        >
          View people directory
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Empty State                                                        */
/* ================================================================== */

function EmptyDashboard() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
        <FolderKanban className="h-10 w-10 text-teal-600 dark:text-teal-400" />
      </div>
      <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
        No projects yet
      </h2>
      <p className="mb-6 max-w-md text-sm text-slate-500 dark:text-slate-400">
        Upload your Slack exports, Jira CSVs, or Google Drive documents and
        ChiefOps will automatically discover projects, people, and status.
      </p>
      <Link to="/upload" className="btn-primary">
        Upload Data
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

/* ================================================================== */
/*  Hardcoded Fallback Dashboard (pre-ingestion)                       */
/* ================================================================== */

function FallbackDashboard() {
  const {
    projects,
    isLoading: projectsLoading,
    fetchProjects,
  } = useProjectStore();
  const {
    triggeredAlerts,
    isLoading: alertsLoading,
    fetchTriggeredAlerts,
    dismissAlert,
  } = useAlertStore();

  useEffect(() => {
    fetchProjects();
    fetchTriggeredAlerts();
  }, [fetchProjects, fetchTriggeredAlerts]);

  // Computed stats
  const activeProjects = projects.filter(
    (p) => p.status !== "completed" && p.status !== "cancelled",
  );
  const totalPeople = useMemo(
    () => projects.reduce((sum, p) => sum + getTeamSize(p), 0),
    [projects],
  );
  const openTasks = useMemo(
    () => projects.reduce((sum, p) => sum + getOpenTasks(p), 0),
    [projects],
  );
  const avgHealth = useMemo(() => {
    if (activeProjects.length === 0) return null;
    const scores = activeProjects
      .map((p) => healthToNumber(p.health_score))
      .filter((s): s is number => s !== null);
    if (scores.length === 0) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  }, [activeProjects]);

  const activeAlerts = triggeredAlerts.filter((a) => !a.acknowledged);
  const unreadCount = activeAlerts.length;
  const isLoading = projectsLoading || alertsLoading;

  return (
    <>
      {/* Loading state */}
      {isLoading && projects.length === 0 && (
        <>
          <div className="grid gap-4 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <SkeletonCard className="h-36" />
            </div>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="skeleton h-24 rounded-xl" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SkeletonProjectCard />
            <SkeletonProjectCard />
            <SkeletonProjectCard />
          </div>
        </>
      )}

      {/* Content (post-load) */}
      {!isLoading && projects.length === 0 && <EmptyDashboard />}

      {projects.length > 0 && (
        <>
          {/* Top row: Health Score + KPI cards */}
          <div className="grid gap-4 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <HealthScoreRing score={avgHealth} />
            </div>
            <KpiCard
              label="Total Projects"
              value={projects.length}
              icon={<FolderKanban className="h-5 w-5 text-chief-600 dark:text-chief-400" />}
              color="bg-chief-100 dark:bg-chief-900/40"
              subtitle={`${activeProjects.length} active`}
            />
            <KpiCard
              label="Team Members"
              value={totalPeople}
              icon={<Users className="h-5 w-5 text-teal-600 dark:text-teal-400" />}
              color="bg-teal-100 dark:bg-teal-900/40"
            />
            <KpiCard
              label="Open Tasks"
              value={openTasks}
              icon={<CheckSquare className="h-5 w-5 text-warm-600 dark:text-warm-400" />}
              color="bg-warm-100 dark:bg-warm-900/40"
              subtitle={
                unreadCount > 0
                  ? `${unreadCount} alert${unreadCount !== 1 ? "s" : ""}`
                  : undefined
              }
            />
          </div>

          {/* Alert banner */}
          <AlertBanner
            alerts={activeAlerts}
            onDismiss={(id) => dismissAlert(id)}
          />

          {/* AI Briefing panel */}
          <AiBriefingPanel projects={projects} />

          {/* Project overview cards grid */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
                <TrendingUp className="h-5 w-5 text-teal-500" />
                Project Overview
              </h2>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {activeProjects.length} active project
                {activeProjects.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <ProjectOverviewCard key={project.project_id} project={project} />
              ))}
            </div>
          </div>

          {/* Team quick link */}
          <TeamQuickLink totalPeople={totalPeople} />
        </>
      )}
    </>
  );
}

/* ================================================================== */
/*  Main Dashboard Page                                                */
/* ================================================================== */

export function MainDashboard() {
  const { fetchDefaultDashboard, activeDashboard, isLoading: dashLoading } =
    useDashboardStore();
  const [hasDefaultDashboard, setHasDefaultDashboard] = useState<
    boolean | null
  >(null);

  const loadDefault = useCallback(async () => {
    const found = await fetchDefaultDashboard();
    setHasDefaultDashboard(found);
  }, [fetchDefaultDashboard]);

  useEffect(() => {
    loadDefault();
  }, [loadDefault]);

  // While checking for default dashboard, show loading
  const isChecking = hasDefaultDashboard === null && dashLoading;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <LayoutDashboard className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {hasDefaultDashboard ? "COO Command Center" : "Dashboard"}
        </h1>
        {hasDefaultDashboard && activeDashboard && (
          <span className="badge-teal text-2xs">
            {activeDashboard.widget_ids.length} widgets
          </span>
        )}
      </div>

      {/* Loading indicator while checking for default dashboard */}
      {isChecking && (
        <>
          <div className="grid gap-4 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <SkeletonCard className="h-36" />
            </div>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="skeleton h-24 rounded-xl" />
        </>
      )}

      {/* DB-backed default dashboard */}
      {hasDefaultDashboard === true && <DefaultDashboardView />}

      {/* Hardcoded fallback */}
      {hasDefaultDashboard === false && <FallbackDashboard />}
    </div>
  );
}
