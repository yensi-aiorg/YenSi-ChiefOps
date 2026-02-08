import {
  MessageSquare,
  ListTodo,
  FolderOpen,
  Mail,
  Clock,
  MessagesSquare,
  Smile,
  FolderKanban,
} from "lucide-react";
import type { Person } from "@/types";
import { ActivityLevel, SourceSystem } from "@/types";
import {
  cn,
  getInitials,
  formatRelativeTime,
  formatNumber,
  formatPercentage,
} from "@/lib/utils";
import { RoleBadge } from "./RoleBadge";

/* ------------------------------------------------------------------ */
/*  PersonDetail – full person profile view                            */
/* ------------------------------------------------------------------ */

interface PersonDetailProps {
  person: Person;
  className?: string;
}

function getAvatarGradient(name: string): string {
  const gradients = [
    "from-teal-400 to-teal-600",
    "from-chief-400 to-chief-600",
    "from-purple-400 to-purple-600",
    "from-warm-400 to-warm-600",
    "from-green-400 to-green-600",
    "from-blue-400 to-blue-600",
    "from-rose-400 to-rose-600",
    "from-indigo-400 to-indigo-600",
  ];
  const index = name.charCodeAt(0) % gradients.length;
  return gradients[index] ?? gradients[0]!;
}

function getActivityConfig(level: ActivityLevel | string): {
  color: string;
  bgBar: string;
  label: string;
  pct: number;
} {
  switch (level) {
    case ActivityLevel.VERY_ACTIVE:
    case "very_active":
      return {
        color: "bg-green-500",
        bgBar: "bg-green-100 dark:bg-green-900/30",
        label: "Very Active",
        pct: 100,
      };
    case ActivityLevel.ACTIVE:
    case "active":
      return {
        color: "bg-green-400",
        bgBar: "bg-green-100 dark:bg-green-900/30",
        label: "Active",
        pct: 80,
      };
    case ActivityLevel.MODERATE:
    case "moderate":
      return {
        color: "bg-yellow-400",
        bgBar: "bg-yellow-100 dark:bg-yellow-900/30",
        label: "Moderate",
        pct: 55,
      };
    case ActivityLevel.QUIET:
    case "quiet":
      return {
        color: "bg-orange-400",
        bgBar: "bg-orange-100 dark:bg-orange-900/30",
        label: "Quiet",
        pct: 30,
      };
    case ActivityLevel.INACTIVE:
    case "inactive":
      return {
        color: "bg-red-400",
        bgBar: "bg-red-100 dark:bg-red-900/30",
        label: "Inactive",
        pct: 10,
      };
    default:
      return {
        color: "bg-slate-300",
        bgBar: "bg-slate-100 dark:bg-slate-800",
        label: "Unknown",
        pct: 0,
      };
  }
}

function getSourceIcon(source: SourceSystem | string) {
  switch (source) {
    case SourceSystem.SLACK:
    case "slack":
      return MessageSquare;
    case SourceSystem.JIRA:
    case "jira":
      return ListTodo;
    case SourceSystem.GDRIVE:
    case "gdrive":
    case "drive":
      return FolderOpen;
    default:
      return FolderOpen;
  }
}

