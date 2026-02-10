import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Mail,
  Building2,
  Briefcase,
  Clock,
  CheckCircle2,
  ListTodo,
  MessageSquare,
  MessagesSquare,
  Heart,
  Loader2,
  AlertTriangle,
  FolderKanban,
} from "lucide-react";
import { usePeopleStore } from "@/stores/peopleStore";
import { cn } from "@/lib/utils";
import { formatDate, getInitials } from "@/lib/utils";

const activityColors: Record<string, string> = {
  very_active:
    "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
  active: "badge-teal",
  moderate:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
  quiet:
    "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  inactive:
    "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
};

const activityLabels: Record<string, string> = {
  very_active: "Very Active",
  active: "Active",
  moderate: "Moderate",
  quiet: "Quiet",
  inactive: "Inactive",
};

export function PersonDetail() {
  const { personId } = useParams<{ personId: string }>();
  const { selectedPerson: person, isLoading, error, fetchPersonDetail } =
    usePeopleStore();

  useEffect(() => {
    if (personId) {
      fetchPersonDetail(personId);
    }
  }, [personId, fetchPersonDetail]);

  if (isLoading && !person) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (error && !person) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertTriangle className="mb-4 h-12 w-12 text-red-400" />
        <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          Failed to load person
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          {error}
        </p>
        <Link to="/people" className="btn-secondary">
          <ArrowLeft className="h-4 w-4" />
          Back to People
        </Link>
      </div>
    );
  }

  if (!person) return null;

  const engagement = person.engagement_metrics ?? {
    messages_sent: 0,
    threads_replied: 0,
    reactions_given: 0,
  };

  const taskTotal = person.tasks_assigned ?? 0;
  const taskDone = person.tasks_completed ?? 0;
  const taskPct = taskTotal > 0 ? Math.round((taskDone / taskTotal) * 100) : 0;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Back link */}
      <Link
        to="/people"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to People
      </Link>

      {/* Header */}
      <div className="flex flex-wrap items-start gap-5">
        <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-chief-500 text-xl font-bold text-white shadow-md">
          {person.avatar_url ? (
            <img
              src={person.avatar_url}
              alt={person.name}
              className="h-16 w-16 rounded-2xl object-cover"
            />
          ) : (
            getInitials(person.name)
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              {person.name}
            </h1>
            <span
              className={cn(
                "badge",
                activityColors[person.activity_level] ?? "badge-teal",
              )}
            >
              {activityLabels[person.activity_level] ?? person.activity_level}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
            {person.role && (
              <span className="flex items-center gap-1.5">
                <Briefcase className="h-3.5 w-3.5" />
                {person.role}
              </span>
            )}
            {person.department && (
              <span className="flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5" />
                {person.department}
              </span>
            )}
            {person.email && (
              <span className="flex items-center gap-1.5">
                <Mail className="h-3.5 w-3.5" />
                {person.email}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100 dark:bg-teal-900/40">
            <ListTodo className="h-5 w-5 text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Tasks Assigned
            </p>
            <p className="text-lg font-bold tabular-nums text-slate-900 dark:text-white">
              {taskTotal}
            </p>
          </div>
        </div>

        <div className="card flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900/40">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Tasks Completed
            </p>
            <p className="text-lg font-bold tabular-nums text-slate-900 dark:text-white">
              {taskDone}
            </p>
          </div>
        </div>

        <div className="card flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-chief-100 dark:bg-chief-900/40">
            <MessageSquare className="h-5 w-5 text-chief-600 dark:text-chief-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Messages Sent
            </p>
            <p className="text-lg font-bold tabular-nums text-slate-900 dark:text-white">
              {engagement.messages_sent ?? 0}
            </p>
          </div>
        </div>

        <div className="card flex items-center gap-3 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-warm-100 dark:bg-warm-900/40">
            <Clock className="h-5 w-5 text-warm-600 dark:text-warm-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Last Active
            </p>
            <p className="text-sm font-medium text-slate-900 dark:text-white">
              {formatDate(person.last_active_date)}
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Task completion */}
        <div className="card space-y-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <CheckCircle2 className="h-4 w-4 text-teal-500" />
            Task Completion
          </h3>
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
              <span>Progress</span>
              <span className="font-medium">{taskPct}%</span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  taskPct >= 80
                    ? "bg-teal-500"
                    : taskPct >= 50
                      ? "bg-chief-500"
                      : "bg-warm-500",
                )}
                style={{ width: `${Math.min(taskPct, 100)}%` }}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Assigned
              </p>
              <p className="mt-0.5 text-lg font-bold tabular-nums text-slate-700 dark:text-slate-300">
                {taskTotal}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Completed
              </p>
              <p className="mt-0.5 text-lg font-bold tabular-nums text-green-600 dark:text-green-400">
                {taskDone}
              </p>
            </div>
          </div>
        </div>

        {/* Engagement metrics */}
        <div className="card space-y-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <MessageSquare className="h-4 w-4 text-teal-500" />
            Engagement Metrics
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <MessageSquare className="mx-auto mb-1 h-4 w-4 text-chief-500" />
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Messages
              </p>
              <p className="mt-0.5 text-lg font-bold tabular-nums text-slate-700 dark:text-slate-300">
                {engagement.messages_sent ?? 0}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <MessagesSquare className="mx-auto mb-1 h-4 w-4 text-teal-500" />
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Threads
              </p>
              <p className="mt-0.5 text-lg font-bold tabular-nums text-slate-700 dark:text-slate-300">
                {engagement.threads_replied ?? 0}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800/50">
              <Heart className="mx-auto mb-1 h-4 w-4 text-warm-500" />
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Reactions
              </p>
              <p className="mt-0.5 text-lg font-bold tabular-nums text-slate-700 dark:text-slate-300">
                {engagement.reactions_given ?? 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Projects */}
      {Array.isArray(person.projects) && person.projects.length > 0 && (
        <div className="card space-y-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <FolderKanban className="h-4 w-4 text-teal-500" />
            Projects ({person.projects.length})
          </h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {person.projects.map((projectId) => (
              <Link
                key={projectId}
                to={`/projects/${projectId}`}
                className="flex items-center gap-3 rounded-lg bg-slate-50 p-3 transition-colors hover:bg-slate-100 dark:bg-slate-800/50 dark:hover:bg-slate-800"
              >
                <FolderKanban className="h-4 w-4 flex-shrink-0 text-teal-500" />
                <span className="truncate text-sm font-medium text-slate-700 dark:text-slate-300">
                  {projectId}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Metadata footer */}
      <div className="flex flex-wrap gap-6 text-xs text-slate-400 dark:text-slate-500">
        <span>Created: {formatDate(person.created_at)}</span>
        <span>Updated: {formatDate(person.updated_at)}</span>
        {person.role_source && (
          <span>
            Role source:{" "}
            {person.role_source === "coo_corrected"
              ? "COO Corrected"
              : "AI Identified"}
          </span>
        )}
      </div>
    </div>
  );
}
