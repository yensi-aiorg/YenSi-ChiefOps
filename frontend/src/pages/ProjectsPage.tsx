import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FolderKanban,
  Plus,
  Upload,
  X,
  AlertTriangle,
  CheckCircle2,
  Clock,
  HelpCircle,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

/* ================================================================== */
/*  Health badge                                                       */
/* ================================================================== */

const healthStyles: Record<string, { bg: string; label: string; Icon: React.ComponentType<{ className?: string }> }> = {
  healthy: {
    bg: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
    label: "Healthy",
    Icon: CheckCircle2,
  },
  at_risk: {
    bg: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
    label: "At Risk",
    Icon: AlertTriangle,
  },
  critical: {
    bg: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
    label: "Critical",
    Icon: AlertTriangle,
  },
  unknown: {
    bg: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    label: "Not Analyzed",
    Icon: HelpCircle,
  },
};

function HealthBadge({ health }: { health: string }) {
  const cfg = healthStyles[health] ?? healthStyles["unknown"]!;
  return (
    <span className={cn("badge text-2xs inline-flex items-center gap-1", cfg.bg)}>
      <cfg.Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}

/* ================================================================== */
/*  Status badge                                                       */
/* ================================================================== */

const statusStyles: Record<string, { bg: string; label: string }> = {
  active: {
    bg: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
    label: "Active",
  },
  on_hold: {
    bg: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
    label: "On Hold",
  },
  completed: {
    bg: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
    label: "Completed",
  },
  cancelled: {
    bg: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    label: "Cancelled",
  },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = statusStyles[status] ?? statusStyles["active"]!;
  return <span className={cn("badge text-2xs", cfg.bg)}>{cfg.label}</span>;
}

/* ================================================================== */
/*  Project Card                                                       */
/* ================================================================== */

function ProjectCard({ project }: { project: Record<string, unknown> }) {
  const navigate = useNavigate();
  const name = (project.name as string) || "Untitled";
  const description = (project.description as string) || "";
  const projectId = project.project_id as string;
  const status = (project.status as string) || "active";
  const healthScore = (project.health_score as string) || "unknown";
  const teamSize = (project.team_size as number) || 0;
  const openTasks = (project.open_tasks as number) || 0;
  const completedTasks = (project.completed_tasks as number) || 0;
  const deadline = project.deadline as string | null;

  return (
    <button
      type="button"
      onClick={() => navigate(`/projects/${projectId}`)}
      className="card-interactive w-full text-left"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-slate-900 dark:text-white">
            {name}
          </h3>
          {description && (
            <p className="mt-1 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
              {description}
            </p>
          )}
        </div>
        <HealthBadge health={healthScore} />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <StatusBadge status={status} />
        {deadline && (
          <span className="inline-flex items-center gap-1 text-2xs text-slate-500 dark:text-slate-400">
            <Clock className="h-3 w-3" />
            {new Date(deadline).toLocaleDateString()}
          </span>
        )}
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
        <div>
          <p className="text-2xs text-slate-400 dark:text-slate-500">Team</p>
          <p className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-300">
            {teamSize}
          </p>
        </div>
        <div>
          <p className="text-2xs text-slate-400 dark:text-slate-500">Open</p>
          <p className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-300">
            {openTasks}
          </p>
        </div>
        <div>
          <p className="text-2xs text-slate-400 dark:text-slate-500">Done</p>
          <p className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-300">
            {completedTasks}
          </p>
        </div>
      </div>
    </button>
  );
}

/* ================================================================== */
/*  Skeleton card                                                      */
/* ================================================================== */

function SkeletonProjectCard() {
  return (
    <div className="card space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-32" />
          <div className="skeleton h-3 w-48" />
        </div>
        <div className="skeleton h-5 w-20 rounded-full" />
      </div>
      <div className="skeleton h-px w-full" />
      <div className="grid grid-cols-3 gap-2">
        <div className="skeleton h-8 w-full" />
        <div className="skeleton h-8 w-full" />
        <div className="skeleton h-8 w-full" />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Create Project Dialog                                              */
/* ================================================================== */

function CreateProjectDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { createProject, isLoading } = useProjectStore();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!name.trim()) {
        setError("Project name is required.");
        return;
      }
      setError(null);
      try {
        await createProject({ name: name.trim(), description: description.trim() } as Parameters<typeof createProject>[0]);
        setName("");
        setDescription("");
        onCreated();
        onClose();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create project.");
      }
    },
    [name, description, createProject, onCreated, onClose],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-surface-dark">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            New Project
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="project-name"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Project Name
            </label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. D2L Learning Academy"
              className="input w-full"
              autoFocus
            />
          </div>

          <div>
            <label
              htmlFor="project-description"
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Description
            </label>
            <textarea
              id="project-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief project description..."
              rows={3}
              className="input w-full resize-none"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? "Creating..." : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Projects Page                                                      */
/* ================================================================== */

export function ProjectsPage() {
  const { projects, isLoading, fetchProjects } = useProjectStore();
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreated = useCallback(() => {
    fetchProjects();
  }, [fetchProjects]);

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderKanban className="h-6 w-6 text-teal-600 dark:text-teal-400" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Projects
          </h1>
          {projects.length > 0 && (
            <span className="badge-neutral ml-2">
              {projects.length} project{projects.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="btn-primary"
        >
          <Plus className="h-4 w-4" />
          New Project
        </button>
      </div>

      {/* Loading skeletons */}
      {isLoading && projects.length === 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonProjectCard key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
            <FolderKanban className="h-10 w-10 text-teal-600 dark:text-teal-400" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
            No projects yet
          </h2>
          <p className="mb-6 max-w-md text-sm text-slate-500 dark:text-slate-400">
            Create a project manually or upload Jira/Slack data to auto-discover
            projects from your team's activity.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setDialogOpen(true)}
              className="btn-primary"
            >
              <Plus className="h-4 w-4" />
              Create Project
            </button>
            <Link to="/upload" className="btn-secondary">
              <Upload className="h-4 w-4" />
              Upload Data
            </Link>
          </div>
        </div>
      )}

      {/* Project cards grid */}
      {projects.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.project_id}
              project={project as unknown as Record<string, unknown>}
            />
          ))}
        </div>
      )}

      {/* Create project dialog */}
      <CreateProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}
