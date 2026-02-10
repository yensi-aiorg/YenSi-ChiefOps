import { useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  TrendingUp,
  Users,
  XCircle,
  Activity,
} from "lucide-react";
import { useCooBriefingStore } from "@/stores/cooBriefingStore";
import { cn } from "@/lib/utils";
import type {
  AttentionItem,
  COOBriefingStatus,
  TeamCapacityItem,
  DeadlineItem,
  RecentChangeItem,
  FileSummaryInfo,
} from "@/types";

/* ================================================================== */
/*  COO Briefing Tab                                                   */
/* ================================================================== */

export function COOBriefingTab({ projectId }: { projectId: string }) {
  const {
    briefing,
    status,
    fileSummaries,
    isLoading,
    error,
    startPolling,
    reset,
  } = useCooBriefingStore();

  useEffect(() => {
    startPolling(projectId);
    return () => {
      reset();
    };
  }, [projectId, startPolling, reset]);

  // Idle — no pipeline has run
  if (
    !isLoading &&
    status?.pipeline_status === "idle" &&
    !briefing
  ) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
          <FileText className="h-8 w-8 text-teal-600 dark:text-teal-400" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          No COO Briefing Yet
        </h3>
        <p className="max-w-sm text-sm text-slate-500 dark:text-slate-400">
          Upload files to this project and a COO briefing will be automatically
          generated from the uploaded content.
        </p>
      </div>
    );
  }

  // Processing — show progress
  if (
    status?.pipeline_status === "processing" ||
    isLoading
  ) {
    return <ProcessingView status={status} fileSummaries={fileSummaries} />;
  }

  // Error state with no briefing
  if (error && !briefing) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertTriangle className="mb-4 h-12 w-12 text-red-400" />
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          Briefing Error
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">{error}</p>
      </div>
    );
  }

  // Briefing failed but we have summaries
  if (briefing?.status === "failed" && fileSummaries.length > 0) {
    return (
      <div className="space-y-6">
        <div className="card border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <p className="text-sm text-amber-800 dark:text-amber-300">
            Briefing aggregation failed: {briefing.error_message ?? "Unknown error"}.
            Showing individual file summaries below.
          </p>
        </div>
        <FileSummariesFallback summaries={fileSummaries} />
      </div>
    );
  }

  // Success — render the briefing
  if (briefing?.status === "completed" && briefing.briefing) {
    const b = briefing.briefing;
    return (
      <div className="space-y-6">
        {/* Executive Summary */}
        <div className="card p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <FileText className="h-4 w-4 text-teal-500" />
            Executive Summary
          </h3>
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {b.executive_summary}
          </p>
        </div>

        {/* Needs Attention */}
        {b.attention_items.length > 0 && (
          <AttentionSection items={b.attention_items} />
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Project Health */}
          {b.project_health && (
            <HealthSection health={b.project_health} />
          )}

          {/* Team Capacity */}
          {b.team_capacity.length > 0 && (
            <TeamCapacitySection items={b.team_capacity} />
          )}
        </div>

        {/* Upcoming Deadlines */}
        {b.upcoming_deadlines.length > 0 && (
          <DeadlinesSection items={b.upcoming_deadlines} />
        )}

        {/* Recent Changes */}
        {b.recent_changes.length > 0 && (
          <RecentChangesSection items={b.recent_changes} />
        )}

        {/* Collapsible file summaries */}
        {fileSummaries.length > 0 && (
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300">
              View {fileSummaries.length} file{" "}
              {fileSummaries.length === 1 ? "summary" : "summaries"}
            </summary>
            <div className="mt-4">
              <FileSummariesFallback summaries={fileSummaries} />
            </div>
          </details>
        )}
      </div>
    );
  }

  // Fallback: nothing to show
  return null;
}

/* ================================================================== */
/*  Processing progress view                                           */
/* ================================================================== */

function ProcessingView({
  status,
  fileSummaries,
}: {
  status: COOBriefingStatus | null;
  fileSummaries: FileSummaryInfo[];
}) {
  const total = status?.summaries_total ?? 0;
  const completed = status?.summaries_completed ?? 0;
  const failed = status?.summaries_failed ?? 0;
  const done = completed + failed;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="mb-4 flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-teal-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            Generating COO Briefing...
          </h3>
        </div>

        <div className="mb-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>
            {done} of {total} file{total !== 1 ? "s" : ""} summarized
            {failed > 0 && ` (${failed} failed)`}
          </span>
          <span className="font-medium">{pct}%</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className="h-full rounded-full bg-teal-500 transition-all duration-500"
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>

        {status?.briefing_status === "processing" && (
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Aggregating summaries into COO briefing...
          </p>
        )}
      </div>

      {/* Show completed summaries as they come in */}
      {fileSummaries.filter((s) => s.status === "completed").length > 0 && (
        <FileSummariesFallback
          summaries={fileSummaries.filter((s) => s.status === "completed")}
        />
      )}
    </div>
  );
}