export function PersonDetail({ person, className }: PersonDetailProps) {
  const initials = getInitials(person.name);
  const gradient = getAvatarGradient(person.name);
  const activity = getActivityConfig(person.activity_level);
  const completionRate =
    person.tasks_assigned > 0
      ? (person.tasks_completed / person.tasks_assigned) * 100
      : 0;
  const circumference = 2 * Math.PI * 38;
  const strokeDashoffset = circumference - (completionRate / 100) * circumference;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="card flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        {/* Large avatar */}
        <div className="relative shrink-0">
          {person.avatar_url ? (
            <img
              src={person.avatar_url}
              alt={person.name}
              className="h-20 w-20 rounded-2xl object-cover ring-4 ring-white shadow-soft dark:ring-surface-dark-card"
            />
          ) : (
            <div
              className={cn(
                "flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br text-xl font-bold text-white ring-4 ring-white shadow-soft dark:ring-surface-dark-card",
                gradient,
              )}
            >
              {initials}
            </div>
          )}
        </div>

        <div className="flex-1 text-center sm:text-left">
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">
            {person.name}
          </h1>

          <div className="mt-1.5 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <RoleBadge role={person.role} source={person.role_source} />
            {person.department && (
              <span className="badge-neutral">{person.department}</span>
            )}
          </div>

          {person.email && (
            <div className="mt-2 flex items-center justify-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 sm:justify-start">
              <Mail className="h-3.5 w-3.5" />
              <span>{person.email}</span>
            </div>
          )}

          {person.last_active_date && (
            <div className="mt-1 flex items-center justify-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 sm:justify-start">
              <Clock className="h-3 w-3" />
              <span>Last active {formatRelativeTime(person.last_active_date)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Activity level */}
      <div className="card">
        <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
          Activity Level
        </h2>
        <div className="flex items-center gap-3">
          <div className={cn("h-2 flex-1 rounded-full", activity.bgBar)}>
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                activity.color,
              )}
              style={{ width: `${activity.pct}%` }}
            />
          </div>
          <span
            className={cn(
              "text-sm font-medium",
              activity.pct > 60
                ? "text-green-600 dark:text-green-400"
                : activity.pct > 30
                  ? "text-yellow-600 dark:text-yellow-400"
                  : "text-red-600 dark:text-red-400",
            )}
          >
            {activity.label}
          </span>
        </div>
      </div>

      {/* Source references */}
      {(person.source_ids.length > 0 ||
        person.slack_user_id ||
        person.jira_username) && (
        <div className="card">
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
            Source References
          </h2>
          <div className="space-y-2">
            {person.slack_user_id && (
              <div className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800">
                <MessageSquare className="h-4 w-4 text-purple-500" />
                <div>
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    Slack User ID
                  </p>
                  <p className="font-mono text-2xs text-slate-500 dark:text-slate-400">
                    {person.slack_user_id}
                  </p>
                </div>
              </div>
            )}
            {person.jira_username && (
              <div className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800">
                <ListTodo className="h-4 w-4 text-blue-500" />
                <div>
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    Jira Username
                  </p>
                  <p className="font-mono text-2xs text-slate-500 dark:text-slate-400">
                    {person.jira_username}
                  </p>
                </div>
              </div>
            )}
            {person.source_ids.map((ref, idx) => {
              const Icon = getSourceIcon(ref.source);
              return (
                <div
                  key={`${ref.source}-${ref.source_id}-${idx}`}
                  className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800"
                >
                  <Icon className="h-4 w-4 text-slate-400" />
                  <div>
                    <p className="text-xs font-medium capitalize text-slate-700 dark:text-slate-300">
                      {String(ref.source)}
                    </p>
                    <p className="font-mono text-2xs text-slate-500 dark:text-slate-400">
                      {ref.source_id}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Engagement metrics */}
      <div className="card">
        <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
          Engagement Metrics
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <MetricTile
            icon={<MessageSquare className="h-4 w-4 text-teal-500" />}
            label="Messages Sent"
            value={person.engagement_metrics.messages_sent}
          />
          <MetricTile
            icon={<MessagesSquare className="h-4 w-4 text-chief-500" />}
            label="Threads Replied"
            value={person.engagement_metrics.threads_replied}
          />
          <MetricTile
            icon={<Smile className="h-4 w-4 text-warm-500" />}
            label="Reactions Given"
            value={person.engagement_metrics.reactions_given}
          />
        </div>
      </div>

      {/* Project involvement */}
      {person.projects.length > 0 && (
        <div className="card">
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
            Project Involvement
          </h2>
          <div className="space-y-1.5">
            {person.projects.map((projectId) => (
              <div
                key={projectId}
                className="flex items-center gap-2.5 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800"
              >
                <FolderKanban className="h-4 w-4 text-teal-500" />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {projectId}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task breakdown with progress ring */}
      <div className="card">
        <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">
          Task Breakdown
        </h2>
        <div className="flex items-center gap-6">
          {/* Progress ring */}
          <div className="relative h-24 w-24 shrink-0">
            <svg
              className="-rotate-90"
              viewBox="0 0 80 80"
              width="96"
              height="96"
            >
              <circle
                cx="40"
                cy="40"
                r="38"
                fill="none"
                stroke="currentColor"
                strokeWidth="4"
                className="text-slate-100 dark:text-slate-700"
              />
              <circle
                cx="40"
                cy="40"
                r="38"
                fill="none"
                stroke="currentColor"
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="text-teal-500 transition-all duration-700"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-base font-bold text-slate-900 dark:text-white">
                {formatPercentage(completionRate)}
              </span>
            </div>
          </div>

          {/* Breakdown stats */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Assigned
              </span>
              <span className="text-sm font-semibold text-slate-900 dark:text-white">
                {formatNumber(person.tasks_assigned)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Completed
              </span>
              <span className="text-sm font-semibold text-green-600 dark:text-green-400">
                {formatNumber(person.tasks_completed)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Remaining
              </span>
              <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
                {formatNumber(
                  Math.max(0, person.tasks_assigned - person.tasks_completed),
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* -- Helper sub-component ------------------------------------------ */

function MetricTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg bg-slate-50 px-3 py-3 dark:bg-slate-800">
      {icon}
      <span className="text-lg font-bold text-slate-900 dark:text-white">
        {formatNumber(value)}
      </span>
      <span className="text-center text-2xs text-slate-500 dark:text-slate-400">
        {label}
      </span>
    </div>
  );
}
