import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Loader2,
  TrendingUp,
  Users,
  XCircle,
  Activity,
  Shield,
  ChevronRight,
  Zap,
  CalendarClock,
  ArrowUpRight,
  RefreshCw,
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
    isExporting,
    isStuck,
    error,
    startPolling,
    regenerateBriefing,
    exportBriefingPdf,
    reset,
  } = useCooBriefingStore();

  const [regenerating, setRegenerating] = useState(false);
  const [exportStatus, setExportStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  useEffect(() => {
    startPolling(projectId);
    return () => {
      reset();
    };
  }, [projectId, startPolling, reset]);

  const handleRegenerate = useCallback(async () => {
    setRegenerating(true);
    await regenerateBriefing(projectId);
    // polling restarts inside regenerateBriefing, regenerating state
    // clears when the briefing status changes from processing
    setTimeout(() => setRegenerating(false), 2000);
  }, [projectId, regenerateBriefing]);

  const handleExportPdf = useCallback(async () => {
    if (exportStatus === "loading") return;
    setExportStatus("loading");
    try {
      await exportBriefingPdf(projectId);
      setExportStatus("success");
      setTimeout(() => setExportStatus("idle"), 2500);
    } catch {
      setExportStatus("error");
      setTimeout(() => setExportStatus("idle"), 3000);
    }
  }, [projectId, exportBriefingPdf, exportStatus]);

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

  // Stuck — polling timed out without completing
  if (isStuck) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
          <Clock className="h-6 w-6 text-amber-500" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          Briefing Generation Stalled
        </h3>
        <p className="mb-4 max-w-sm text-sm text-slate-500 dark:text-slate-400">
          The briefing has been processing for longer than expected. You can retry
          to generate a new briefing from the existing file summaries.
        </p>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700 disabled:opacity-50"
        >
          <RefreshCw className={cn("h-4 w-4", regenerating && "animate-spin")} />
          {regenerating ? "Retrying..." : "Retry Briefing"}
        </button>
      </div>
    );
  }

  // Error state with no briefing
  if (error && !briefing) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <AlertTriangle className="h-6 w-6 text-red-500" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          Briefing Error
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">{error}</p>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="mt-4 flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700 disabled:opacity-50"
        >
          <RefreshCw className={cn("h-4 w-4", regenerating && "animate-spin")} />
          {regenerating ? "Retrying..." : "Retry Briefing"}
        </button>
      </div>
    );
  }

  // Briefing failed but we have summaries
  if (briefing?.status === "failed" && fileSummaries.length > 0) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Briefing aggregation failed: {briefing.error_message ?? "Unknown error"}.
                Showing individual file summaries below.
              </p>
            </div>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-700 shadow-sm transition-colors hover:bg-amber-50 disabled:opacity-50 dark:border-amber-700 dark:bg-amber-900/40 dark:text-amber-300 dark:hover:bg-amber-900/60"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", regenerating && "animate-spin")} />
              {regenerating ? "Retrying..." : "Retry"}
            </button>
          </div>
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
        {/* Executive Summary — hero card */}
        <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-gradient-to-br from-white via-white to-teal-50/50 p-6 shadow-soft dark:border-slate-700 dark:from-surface-dark-card dark:via-surface-dark-card dark:to-teal-950/20">
          <div className="absolute right-0 top-0 h-32 w-32 opacity-5">
            <Shield className="h-full w-full text-teal-600" />
          </div>
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-teal-600 shadow-sm">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="mb-1 text-base font-bold text-slate-900 dark:text-white">
                Executive Summary
              </h3>
              <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                {b.executive_summary}
              </p>
            </div>
          </div>
          {/* Timestamp + Actions */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-2xs text-slate-400">
              <CalendarClock className="h-3 w-3" />
              Generated {new Date(briefing.updated_at).toLocaleString()}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExportPdf}
                disabled={exportStatus === "loading" || isExporting}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-all hover:border-teal-300 hover:text-teal-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-teal-600 dark:hover:text-teal-400"
              >
                {exportStatus === "loading" || isExporting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Exporting...
                  </>
                ) : exportStatus === "success" ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                    Downloaded
                  </>
                ) : exportStatus === "error" ? (
                  <>
                    <XCircle className="h-3.5 w-3.5 text-red-500" />
                    Failed
                  </>
                ) : (
                  <>
                    <Download className="h-3.5 w-3.5" />
                    Download PDF
                  </>
                )}
              </button>
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-all hover:border-teal-300 hover:text-teal-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-teal-600 dark:hover:text-teal-400"
              >
                <RefreshCw className={cn("h-3.5 w-3.5", regenerating && "animate-spin")} />
                {regenerating ? "Regenerating..." : "Regenerate"}
              </button>
            </div>
          </div>
        </div>

        {/* Needs Attention — highest priority */}
        {b.attention_items && b.attention_items.length > 0 && (
          <AttentionSection items={b.attention_items} />
        )}

        {/* Health + Capacity side by side */}
        <div className="grid gap-6 lg:grid-cols-2">
          {b.project_health && (
            <HealthSection health={b.project_health} />
          )}
          {b.team_capacity && b.team_capacity.length > 0 && (
            <TeamCapacitySection items={b.team_capacity} />
          )}
        </div>

        {/* Deadlines + Recent Changes */}
        {b.upcoming_deadlines && b.upcoming_deadlines.length > 0 && (
          <DeadlinesSection items={b.upcoming_deadlines} />
        )}

        {b.recent_changes && b.recent_changes.length > 0 && (
          <RecentChangesSection items={b.recent_changes} />
        )}

        {/* Collapsible file summaries */}
        {fileSummaries.length > 0 && (
          <details className="group">
            <summary className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300">
              <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" />
              View {fileSummaries.length} source file{" "}
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
      <div className="card p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 dark:bg-teal-900/40">
            <Loader2 className="h-5 w-5 animate-spin text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Generating COO Briefing
            </h3>
            <p className="text-2xs text-slate-500 dark:text-slate-400">
              Analyzing {total} file{total !== 1 ? "s" : ""} with AI...
            </p>
          </div>
        </div>

        <div className="mb-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>
            {done} of {total} file{total !== 1 ? "s" : ""} summarized
            {failed > 0 && (
              <span className="ml-1 text-red-500">({failed} failed)</span>
            )}
          </span>
          <span className="font-semibold text-teal-600 dark:text-teal-400">{pct}%</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
          <div
            className="h-full rounded-full bg-gradient-to-r from-teal-400 to-teal-600 transition-all duration-700 ease-out"
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>

        {status?.briefing_status === "processing" && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-teal-50 px-3 py-2 dark:bg-teal-900/20">
            <Activity className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
            <p className="text-xs font-medium text-teal-700 dark:text-teal-300">
              Aggregating summaries into COO briefing...
            </p>
          </div>
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
/*  Attention section                                                  */
/* ================================================================== */

function AttentionSection({ items }: { items: AttentionItem[] }) {
  const config: Record<string, {
    border: string;
    bg: string;
    icon: string;
    label: string;
    labelBg: string;
  }> = {
    red: {
      border: "border-red-200 dark:border-red-800/60",
      bg: "bg-red-50/80 dark:bg-red-950/30",
      icon: "text-red-500 dark:text-red-400",
      label: "CRITICAL",
      labelBg: "bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300",
    },
    amber: {
      border: "border-amber-200 dark:border-amber-800/60",
      bg: "bg-amber-50/80 dark:bg-amber-950/30",
      icon: "text-amber-500 dark:text-amber-400",
      label: "WARNING",
      labelBg: "bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300",
    },
    green: {
      border: "border-slate-200 dark:border-slate-700",
      bg: "bg-slate-50/50 dark:bg-slate-800/30",
      icon: "text-slate-400",
      label: "INFO",
      labelBg: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    },
  };

  const redCount = items.filter((i) => i.severity === "red").length;
  const amberCount = items.filter((i) => i.severity === "amber").length;

  return (
    <div className="card overflow-hidden p-0">
      {/* Header with count badges */}
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-700">
        <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <AlertTriangle className="h-4 w-4 text-warm-500" />
          Needs Attention
        </h3>
        <div className="flex items-center gap-2">
          {redCount > 0 && (
            <span className="badge bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400">
              {redCount} critical
            </span>
          )}
          {amberCount > 0 && (
            <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
              {amberCount} warning{amberCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Items */}
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {items.map((item, i) => {
          const c = config[item.severity] ?? config.green!;
          return (
            <div
              key={i}
              className={cn(
                "flex gap-3 px-5 py-4 transition-colors",
                c?.bg,
              )}
            >
              <div className="flex flex-shrink-0 pt-0.5">
                <AlertTriangle className={cn("h-4 w-4", c?.icon)} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">
                    {item.title}
                  </p>
                  <span className={cn("badge text-2xs font-bold uppercase tracking-wide", c?.labelBg)}>
                    {c?.label}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  {item.details}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Health section                                                     */
/* ================================================================== */

function HealthSection({
  health,
}: {
  health: { status: string; score: number; rationale: string };
}) {
  const statusConfig: Record<string, {
    gradient: string;
    text: string;
    badgeBg: string;
    label: string;
    ring: string;
  }> = {
    green: {
      gradient: "from-green-500 to-emerald-600",
      text: "text-green-600 dark:text-green-400",
      badgeBg: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
      label: "Healthy",
      ring: "ring-green-200 dark:ring-green-800",
    },
    yellow: {
      gradient: "from-yellow-500 to-amber-600",
      text: "text-yellow-600 dark:text-yellow-400",
      badgeBg: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
      label: "At Risk",
      ring: "ring-yellow-200 dark:ring-yellow-800",
    },
    red: {
      gradient: "from-red-500 to-rose-600",
      text: "text-red-600 dark:text-red-400",
      badgeBg: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
      label: "Critical",
      ring: "ring-red-200 dark:ring-red-800",
    },
  };

  const greenDefault = statusConfig.green;
  const c = statusConfig[health.status] ?? greenDefault;

  return (
    <div className="card space-y-4 p-5">
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
        <TrendingUp className="h-4 w-4 text-teal-500" />
        Project Health
      </h3>

      <div className="flex items-center gap-4">
        {/* Score circle */}
        <div className={cn("flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full ring-4", c?.ring)}>
          <div className={cn("flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br text-white", c?.gradient)}>
            <span className="text-xl font-extrabold tabular-nums">{health.score}</span>
          </div>
        </div>
        <div>
          <span className={cn("badge text-xs font-bold uppercase", c?.badgeBg)}>
            {c?.label}
          </span>
          <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
            out of 100
          </p>
        </div>
      </div>

      <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400">
        {health.rationale}
      </p>
    </div>
  );
}

/* ================================================================== */
/*  Team capacity section                                              */
/* ================================================================== */

function TeamCapacitySection({ items }: { items: TeamCapacityItem[] }) {
  const badgeConfig: Record<string, { bg: string; icon: React.ReactNode }> = {
    overloaded: {
      bg: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
      icon: <AlertTriangle className="h-3 w-3" />,
    },
    balanced: {
      bg: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
      icon: <CheckCircle2 className="h-3 w-3" />,
    },
    underutilized: {
      bg: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
      icon: <ArrowUpRight className="h-3 w-3" />,
    },
  };

  return (
    <div className="card space-y-4 p-5">
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
        <Users className="h-4 w-4 text-teal-500" />
        Team Capacity
        <span className="badge-neutral ml-auto text-2xs">{items.length} people</span>
      </h3>
      <div className="space-y-2">
        {items.map((item, i) => {
          const c = badgeConfig[item.status] ?? badgeConfig.balanced!;
          return (
            <div
              key={i}
              className="rounded-lg border border-slate-100 bg-slate-50/50 px-3.5 py-2.5 dark:border-slate-800 dark:bg-slate-800/30"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {item.person}
                </p>
                <span className={cn("badge text-2xs font-bold uppercase", c?.bg)}>
                  {c?.icon}
                  {item.status}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {item.details}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Deadlines section                                                  */
/* ================================================================== */

function DeadlinesSection({ items }: { items: DeadlineItem[] }) {
  const statusConfig: Record<string, {
    icon: React.ReactNode;
    badgeBg: string;
    label: string;
    border: string;
  }> = {
    on_track: {
      icon: <CheckCircle2 className="h-4 w-4 text-green-500" />,
      badgeBg: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
      label: "on track",
      border: "border-l-green-400",
    },
    at_risk: {
      icon: <Clock className="h-4 w-4 text-yellow-500" />,
      badgeBg: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
      label: "at risk",
      border: "border-l-yellow-400",
    },
    overdue: {
      icon: <XCircle className="h-4 w-4 text-red-500" />,
      badgeBg: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
      label: "overdue",
      border: "border-l-red-400",
    },
  };

  const atRiskCount = items.filter((i) => i.status === "at_risk" || i.status === "overdue").length;

  return (
    <div className="card overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-700">
        <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <CalendarClock className="h-4 w-4 text-teal-500" />
          Upcoming Deadlines
        </h3>
        {atRiskCount > 0 && (
          <span className="badge bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400">
            {atRiskCount} at risk
          </span>
        )}
      </div>
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {items.map((item, i) => {
          const c = statusConfig[item.status] ?? statusConfig.on_track!;
          return (
            <div
              key={i}
              className={cn(
                "flex items-center gap-3 border-l-4 px-5 py-3.5",
                c?.border,
              )}
            >
              {c?.icon}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {item.item}
                </p>
                <p className="text-2xs text-slate-500 dark:text-slate-400">
                  {item.date}
                </p>
              </div>
              <span className={cn("badge text-2xs font-semibold uppercase", c?.badgeBg)}>
                {c?.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Recent changes section                                             */
/* ================================================================== */

function RecentChangesSection({ items }: { items: RecentChangeItem[] }) {
  return (
    <div className="card overflow-hidden p-0">
      <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-700">
        <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <Activity className="h-4 w-4 text-teal-500" />
          Recent Changes
        </h3>
      </div>
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {items.map((item, i) => (
          <div key={i} className="px-5 py-3.5">
            <div className="flex items-start gap-3">
              <div className="mt-1 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-teal-100 dark:bg-teal-900/40">
                <ChevronRight className="h-3 w-3 text-teal-600 dark:text-teal-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {item.change}
                </p>
                <p className="mt-1 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                  <ArrowUpRight className="h-3 w-3 flex-shrink-0 text-teal-500" />
                  {item.impact}
                </p>
              </div>
            </div>
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
            <span className="badge-neutral text-2xs">{s.file_type}</span>
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
