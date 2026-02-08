import { useState, useEffect } from "react";
import {
  ChevronDown,
  ChevronRight,
  Calendar,
  AlertTriangle,
  HelpCircle,
  CheckCircle2,
  Gauge,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  TechnicalAdvisorPanel – project analysis: planning, gaps, Q&A     */
/* ------------------------------------------------------------------ */

interface TechnicalAdvisorPanelProps {
  projectId: string;
  className?: string;
}

/* -- Section collapse wrapper -------------------------------------- */

function CollapsibleSection({
  title,
  icon,
  count,
  defaultOpen = true,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 text-left"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
        )}
        {icon}
        <span className="flex-1 text-sm font-semibold text-slate-900 dark:text-white">
          {title}
        </span>
        {count !== undefined && count > 0 && (
          <span className="badge-neutral">{count}</span>
        )}
      </button>

      {open && <div className="mt-4">{children}</div>}
    </div>
  );
}

/* -- Backward Planning Timeline ------------------------------------ */

interface BackwardPlanItemProps {
  task: string;
  estimatedDays: number;
  dependsOn: string[];
  priority: string;
  index: number;
  total: number;
}

function BackwardPlanBar({
  task,
  estimatedDays,
  dependsOn,
  priority,
  index,
  total,
}: BackwardPlanItemProps) {
  const maxDays = 30;
  const widthPct = Math.min((estimatedDays / maxDays) * 100, 100);
  const offsetPct = (index / total) * 60;

  function getPriorityColor(p: string): string {
    switch (p.toLowerCase()) {
      case "critical":
        return "bg-red-500";
      case "high":
        return "bg-orange-500";
      case "medium":
        return "bg-yellow-500";
      case "low":
        return "bg-blue-500";
      default:
        return "bg-teal-500";
    }
  }

  return (
    <div className="group">
      <div className="flex items-center gap-3">
        <div className="w-32 shrink-0">
          <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-300">
            {task}
          </p>
          <p className="text-2xs text-slate-400">
            {estimatedDays} day{estimatedDays !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex-1">
          <div className="h-6 rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className={cn(
                "flex h-full items-center rounded-full px-2 text-2xs font-medium text-white transition-all",
                getPriorityColor(priority),
              )}
              style={{
                width: `${Math.max(widthPct, 15)}%`,
                marginLeft: `${offsetPct}%`,
              }}
            >
              <span className="truncate">{task}</span>
            </div>
          </div>
        </div>
      </div>
      {dependsOn.length > 0 && (
        <div className="ml-[140px] mt-1 hidden text-2xs text-slate-400 group-hover:block dark:text-slate-500">
          Depends on: {dependsOn.join(", ")}
        </div>
      )}
    </div>
  );
}

/* -- Missing Task Card --------------------------------------------- */

function MissingTaskCard({
  task,
  index,
}: {
  task: string;
  index: number;
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/50 px-4 py-3 dark:border-amber-800 dark:bg-amber-900/10">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
      <div>
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
          {task}
        </p>
        <p className="mt-0.5 text-2xs text-amber-600 dark:text-amber-400">
          Missing task #{index + 1} -- identified by AI analysis
        </p>
      </div>
    </div>
  );
}

/* -- Architect Question Accordion ---------------------------------- */

function ArchitectQuestionItem({
  question,
}: {
  question: string;
  index: number;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left"
      >
        <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-chief-500" />
        <span className="flex-1 text-sm font-medium text-slate-800 dark:text-slate-200">
          {question}
        </span>
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
        )}
      </button>
      {open && (
        <div className="border-t border-slate-100 px-4 py-3 dark:border-slate-700">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            This question was identified during technical feasibility analysis.
            Consider discussing with your engineering lead or technical architect
            to determine the best path forward.
          </p>
        </div>
      )}
    </div>
  );
}

/* -- Main Component ------------------------------------------------ */

export function TechnicalAdvisorPanel({
  projectId,
  className,
}: TechnicalAdvisorPanelProps) {
  const { selectedProject, fetchProjectDetail, isLoading } = useProjectStore();

  useEffect(() => {
    if (!selectedProject || selectedProject.project_id !== projectId) {
      fetchProjectDetail(projectId);
    }
  }, [projectId, selectedProject, fetchProjectDetail]);

  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
            <span className="text-sm text-slate-500 dark:text-slate-400">
              Loading project analysis...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (!selectedProject) {
    return (
      <div className={cn("card", className)}>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No project data available.
        </p>
      </div>
    );
  }

  const project = selectedProject;
  const backwardPlan = project.gap_analysis?.backward_plan ?? [];
  const missingTasks = project.missing_tasks ?? [];
  const architectQuestions =
    project.technical_feasibility?.architect_questions ?? [];

  return (
    <div className={cn("space-y-4", className)}>
      {/* Section header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-chief-500 to-chief-600">
          <Gauge className="h-5 w-5 text-white" />
        </div>
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Technical Advisor
          </h2>
          <p className="text-2xs text-slate-500 dark:text-slate-400">
            AI-powered project analysis for {project.name}
          </p>
        </div>
      </div>

      {/* Backward Planning */}
      <CollapsibleSection
        title="Backward Planning"
        icon={<Calendar className="h-4 w-4 text-teal-500" />}
        count={backwardPlan.length}
        defaultOpen={true}
      >
        {backwardPlan.length > 0 ? (
          <div className="space-y-3">
            {backwardPlan.map((item, idx) => (
              <BackwardPlanBar
                key={`bp-${idx}`}
                task={item.task}
                estimatedDays={item.estimated_days}
                dependsOn={item.depends_on}
                priority={item.priority}
                index={idx}
                total={backwardPlan.length}
              />
            ))}
          </div>
        ) : (
          <EmptyState message="No backward planning items available. Trigger an analysis to generate a plan." />
        )}
      </CollapsibleSection>

      {/* Missing Tasks */}
      <CollapsibleSection
        title="Missing Tasks"
        icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
        count={missingTasks.length}
        defaultOpen={missingTasks.length > 0}
      >
        {missingTasks.length > 0 ? (
          <div className="space-y-2">
            {missingTasks.map((task, idx) => (
              <MissingTaskCard key={`mt-${idx}`} task={task} index={idx} />
            ))}
          </div>
        ) : (
          <EmptyState message="No missing tasks detected. Your project planning looks comprehensive." />
        )}
      </CollapsibleSection>

      {/* Architect Questions */}
      <CollapsibleSection
        title="Architect Questions"
        icon={<HelpCircle className="h-4 w-4 text-chief-500" />}
        count={architectQuestions.length}
        defaultOpen={architectQuestions.length > 0}
      >
        {architectQuestions.length > 0 ? (
          <div className="space-y-2">
            {architectQuestions.map((q, idx) => (
              <ArchitectQuestionItem
                key={`aq-${idx}`}
                question={q}
                index={idx}
              />
            ))}
          </div>
        ) : (
          <EmptyState message="No open architect questions. Your technical approach is well-defined." />
        )}
      </CollapsibleSection>
    </div>
  );
}

/* -- Empty state helper -------------------------------------------- */

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-4 py-3 dark:bg-slate-800">
      <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
      <p className="text-sm text-slate-600 dark:text-slate-400">{message}</p>
    </div>
  );
}
