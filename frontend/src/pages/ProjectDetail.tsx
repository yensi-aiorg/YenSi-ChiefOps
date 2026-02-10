import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FolderKanban,
  Clock,
  Users,
  AlertTriangle,
  TrendingUp,
  Target,
  Zap,
  ArrowLeft,
  Loader2,
  ShieldCheck,
  HelpCircle,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Minus,
  BarChart3,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useChatStore } from "@/stores/chatStore";
import { ProjectFilesTab } from "@/components/project/ProjectFilesTab";
import { COOBriefingTab } from "@/components/project/COOBriefingTab";
import { cn } from "@/lib/utils";
import {
  formatDate,
  formatRelativeTime,
  getHealthScoreColor,
  getInitials,
} from "@/lib/utils";
import type { Project } from "@/types";

/* ================================================================== */
/*  Adapter helpers (bridge backend ProjectDetail → frontend Project)  */
/* ================================================================== */

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

type AnyProject = Record<string, unknown>;

function getCompletionPct(p: AnyProject): number {
  if (typeof p.completion_percentage === "number") return p.completion_percentage;
  const total = typeof p.total_tasks === "number" ? p.total_tasks : 0;
  const completed = typeof p.completed_tasks === "number" ? p.completed_tasks : 0;
  return total > 0 ? Math.round((completed / total) * 100) : 0;
}

function getTaskCounts(p: AnyProject): {
  total: number;
  completed: number;
  in_progress: number;
  blocked: number;
  to_do: number;
} {
  if (p.task_summary && typeof p.task_summary === "object") {
    const ts = p.task_summary as Record<string, number>;
    return {
      total: ts.total ?? 0,
      completed: ts.completed ?? 0,
      in_progress: ts.in_progress ?? 0,
      blocked: ts.blocked ?? 0,
      to_do: ts.to_do ?? 0,
    };
  }
  const total = typeof p.total_tasks === "number" ? p.total_tasks : 0;
  const completed = typeof p.completed_tasks === "number" ? p.completed_tasks : 0;
  const open = typeof p.open_tasks === "number" ? p.open_tasks : 0;
  return { total, completed, in_progress: 0, blocked: 0, to_do: open };
}

function getTeamMembers(
  p: AnyProject,
): { person_id: string; name: string; role: string }[] {
  if (
    Array.isArray(p.people_involved) &&
    p.people_involved.length > 0 &&
    typeof p.people_involved[0] === "object"
  ) {
    return p.people_involved;
  }
  if (Array.isArray(p.team_members)) {
    return (p.team_members as string[]).map((id) => ({
      person_id: id,
      name: id,
      role: "",
    }));
  }
  return [];
}

function getLastAnalyzed(p: AnyProject): string | null {
  return (p.last_analyzed_at ?? p.last_analysis_at ?? null) as string | null;
}

/* ================================================================== */
/*  Status badge                                                       */
/* ================================================================== */

const statusColors: Record<string, string> = {
  on_track: "badge-teal",
  at_risk: "badge-warm",
  behind: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  completed: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  active: "badge-teal",
  on_hold: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
  cancelled: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

const statusLabels: Record<string, string> = {
  on_track: "On Track",
  at_risk: "At Risk",
  behind: "Behind",
  completed: "Completed",
  active: "Active",
  on_hold: "On Hold",
  cancelled: "Cancelled",
};

/* ================================================================== */
/*  Health Score Ring (compact)                                         */
/* ================================================================== */

function HealthScoreCompact({ score }: { score: number | null }) {
  const circumference = 2 * Math.PI * 20;
  const safeScore = score ?? 0;
  const offset = circumference - (safeScore / 100) * circumference;

  if (score === null) {
    return (
      <div className="relative inline-flex">
        <svg width="52" height="52" viewBox="0 0 52 52">
          <circle
            cx="26"
            cy="26"
            r="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            className="text-slate-200 dark:text-slate-700"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-slate-400">
          --
        </span>
      </div>
    );
  }

  return (
    <div className="relative inline-flex">
      <svg width="52" height="52" viewBox="0 0 52 52">
        <circle
          cx="26"
          cy="26"
          r="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-slate-200 dark:text-slate-700"
        />
        <circle
          cx="26"
          cy="26"
          r="20"
          fill="none"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 26 26)"
          className={cn(
            "transition-all duration-700",
            safeScore >= 70
              ? "stroke-teal-500"
              : safeScore >= 40
                ? "stroke-yellow-500"
                : "stroke-red-500",
          )}
        />
      </svg>
      <span
        className={cn(
          "absolute inset-0 flex items-center justify-center text-sm font-bold",
          getHealthScoreColor(safeScore),
        )}
      >
        {safeScore}
      </span>
    </div>
  );
}

