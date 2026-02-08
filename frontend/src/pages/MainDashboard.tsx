import { useEffect, useMemo } from "react";
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
  Activity,
  XCircle,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useAlertStore } from "@/stores/alertStore";
import { useDashboardStore } from "@/stores/dashboardStore";
import { cn } from "@/lib/utils";
import {
  formatRelativeTime,
  getHealthScoreBadge,
  getHealthScoreColor,
} from "@/lib/utils";
import type { Project, AlertTriggered } from "@/types";

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
/*  Health Score Ring (large)                                           */
/* ================================================================== */

function HealthScoreRing({ score }: { score: number | null }) {
  const safeScore = score ?? 0;
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (safeScore / 100) * circumference;
  const badge = getHealthScoreBadge(safeScore);

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
    (p) => p.status !== "completed",
  ).length;
  const atRiskCount = projects.filter(
    (p) => p.status === "at_risk" || p.status === "behind",
  ).length;
  const totalPeople = useMemo(() => {
    const ids = new Set<string>();
    projects.forEach((p) =>
      p.people_involved.forEach((m) => ids.add(m.person_id)),
    );
    return ids.size;
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
  const statusColors: Record<string, string> = {
    on_track: "badge-teal",
    at_risk: "badge-warm",
    behind: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    completed:
      "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  };
  const statusLabels: Record<string, string> = {
    on_track: "On Track",
    at_risk: "At Risk",
    behind: "Behind",
    completed: "Completed",
  };

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
          <span className={cn("badge", statusColors[project.status])}>
            {statusLabels[project.status] ?? project.status}
          </span>
          <span
            className={cn(
              "text-lg font-bold tabular-nums",
              getHealthScoreColor(project.health_score),
            )}
          >
            {project.health_score}
          </span>
        </div>
      </div>

      {/* Completion bar */}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Completion</span>
          <span className="font-medium">
            {project.completion_percentage.toFixed(0)}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              project.completion_percentage >= 80
                ? "bg-teal-500"
                : project.completion_percentage >= 50
                  ? "bg-chief-500"
                  : "bg-warm-500",
            )}
            style={{
              width: `${Math.min(project.completion_percentage, 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <Users className="h-3.5 w-3.5" />
          {project.people_involved.length} member
          {project.people_involved.length !== 1 ? "s" : ""}
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
/*  Team Activity Summary                                              */
/* ================================================================== */

function TeamActivitySummary({ projects }: { projects: Project[] }) {
  const allMembers = useMemo(() => {
    const map = new Map<
      string,
      { name: string; role: string; activity_level: string; projectCount: number }
    >();
    projects.forEach((p) =>
      p.people_involved.forEach((m) => {
        const existing = map.get(m.person_id);
        if (existing) {
          existing.projectCount += 1;
        } else {
          map.set(m.person_id, {
            name: m.name,
            role: m.role,
            activity_level: m.activity_level,
            projectCount: 1,
          });
        }
      }),
    );
    return Array.from(map.values())
      .sort((a, b) => b.projectCount - a.projectCount)
      .slice(0, 8);
  }, [projects]);

  if (allMembers.length === 0) return null;

  const activityBadge = (level: string) => {
    const styles: Record<string, string> = {
      very_active:
        "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
      active:
        "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
      moderate:
        "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
      quiet:
        "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
      inactive:
        "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
    };
    const labels: Record<string, string> = {
      very_active: "Very Active",
      active: "Active",
      moderate: "Moderate",
      quiet: "Quiet",
      inactive: "Inactive",
    };
    return (
      <span
        className={cn(
          "badge text-2xs",
          styles[level] ?? styles.moderate,
        )}
      >
        {labels[level] ?? level}
      </span>
    );
  };

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <Activity className="h-4 w-4 text-teal-500" />
          Team Activity Summary
        </h3>
        <Link
          to="/people"
          className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
        >
          View all
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Role</th>
              <th className="pb-2 pr-4">Activity</th>
              <th className="pb-2 text-right">Projects</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {allMembers.map((m, i) => (
              <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                <td className="py-2.5 pr-4 font-medium text-slate-900 dark:text-white">
                  {m.name}
                </td>
                <td className="py-2.5 pr-4 text-slate-600 dark:text-slate-400">
                  {m.role}
                </td>
                <td className="py-2.5 pr-4">{activityBadge(m.activity_level)}</td>
                <td className="py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-400">
                  {m.projectCount}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
/*  Main Dashboard Page                                                */
/* ================================================================== */

export function MainDashboard() {
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
  const { fetchDashboards } = useDashboardStore();

  useEffect(() => {
    fetchProjects();
    fetchTriggeredAlerts();
    fetchDashboards();
  }, [fetchProjects, fetchTriggeredAlerts, fetchDashboards]);

  // Computed stats
  const activeProjects = projects.filter((p) => p.status !== "completed");
  const totalPeople = useMemo(() => {
    const ids = new Set<string>();
    projects.forEach((p) =>
      p.people_involved.forEach((m) => ids.add(m.person_id)),
    );
    return ids.size;
  }, [projects]);
  const openTasks = useMemo(
    () =>
      projects.reduce(
        (sum, p) =>
          sum + p.task_summary.to_do + p.task_summary.in_progress + p.task_summary.blocked,
        0,
      ),
    [projects],
  );
  const avgHealth = useMemo(() => {
    if (activeProjects.length === 0) return null;
    const sum = activeProjects.reduce((s, p) => s + p.health_score, 0);
    return Math.round(sum / activeProjects.length);
  }, [activeProjects]);

  const activeAlerts = triggeredAlerts.filter((a) => !a.acknowledged);
  const unreadCount = activeAlerts.length;
  const isLoading = projectsLoading || alertsLoading;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <LayoutDashboard className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Dashboard
        </h1>
      </div>

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

      {(projects.length > 0 || (!isLoading && projects.length > 0)) && (
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

          {/* Team activity summary */}
          <TeamActivitySummary projects={projects} />
        </>
      )}
    </div>
  );
}
