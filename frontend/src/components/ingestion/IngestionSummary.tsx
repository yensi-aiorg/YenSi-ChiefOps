import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MessageSquare,
  ListTodo,
  FolderOpen,
  FileText,
  Copy,
  BarChart3,
} from "lucide-react";
import type { IngestionJob } from "@/types";
import { IngestionFileStatus } from "@/types";
import { cn, formatNumber } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  IngestionSummary – post-upload summary card                        */
/* ------------------------------------------------------------------ */

interface IngestionSummaryProps {
  job: IngestionJob;
  className?: string;
}

type JobOutcome = "success" | "partial" | "failure";

function getJobOutcome(job: IngestionJob): JobOutcome {
  const allCompleted = job.files.every(
    (f) =>
      f.status === IngestionFileStatus.COMPLETED ||
      f.status === ("completed" as IngestionFileStatus),
  );
  const allFailed = job.files.every(
    (f) =>
      f.status === IngestionFileStatus.FAILED ||
      f.status === ("failed" as IngestionFileStatus),
  );

  if (allCompleted) return "success";
  if (allFailed) return "failure";
  return "partial";
}

const OUTCOME_CONFIG: Record<
  JobOutcome,
  {
    icon: React.ComponentType<{ className?: string }>;
    title: string;
    bg: string;
    text: string;
    border: string;
    iconColor: string;
  }
> = {
  success: {
    icon: CheckCircle2,
    title: "Upload Complete",
    bg: "bg-green-50 dark:bg-green-900/10",
    text: "text-green-800 dark:text-green-300",
    border: "border-green-200 dark:border-green-800",
    iconColor: "text-green-500",
  },
  partial: {
    icon: AlertTriangle,
    title: "Partial Upload",
    bg: "bg-amber-50 dark:bg-amber-900/10",
    text: "text-amber-800 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-800",
    iconColor: "text-amber-500",
  },
  failure: {
    icon: XCircle,
    title: "Upload Failed",
    bg: "bg-red-50 dark:bg-red-900/10",
    text: "text-red-800 dark:text-red-300",
    border: "border-red-200 dark:border-red-800",
    iconColor: "text-red-500",
  },
};

function categorizeFiles(job: IngestionJob) {
  let slackRecords = 0;
  let jiraRecords = 0;
  let driveRecords = 0;
  let otherRecords = 0;

  for (const file of job.files) {
    const typeStr =
      typeof file.file_type === "string"
        ? file.file_type
        : String(file.file_type);
    const lower = typeStr.toLowerCase();

    if (lower.includes("slack")) {
      slackRecords += file.records_processed;
    } else if (lower.includes("jira")) {
      jiraRecords += file.records_processed;
    } else if (lower.includes("drive") || lower.includes("document")) {
      driveRecords += file.records_processed;
    } else {
      otherRecords += file.records_processed;
    }
  }

  return { slackRecords, jiraRecords, driveRecords, otherRecords };
}

export function IngestionSummary({ job, className }: IngestionSummaryProps) {
  const outcome = getJobOutcome(job);
  const config = OUTCOME_CONFIG[outcome];
  const OutcomeIcon = config.icon;
  const { slackRecords, jiraRecords, driveRecords, otherRecords } =
    categorizeFiles(job);

  const totalRecords = job.total_records;
  const totalDuplicates = job.files.reduce(
    (sum, f) => sum + f.records_skipped,
    0,
  );
  const totalErrors = job.error_count;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border",
        config.border,
        className,
      )}
    >
      {/* Header */}
      <div className={cn("flex items-center gap-3 px-5 py-4", config.bg)}>
        <OutcomeIcon className={cn("h-6 w-6", config.iconColor)} />
        <div>
          <h3 className={cn("text-sm font-semibold", config.text)}>
            {config.title}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {job.files.length} file{job.files.length !== 1 ? "s" : ""} processed
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-px bg-slate-100 dark:bg-slate-700 sm:grid-cols-4">
        <StatCell
          icon={<FileText className="h-4 w-4 text-slate-400" />}
          label="Total Files"
          value={job.files.length}
        />
        <StatCell
          icon={<BarChart3 className="h-4 w-4 text-teal-500" />}
          label="Records Ingested"
          value={totalRecords}
        />
        <StatCell
          icon={<Copy className="h-4 w-4 text-amber-500" />}
          label="Duplicates Skipped"
          value={totalDuplicates}
        />
        <StatCell
          icon={<XCircle className="h-4 w-4 text-red-500" />}
          label="Errors"
          value={totalErrors}
        />
      </div>

      {/* Breakdown by source type */}
      {(slackRecords > 0 ||
        jiraRecords > 0 ||
        driveRecords > 0 ||
        otherRecords > 0) && (
        <div className="border-t border-slate-100 bg-white px-5 py-4 dark:border-slate-700 dark:bg-surface-dark-card">
          <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Breakdown by Source
          </h4>
          <div className="space-y-2">
            {slackRecords > 0 && (
              <BreakdownRow
                icon={<MessageSquare className="h-4 w-4 text-purple-500" />}
                label="Slack Messages"
                count={slackRecords}
                color="bg-purple-500"
                total={totalRecords}
              />
            )}
            {jiraRecords > 0 && (
              <BreakdownRow
                icon={<ListTodo className="h-4 w-4 text-blue-500" />}
                label="Jira Tasks"
                count={jiraRecords}
                color="bg-blue-500"
                total={totalRecords}
              />
            )}
            {driveRecords > 0 && (
              <BreakdownRow
                icon={<FolderOpen className="h-4 w-4 text-amber-500" />}
                label="Drive Documents"
                count={driveRecords}
                color="bg-amber-500"
                total={totalRecords}
              />
            )}
            {otherRecords > 0 && (
              <BreakdownRow
                icon={<FileText className="h-4 w-4 text-slate-400" />}
                label="Other Records"
                count={otherRecords}
                color="bg-slate-400"
                total={totalRecords}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* -- Helper sub-components ----------------------------------------- */

function StatCell({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="flex flex-col items-center gap-1 bg-white px-4 py-4 dark:bg-surface-dark-card">
      {icon}
      <span className="text-lg font-bold text-slate-900 dark:text-white">
        {formatNumber(value)}
      </span>
      <span className="text-2xs text-slate-500 dark:text-slate-400">
        {label}
      </span>
    </div>
  );
}

function BreakdownRow({
  icon,
  label,
  count,
  color,
  total,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  color: string;
  total: number;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      {icon}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {label}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            {formatNumber(count)}
          </span>
        </div>
        <div className="mt-1 h-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
          <div
            className={cn("h-full rounded-full transition-all", color)}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
