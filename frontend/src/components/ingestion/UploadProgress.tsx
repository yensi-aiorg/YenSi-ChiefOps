import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  SkipForward,
  FileText,
} from "lucide-react";
import type { IngestionJob, IngestionFileResult } from "@/types";
import { IngestionFileStatus, IngestionFileType } from "@/types";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  UploadProgress – per-file progress for an ingestion job            */
/* ------------------------------------------------------------------ */

interface UploadProgressProps {
  job: IngestionJob;
  className?: string;
}

function getFileStatusIcon(status: IngestionFileStatus | string) {
  switch (status) {
    case IngestionFileStatus.COMPLETED:
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case IngestionFileStatus.FAILED:
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case IngestionFileStatus.PROCESSING:
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin text-teal-500" />;
    case IngestionFileStatus.SKIPPED:
    case "skipped":
      return <SkipForward className="h-4 w-4 text-slate-400" />;
    default:
      return <Clock className="h-4 w-4 text-slate-400" />;
  }
}

function getFileTypeBadge(fileType: IngestionFileType | string) {
  const typeStr = typeof fileType === "string" ? fileType : String(fileType);
  const lower = typeStr.toLowerCase();

  if (lower.includes("slack")) {
    return {
      label: "Slack",
      bg: "bg-purple-100 dark:bg-purple-900/30",
      text: "text-purple-700 dark:text-purple-300",
    };
  }
  if (lower.includes("jira")) {
    return {
      label: "Jira",
      bg: "bg-blue-100 dark:bg-blue-900/30",
      text: "text-blue-700 dark:text-blue-300",
    };
  }
  if (lower.includes("drive") || lower.includes("document")) {
    return {
      label: "Drive",
      bg: "bg-amber-100 dark:bg-amber-900/30",
      text: "text-amber-700 dark:text-amber-300",
    };
  }
  return {
    label: "File",
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-700 dark:text-slate-300",
  };
}

function getProgressColor(status: IngestionFileStatus | string): string {
  switch (status) {
    case IngestionFileStatus.COMPLETED:
    case "completed":
      return "bg-green-500";
    case IngestionFileStatus.FAILED:
    case "failed":
      return "bg-red-500";
    case IngestionFileStatus.PROCESSING:
    case "processing":
      return "bg-teal-500";
    case IngestionFileStatus.SKIPPED:
    case "skipped":
      return "bg-slate-400";
    default:
      return "bg-slate-300 dark:bg-slate-600";
  }
}

function computeFileProgress(file: IngestionFileResult): number {
  const status = file.status;
  if (
    status === IngestionFileStatus.COMPLETED ||
    status === ("completed" as IngestionFileStatus)
  ) {
    return 100;
  }
  if (
    status === IngestionFileStatus.FAILED ||
    status === ("failed" as IngestionFileStatus)
  ) {
    return 100;
  }
  if (
    status === IngestionFileStatus.SKIPPED ||
    status === ("skipped" as IngestionFileStatus)
  ) {
    return 100;
  }
  if (
    status === IngestionFileStatus.PROCESSING ||
    status === ("processing" as IngestionFileStatus)
  ) {
    // Estimate progress from records if available
    if (file.records_processed > 0) {
      return Math.min(90, file.records_processed);
    }
    return 50;
  }
  return 0;
}

function FileRow({ file }: { file: IngestionFileResult }) {
  const typeBadge = getFileTypeBadge(file.file_type);
  const progress = computeFileProgress(file);
  const progressColor = getProgressColor(file.status);
  const statusIcon = getFileStatusIcon(file.status);

  return (
    <div className="rounded-lg border border-slate-100 bg-white px-4 py-3 dark:border-slate-700/50 dark:bg-surface-dark-card">
      <div className="flex items-center gap-3">
        <FileText className="h-4.5 w-4.5 shrink-0 text-slate-400" />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
              {file.filename}
            </span>
            <span
              className={cn(
                "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-2xs font-medium",
                typeBadge.bg,
                typeBadge.text,
              )}
            >
              {typeBadge.label}
            </span>
          </div>

          {/* Progress bar */}
          <div className="mt-2 flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500 ease-out",
                  progressColor,
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="shrink-0 text-2xs text-slate-400">
              {progress}%
            </span>
          </div>

          {/* Stats row */}
          {(file.records_processed > 0 || file.records_skipped > 0) && (
            <div className="mt-1 flex gap-3 text-2xs text-slate-500 dark:text-slate-400">
              <span>{file.records_processed} records processed</span>
              {file.records_skipped > 0 && (
                <span>{file.records_skipped} skipped</span>
              )}
            </div>
          )}

          {/* Error message */}
          {file.error_message && (
            <p className="mt-1 text-2xs text-red-500 dark:text-red-400">
              {file.error_message}
            </p>
          )}
        </div>

        {statusIcon}
      </div>
    </div>
  );
}

export function UploadProgress({ job, className }: UploadProgressProps) {
  const completedCount = job.files.filter(
    (f) =>
      f.status === IngestionFileStatus.COMPLETED ||
      f.status === ("completed" as IngestionFileStatus),
  ).length;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Overall progress header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {job.status === IngestionFileStatus.PROCESSING ||
          job.status === ("processing" as typeof job.status) ? (
            <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
          ) : job.status === ("completed" as typeof job.status) ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : job.status === ("failed" as typeof job.status) ? (
            <XCircle className="h-4 w-4 text-red-500" />
          ) : (
            <Clock className="h-4 w-4 text-slate-400" />
          )}
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Processing files
          </span>
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {completedCount} / {job.files.length} complete
        </span>
      </div>

      {/* File list */}
      <div className="space-y-2">
        {job.files.map((file, index) => (
          <FileRow key={`${file.filename}-${index}`} file={file} />
        ))}
      </div>
    </div>
  );
}
