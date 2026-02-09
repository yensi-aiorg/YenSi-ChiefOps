import { useEffect, useState, useCallback, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileUp,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ChevronDown,
  ChevronRight,
  FileText,
  AlertCircle,
  HardDrive,
} from "lucide-react";
import { useIngestionStore } from "@/stores/ingestionStore";
import { cn } from "@/lib/utils";
import { formatDate, formatNumber } from "@/lib/utils";
import type { IngestionJob } from "@/types";

/* ================================================================== */
/*  Status badge helper                                                */
/* ================================================================== */

const statusConfig: Record<
  string,
  { label: string; icon: React.ReactNode; className: string }
> = {
  pending: {
    label: "Pending",
    icon: <Clock className="h-3.5 w-3.5" />,
    className:
      "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  processing: {
    label: "Processing",
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    className:
      "bg-chief-100 text-chief-700 dark:bg-chief-900/40 dark:text-chief-300",
  },
  completed: {
    label: "Completed",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    className:
      "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  },
  failed: {
    label: "Failed",
    icon: <XCircle className="h-3.5 w-3.5" />,
    className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  },
  skipped: {
    label: "Skipped",
    icon: <AlertCircle className="h-3.5 w-3.5" />,
    className:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  },
};

function StatusBadge({ status }: { status: string }) {
  const defaultCfg = { label: status, icon: null, className: "" };
  const cfg = statusConfig[status] ?? statusConfig["pending"] ?? defaultCfg;
  return (
    <span className={cn("badge gap-1", cfg.className)}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

/* ================================================================== */
/*  DropZone                                                           */
/* ================================================================== */

function DropZoneArea({
  onFilesSelected,
  isUploading,
  uploadProgress,
}: {
  onFilesSelected: (files: File[]) => void;
  isUploading: boolean;
  uploadProgress: number;
}) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0 && !isUploading) {
        onFilesSelected(acceptedFiles);
      }
    },
    [onFilesSelected, isUploading],
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: {
        "application/json": [".json"],
        "application/zip": [".zip"],
        "text/csv": [".csv"],
        "text/plain": [".txt"],
      },
      multiple: true,
      disabled: isUploading,
    });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-200",
        isDragActive && !isDragReject
          ? "border-teal-400 bg-teal-50/50 dark:border-teal-500 dark:bg-teal-900/20"
          : isDragReject
            ? "border-red-400 bg-red-50/50 dark:border-red-500 dark:bg-red-900/20"
            : "border-slate-300 bg-white hover:border-teal-400 hover:bg-slate-50 dark:border-slate-600 dark:bg-surface-dark-card dark:hover:border-teal-600 dark:hover:bg-surface-dark-muted",
        isUploading && "pointer-events-none opacity-60",
      )}
    >
      <input {...getInputProps()} />

      {isUploading ? (
        <div className="space-y-4">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-teal-500" />
          <div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white">
              Uploading files...
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {uploadProgress}% complete
            </p>
          </div>
          <div className="mx-auto h-2 w-64 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
            <div
              className="h-full rounded-full bg-teal-500 transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
            <FileUp className="h-8 w-8 text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white">
              {isDragActive
                ? "Drop files here"
                : "Drag & drop files to upload"}
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              or click to browse. Supports JSON, ZIP, CSV, and TXT files.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              "Slack Export (.zip/.json)",
              "Jira CSV (.csv)",
              "Drive Docs (.txt/.json)",
            ].map((label) => (
              <span key={label} className="badge-neutral text-2xs">
                {label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ================================================================== */
/*  Upload Progress (active job detail)                                */
/* ================================================================== */

function UploadProgressDetail({ job }: { job: IngestionJob }) {
  const totalFiles = job.files.length;
  const completedFiles = job.files.filter(
    (f) =>
      f.status === "completed" ||
      f.status === "failed" ||
      f.status === "skipped",
  ).length;
  const progressPct =
    totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0;

  return (
    <div className="card space-y-4 border-l-4 border-l-teal-500 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Loader2
            className={cn(
              "h-5 w-5",
              job.status === "processing"
                ? "animate-spin text-teal-500"
                : job.status === "completed"
                  ? "text-green-500"
                  : "text-red-500",
            )}
          />
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Active Ingestion Job
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Job ID: {job.job_id.slice(0, 8)}...
            </p>
          </div>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Progress bar */}
      <div>
        <div className="mb-1 flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>
            {completedFiles} / {totalFiles} files processed
          </span>
          <span>{progressPct}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
          <div
            className="h-full rounded-full bg-teal-500 transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Per-file details */}
      <div className="space-y-2">
        {job.files.map((file, idx) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const raw = file as any;
          const recordsProcessed = raw.records_processed ?? null;
          const recordsSkipped = raw.records_skipped ?? 0;
          const fileStatus = raw.status ?? "";
          const sizeBytes = raw.size_bytes ?? null;

          return (
            <div
              key={idx}
              className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50"
            >
              <FileText className="h-4 w-4 flex-shrink-0 text-slate-400" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-300">
                  {file.filename}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {recordsProcessed != null
                    ? `${formatNumber(recordsProcessed)} records`
                    : sizeBytes != null
                      ? `${formatNumber(sizeBytes)} bytes`
                      : ""}
                  {recordsSkipped > 0 &&
                    ` (${formatNumber(recordsSkipped)} skipped)`}
                </p>
              </div>
              {fileStatus && <StatusBadge status={fileStatus} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Ingestion Summary (post-completion)                                */
/* ================================================================== */

function IngestionSummary({ job }: { job: IngestionJob }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const raw = job as any;
  const totalRecords = raw.total_records ?? 0;
  const errorCount = raw.error_count ?? 0;
  const files = Array.isArray(job.files) ? job.files : [];
  const fileCount = files.length;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const completedFiles = files.filter(
    (f: any) => f.status === "completed",
  ).length;

  return (
    <div className="card space-y-4 border-l-4 border-l-green-500 p-5">
      <div className="flex items-center gap-3">
        <CheckCircle2 className="h-5 w-5 text-green-500" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
          Ingestion Complete
        </h3>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Files</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">
            {completedFiles}/{fileCount}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Records</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">
            {formatNumber(totalRecords)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Errors</p>
          <p
            className={cn(
              "text-lg font-bold",
              errorCount > 0
                ? "text-red-600 dark:text-red-400"
                : "text-green-600 dark:text-green-400",
            )}
          >
            {errorCount}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400">Duration</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">
            {job.started_at && job.completed_at
              ? `${Math.round(
                  (new Date(job.completed_at).getTime() -
                    new Date(job.started_at).getTime()) /
                    1000,
                )}s`
              : "--"}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Job Row (expandable)                                               */
/* ================================================================== */

function JobRow({ job }: { job: IngestionJob }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="cursor-pointer border-b border-slate-100 transition-colors hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50"
      >
        <td className="px-5 py-3">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronRight className="h-4 w-4 text-slate-400" />
            )}
            <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
              {job.job_id.slice(0, 12)}...
            </span>
          </div>
        </td>
        <td className="px-5 py-3 text-sm text-slate-600 dark:text-slate-400">
          {formatDate(job.created_at, "MMM d, yyyy HH:mm")}
        </td>
        <td className="px-5 py-3 text-center text-sm tabular-nums text-slate-700 dark:text-slate-300">
          {job.files.length}
        </td>
        <td className="px-5 py-3 text-center text-sm tabular-nums text-slate-700 dark:text-slate-300">
          {formatNumber(job.total_records)}
        </td>
        <td className="px-5 py-3">
          <StatusBadge status={job.status} />
        </td>
      </tr>
      {expanded && (
        <tr>
          <td
            colSpan={5}
            className="border-b border-slate-100 px-8 pb-4 pt-2 dark:border-slate-800"
          >
            <div className="space-y-2">
              {job.files.map((file, idx) => {
                // Backend FileInfo may return extra fields (file_type, records_processed, etc.)
                // or only basics (filename, size_bytes, content_type). Safely handle both.
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const raw = file as any;
                const fileType = raw.file_type ?? raw.content_type ?? "";
                const recordsProcessed = raw.records_processed ?? null;
                const recordsSkipped = raw.records_skipped ?? 0;
                const errorMessage = raw.error_message ?? null;
                const fileStatus = raw.status ?? "";
                const sizeBytes = raw.size_bytes ?? null;

                return (
                  <div
                    key={idx}
                    className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50"
                  >
                    <FileText className="h-4 w-4 flex-shrink-0 text-slate-400" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-slate-700 dark:text-slate-300">
                        {file.filename}
                      </p>
                      <div className="flex gap-3 text-xs text-slate-500 dark:text-slate-400">
                        {fileType && (
                          <span>
                            Type: {fileType.replace(/_/g, " ")}
                          </span>
                        )}
                        {recordsProcessed != null && (
                          <span>
                            {formatNumber(recordsProcessed)} records
                          </span>
                        )}
                        {sizeBytes != null && recordsProcessed == null && (
                          <span>
                            {formatNumber(sizeBytes)} bytes
                          </span>
                        )}
                        {recordsSkipped > 0 && (
                          <span>
                            {formatNumber(recordsSkipped)} skipped
                          </span>
                        )}
                      </div>
                      {errorMessage && (
                        <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                          {errorMessage}
                        </p>
                      )}
                    </div>
                    {fileStatus && <StatusBadge status={fileStatus} />}
                  </div>
                );
              })}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/* ================================================================== */
/*  Data Upload Page                                                   */
/* ================================================================== */

export function DataUpload() {
  const {
    jobs,
    activeJobId,
    uploadProgress,
    isUploading,
    error,
    fetchJobs,
    fetchJob,
    uploadFiles,
    clearError,
  } = useIngestionStore();

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Poll the active job while it's in a non-terminal status.
  useEffect(() => {
    if (!activeJobId) return;
    const activeJob = jobs.find((j) => j.job_id === activeJobId);
    const TERMINAL = new Set(["completed", "failed", "cancelled"]);
    if (activeJob && TERMINAL.has(activeJob.status)) return;

    const poll = setInterval(() => {
      fetchJob(activeJobId).catch(() => {
        // Swallow network errors — keep retrying.
      });
    }, 3000);

    return () => clearInterval(poll);
  }, [activeJobId, jobs, fetchJob]);

  // Derive the active job object from the list
  const activeJob = useMemo(
    () => (activeJobId ? jobs.find((j) => j.job_id === activeJobId) ?? null : null),
    [activeJobId, jobs],
  );

  // Compute aggregate upload progress from the Map
  const aggregateProgress = useMemo(() => {
    if (uploadProgress.size === 0) return 0;
    let sum = 0;
    uploadProgress.forEach((v) => {
      sum += v;
    });
    return Math.round(sum / uploadProgress.size);
  }, [uploadProgress]);

  const handleFilesSelected = useCallback(
    (files: File[]) => {
      uploadFiles(files);
    },
    [uploadFiles],
  );

  const showActiveProgress =
    activeJob &&
    (activeJob.status === "processing" || activeJob.status === "pending");
  const showCompletionSummary = activeJob && activeJob.status === "completed";

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Upload className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Upload Data
        </h1>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={clearError}
            className="rounded p-1 hover:bg-red-100 dark:hover:bg-red-900/50"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Drop zone */}
      <DropZoneArea
        onFilesSelected={handleFilesSelected}
        isUploading={isUploading}
        uploadProgress={aggregateProgress}
      />

      {/* Active job progress */}
      {showActiveProgress && <UploadProgressDetail job={activeJob} />}

      {/* Completion summary */}
      {showCompletionSummary && <IngestionSummary job={activeJob} />}

      {/* Ingestion history */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
            <HardDrive className="h-5 w-5 text-teal-500" />
            Ingestion History
          </h2>
          {jobs.length > 0 && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {jobs.length} job{jobs.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Loading skeleton */}
        {jobs.length === 0 && !error && (
          <div className="card flex flex-col items-center py-12 text-center">
            <HardDrive className="mb-3 h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
              No ingestion history yet
            </p>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
              Upload your first data files to get started.
            </p>
          </div>
        )}

        {/* Job table */}
        {jobs.length > 0 && (
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="px-5 py-3">Job ID</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3 text-center">Files</th>
                  <th className="px-5 py-3 text-center">Records</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <JobRow key={job.job_id} job={job} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