/* ================================================================== */
/*  Deadline countdown                                                 */
/* ================================================================== */

function DeadlineCountdown({ deadline }: { deadline: string | null }) {
  if (!deadline) {
    return (
      <span className="text-sm text-slate-400 dark:text-slate-500">
        No deadline set
      </span>
    );
  }

  const days = Math.ceil(
    (new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
  );

  return (
    <div className="flex items-center gap-2">
      <Clock className="h-4 w-4 text-slate-400" />
      <span
        className={cn(
          "text-sm font-medium",
          days < 0
            ? "text-red-600 dark:text-red-400"
            : days < 7
              ? "text-warm-600 dark:text-warm-400"
              : "text-slate-600 dark:text-slate-400",
        )}
      >
        {days < 0
          ? `${Math.abs(days)} days overdue`
          : days === 0
            ? "Due today"
            : `${days} days remaining`}
      </span>
      <span className="text-xs text-slate-400 dark:text-slate-500">
        ({formatDate(deadline)})
      </span>
    </div>
  );
}

/* ================================================================== */
/*  Sprint Health Section                                              */
/* ================================================================== */

function SprintHealthSection({ project }: { project: Project }) {
  const sh = project.sprint_health;

  return (
    <div className="card space-y-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <TrendingUp className="h-4 w-4 text-teal-500" />
        Sprint Health
      </h3>

      {sh ? (
        <>
          {/* Completion bar */}
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
              <span>Sprint Completion</span>
              <span className="font-medium">
                {(sh.completion_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  sh.completion_rate >= 0.8
                    ? "bg-teal-500"
                    : sh.completion_rate >= 0.5
                      ? "bg-chief-500"
                      : "bg-warm-500",
                )}
                style={{
                  width: `${Math.min(sh.completion_rate * 100, 100)}%`,
                }}
              />
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Velocity
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-700 dark:text-slate-300">
                {sh.velocity_trend}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Blockers
              </p>
              <p
                className={cn(
                  "mt-0.5 text-sm font-semibold",
                  sh.blocker_count > 0
                    ? "text-red-600 dark:text-red-400"
                    : "text-green-600 dark:text-green-400",
                )}
              >
                {sh.blocker_count}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Score
              </p>
              <p
                className={cn(
                  "mt-0.5 text-sm font-semibold",
                  getHealthScoreColor(sh.score),
                )}
              >
                {sh.score}
              </p>
            </div>
          </div>

          {/* Task breakdown */}
          {(() => {
            const tc = getTaskCounts(project as unknown as AnyProject);
            return (
              <div className="grid grid-cols-5 gap-2 text-center">
                {(
                  [
                    ["Total", tc.total, "text-slate-700 dark:text-slate-300"],
                    ["Done", tc.completed, "text-green-600 dark:text-green-400"],
                    ["In Progress", tc.in_progress, "text-chief-600 dark:text-chief-400"],
                    ["Blocked", tc.blocked, "text-red-600 dark:text-red-400"],
                    ["To Do", tc.to_do, "text-slate-500 dark:text-slate-400"],
                  ] as [string, number, string][]
                ).map(([label, count, color]) => (
                  <div key={label}>
                    <p className="text-2xs text-slate-400">{label}</p>
                    <p className={cn("text-lg font-bold tabular-nums", color)}>
                      {count}
                    </p>
                  </div>
                ))}
              </div>
            );
          })()}
        </>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No sprint health data available. Trigger an analysis to generate
          sprint metrics.
        </p>
      )}
    </div>
  );
}

/* ================================================================== */
/*  People Section                                                     */
/* ================================================================== */

function PeopleSection({
  members,
}: {
  members: { person_id: string; name: string; role: string }[];
}) {
  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <Users className="h-4 w-4 text-teal-500" />
          Team Members
        </h3>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {members.length} member{members.length !== 1 ? "s" : ""}
        </span>
      </div>

      {members.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No team members identified yet.
        </p>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {members.map((member) => (
            <Link
              key={member.person_id}
              to={`/people/${member.person_id}`}
              className="flex items-center gap-3 rounded-lg bg-slate-50 p-3 transition-colors hover:bg-slate-100 dark:bg-slate-800/50 dark:hover:bg-slate-800"
            >
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-chief-500 text-xs font-bold text-white">
                {getInitials(member.name)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-300">
                  {member.name}
                </p>
                {member.role && (
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {member.role}
                  </p>
                )}
              </div>
              <ChevronRight className="h-4 w-4 flex-shrink-0 text-slate-300 dark:text-slate-600" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/* ================================================================== */
/*  Gap Analysis Section                                               */
/* ================================================================== */

function GapAnalysisSection({ project }: { project: Project }) {
  const gap = project.gap_analysis;

  if (!gap) {
    return (
      <div className="card">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <Target className="h-4 w-4 text-teal-500" />
          Gap Analysis
        </h3>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          No gap analysis available. Run a project analysis to identify missing
          tasks and prerequisites.
        </p>
      </div>
    );
  }

  const severityColor = (priority: string) => {
    const p = priority.toLowerCase();
    if (p === "critical" || p === "high")
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400";
    if (p === "medium")
      return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400";
    return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
  };

  return (
    <div className="card space-y-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <Target className="h-4 w-4 text-teal-500" />
        Gap Analysis
      </h3>

      {/* Missing tasks */}
      {gap.missing_tasks.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Missing Tasks
          </p>
          <div className="space-y-1.5">
            {gap.missing_tasks.map((task, i) => (
              <div
                key={i}
                className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 dark:bg-red-900/20"
              >
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red-500" />
                <span className="text-sm text-red-800 dark:text-red-300">
                  {task}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Backward plan timeline */}
      {gap.backward_plan.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Backward Plan
          </p>
          <div className="space-y-2">
            {gap.backward_plan.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2.5 dark:border-slate-700"
              >
                <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                  {i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {item.task}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    ~{item.estimated_days} day{item.estimated_days !== 1 ? "s" : ""}
                    {item.depends_on.length > 0 &&
                      ` | Depends on: ${item.depends_on.join(", ")}`}
                  </p>
                </div>
                <span className={cn("badge text-2xs", severityColor(item.priority))}>
                  {item.priority}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {gap.missing_tasks.length === 0 && gap.backward_plan.length === 0 && (
        <p className="text-sm text-green-600 dark:text-green-400">
          No gaps detected. Project planning appears comprehensive.
        </p>
      )}
    </div>
  );
}

/* ================================================================== */
/*  Technical Advisor Panel                                            */
/* ================================================================== */

function TechnicalAdvisorPanel({ project }: { project: Project }) {
  const tf = project.technical_feasibility;

  if (!tf) {
    return (
      <div className="card">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <ShieldCheck className="h-4 w-4 text-teal-500" />
          Technical Advisor
        </h3>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          No technical feasibility assessment available. Run a project analysis
          to generate technical insights.
        </p>
      </div>
    );
  }

  const readinessIcon = (status: string) => {
    const s = status.toLowerCase();
    if (s === "ready" || s === "green")
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    if (s === "warning" || s === "yellow" || s === "partial")
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    if (s === "blocked" || s === "red")
      return <XCircle className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-slate-400" />;
  };

  return (
    <div className="card space-y-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
        <ShieldCheck className="h-4 w-4 text-teal-500" />
        Technical Advisor
      </h3>

      {/* Readiness items */}
      {tf.readiness_items.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Readiness
          </p>
          <div className="space-y-2">
            {tf.readiness_items.map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50"
              >
                {readinessIcon(item.status)}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {item.area}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {item.details}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk items */}
      {tf.risk_items.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Risks
          </p>
          <div className="space-y-2">
            {tf.risk_items.map((item, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {item.risk}
                  </p>
                  <span
                    className={cn(
                      "badge text-2xs",
                      item.severity.toLowerCase() === "high" || item.severity.toLowerCase() === "critical"
                        ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
                        : item.severity.toLowerCase() === "medium"
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400"
                          : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
                    )}
                  >
                    {item.severity}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Mitigation: {item.mitigation}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Architect questions */}
      {tf.architect_questions.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Open Questions
          </p>
          <div className="space-y-1.5">
            {tf.architect_questions.map((q, i) => (
              <div
                key={i}
                className="flex items-start gap-2 rounded-lg bg-chief-50 px-3 py-2 dark:bg-chief-900/20"
              >
                <HelpCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-chief-500" />
                <span className="text-sm text-chief-800 dark:text-chief-300">
                  {q}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================== */
/*  Loading skeleton                                                   */
/* ================================================================== */

function ProjectDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="skeleton h-8 w-8 rounded-lg" />
        <div className="skeleton h-7 w-64" />
        <div className="skeleton h-6 w-20 rounded-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <div className="skeleton h-5 w-32" />
          <div className="skeleton h-3 w-full" />
          <div className="skeleton h-3 w-3/4" />
          <div className="skeleton h-20 w-full" />
        </div>
        <div className="card space-y-4">
          <div className="skeleton h-5 w-32" />
          <div className="skeleton h-40 w-full" />
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Project Detail / Dashboard Page                                    */
/* ================================================================== */

type TabId = "overview" | "files" | "coo-briefing" | "custom";

export function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const {
    selectedProject: project,
    isLoading,
    error,
    fetchProjectDetail,
    triggerAnalysis,
    analysisStatus,
    projectFiles,
    fetchProjectFiles,
  } = useProjectStore();

  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const analyzing =
    analysisStatus === "pending" || analysisStatus === "processing";

  useEffect(() => {
    if (projectId) {
      fetchProjectDetail(projectId);
      fetchProjectFiles(projectId);
    }
  }, [projectId, fetchProjectDetail, fetchProjectFiles]);

  // Scope chat to this project while on this page
  useEffect(() => {
    if (projectId) {
      useChatStore.getState().setActiveProject(projectId);
      useChatStore.getState().fetchHistory(projectId);
    }
    return () => {
      useChatStore.getState().setActiveProject(null);
    };
  }, [projectId]);

  const handleAnalyze = async () => {
    if (!projectId || analyzing) return;
    try {
      await triggerAnalysis(projectId);
    } catch {
      // Error is set in the store.
    }
  };

  if (isLoading && !project) {
    return (
      <div className="animate-fade-in">
        <ProjectDetailSkeleton />
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertTriangle className="mb-4 h-12 w-12 text-red-400" />
        <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          Failed to load project
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          {error}
        </p>
        <Link to="/" className="btn-secondary">
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!project) return null;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <FolderKanban className="h-7 w-7 text-teal-600 dark:text-teal-400" />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                {project.name}
              </h1>
              <span className={cn("badge", statusColors[project.status])}>
                {statusLabels[project.status] ?? project.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {project.description || "No description"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <HealthScoreCompact score={healthToNumber(project.health_score)} />
          <div className="flex flex-col gap-1">
            <DeadlineCountdown deadline={project.deadline} />
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Last analyzed:{" "}
              {formatRelativeTime(
                getLastAnalyzed(project as unknown as AnyProject),
              )}
            </p>
          </div>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="btn-primary"
          >
            {analysisStatus === "pending" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : analysisStatus === "processing" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                Analyze
              </>
            )}
          </button>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {(
          [
            { id: "overview" as TabId, label: "Overview", count: 0 },
            { id: "files" as TabId, label: "Files", count: projectFiles.length },
            { id: "coo-briefing" as TabId, label: "COO Briefing", count: 0 },
            { id: "custom" as TabId, label: "Custom Dashboard", count: 0 },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-teal-500 text-teal-700 dark:text-teal-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300",
            )}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-1.5 rounded-full bg-slate-200 px-1.5 py-0.5 text-2xs tabular-nums text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Completion bar */}
          {(() => {
            const pct = getCompletionPct(project as unknown as AnyProject);
            return (
              <div className="card p-5">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                    Overall Completion
                  </h3>
                  <span className="text-lg font-bold tabular-nums text-slate-900 dark:text-white">
                    {pct}%
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      pct >= 80
                        ? "bg-teal-500"
                        : pct >= 50
                          ? "bg-chief-500"
                          : "bg-warm-500",
                    )}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
              </div>
            );
          })()}

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Sprint Health */}
            <SprintHealthSection project={project} />

            {/* People */}
            <PeopleSection
              members={getTeamMembers(project as unknown as AnyProject)}
            />
          </div>

          {/* Gap Analysis */}
          <GapAnalysisSection project={project} />

          {/* Technical Advisor */}
          <TechnicalAdvisorPanel project={project} />

          {/* Key risks */}
          {project.key_risks.length > 0 && (
            <div className="card space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                <AlertTriangle className="h-4 w-4 text-warm-500" />
                Key Risks
              </h3>
              <div className="space-y-1.5">
                {project.key_risks.map((risk, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 rounded-lg bg-warm-50 px-3 py-2 dark:bg-warm-900/20"
                  >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-warm-500" />
                    <span className="text-sm text-warm-800 dark:text-warm-300">
                      {risk}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Files tab */}
      {activeTab === "files" && projectId && (
        <ProjectFilesTab projectId={projectId} />
      )}

      {/* COO Briefing tab */}
      {activeTab === "coo-briefing" && projectId && (
        <COOBriefingTab projectId={projectId} />
      )}

      {/* Custom Dashboard tab */}
      {activeTab === "custom" && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
            <BarChart3 className="h-8 w-8 text-teal-600 dark:text-teal-400" />
          </div>
          <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
            Custom Dashboard
          </h3>
          <p className="mb-4 max-w-sm text-sm text-slate-500 dark:text-slate-400">
            Build a custom dashboard with AI-generated widgets tailored to this
            project.
          </p>
          <Link
            to={`/projects/${projectId}/custom`}
            className="btn-primary"
          >
            Open Custom Dashboard
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}