/* ================================================================== */
/*  Section components                                                 */
/* ================================================================== */

function AttentionSection({ items }: { items: AttentionItem[] }) {
  const colorMap: Record<string, string> = {
    red: "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
    amber: "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20",
    green: "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50",
  };
  const iconMap: Record<string, string> = {
    red: "text-red-500",
    amber: "text-amber-500",
    green: "text-slate-400",
  };

  return (
    <div className="card space-y-3 p-5">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <AlertTriangle className="h-4 w-4 text-warm-500" />
        Needs Attention
      </h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div
            key={i}
            className={cn(
              "rounded-lg border p-3",
              colorMap[item.severity] ?? colorMap.green,
            )}
          >
            <div className="flex items-start gap-2">
              <AlertTriangle
                className={cn(
                  "mt-0.5 h-4 w-4 flex-shrink-0",
                  iconMap[item.severity] ?? iconMap.green,
                )}
              />
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  {item.title}
                </p>
                <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
                  {item.details}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function HealthSection({
  health,
}: {
  health: { status: string; score: number; rationale: string };
}) {
  const colorMap: Record<string, string> = {
    green: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
    yellow: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
    red: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  };
  const scoreColor =
    health.score >= 70
      ? "text-green-600 dark:text-green-400"
      : health.score >= 40
        ? "text-yellow-600 dark:text-yellow-400"
        : "text-red-600 dark:text-red-400";

  return (
    <div className="card space-y-3 p-5">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <TrendingUp className="h-4 w-4 text-teal-500" />
        Project Health
      </h3>
      <div className="flex items-center gap-4">
        <span
          className={cn(
            "badge text-xs font-semibold uppercase",
            colorMap[health.status] ?? colorMap.green,
          )}
        >
          {health.status}
        </span>
        <span className={cn("text-2xl font-bold tabular-nums", scoreColor)}>
          {health.score}
        </span>
        <span className="text-xs text-slate-400">/100</span>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {health.rationale}
      </p>
    </div>
  );
}

function TeamCapacitySection({ items }: { items: TeamCapacityItem[] }) {
  const badgeColor: Record<string, string> = {
    overloaded: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
    balanced: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
    underutilized: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  };

  return (
    <div className="card space-y-3 p-5">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <Users className="h-4 w-4 text-teal-500" />
        Team Capacity
      </h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {item.person}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {item.details}
              </p>
            </div>
            <span
              className={cn(
                "badge ml-2 text-2xs flex-shrink-0",
                badgeColor[item.status] ?? badgeColor.balanced,
              )}
            >
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DeadlinesSection({ items }: { items: DeadlineItem[] }) {
  const statusIcon = (s: string) => {
    if (s === "on_track") return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    if (s === "at_risk") return <Clock className="h-4 w-4 text-yellow-500" />;
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  return (
    <div className="card space-y-3 p-5">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <Clock className="h-4 w-4 text-teal-500" />
        Upcoming Deadlines
      </h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div
            key={i}
            className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2.5 dark:border-slate-700"
          >
            {statusIcon(item.status)}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {item.item}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {item.date}
              </p>
            </div>
            <span
              className={cn(
                "badge text-2xs",
                item.status === "on_track"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
                  : item.status === "at_risk"
                    ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400"
                    : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
              )}
            >
              {item.status.replace("_", " ")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentChangesSection({ items }: { items: RecentChangeItem[] }) {
  return (
    <div className="card space-y-3 p-5">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <Activity className="h-4 w-4 text-teal-500" />
        Recent Changes
      </h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div
            key={i}
            className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50"
          >
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {item.change}
            </p>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Impact: {item.impact}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  File summaries fallback                                            */
/* ================================================================== */

function FileSummariesFallback({
  summaries,
}: {
  summaries: FileSummaryInfo[];
}) {
  return (
    <div className="space-y-3">
      {summaries.map((s) => (
        <div key={s.summary_id} className="card p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {s.filename}
              </span>
            </div>
            <span className="text-2xs text-slate-400">{s.file_type}</span>
          </div>
          {s.summary_markdown ? (
            <div className="prose prose-sm dark:prose-invert max-w-none text-slate-600 dark:text-slate-400">
              <pre className="whitespace-pre-wrap text-xs">{s.summary_markdown}</pre>
            </div>
          ) : s.error_message ? (
            <p className="text-xs text-red-500">{s.error_message}</p>
          ) : (
            <p className="text-xs text-slate-400">Processing...</p>
          )}
        </div>
      ))}
    </div>
  );
}
