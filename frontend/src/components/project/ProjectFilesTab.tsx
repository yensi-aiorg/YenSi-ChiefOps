import { useEffect, useState } from "react";
import {
  FileText,
  FileSpreadsheet,
  FileCode,
  File,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  CloudOff,
  Cloud,
  Upload,
  NotebookPen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DropZone } from "@/components/ingestion/DropZone";
import { useProjectStore } from "@/stores/projectStore";
import type { ProjectFileInfo } from "@/types";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getFileIcon(
  filename: string,
): React.ComponentType<{ className?: string }> {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "xlsx":
      return FileSpreadsheet;
    case "pdf":
    case "docx":
      return FileText;
    case "json":
    case "md":
    case "txt":
      return FileCode;
    default:
      return File;
  }
}

function getFileTypeColor(fileType: string): string {
  switch (fileType) {
    case "slack_json":
      return "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400";
    case "jira_xlsx":
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400";
    case "documentation":
      return "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400";
    default:
      return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
  }
}

function getFileTypeLabel(fileType: string): string {
  switch (fileType) {
    case "slack_json":
      return "Slack";
    case "jira_xlsx":
      return "Jira";
    case "documentation":
      return "Doc";
    default:
      return fileType;
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case "completed":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Completed
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
          <XCircle className="h-3.5 w-3.5" />
          Failed
        </span>
      );
    case "skipped":
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-yellow-600 dark:text-yellow-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          Skipped
        </span>
      );
    default:
      return (
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {status}
        </span>
      );
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

/* ------------------------------------------------------------------ */
/*  File row                                                           */
/* ------------------------------------------------------------------ */

function FileRow({
  file,
  onDelete,
}: {
  file: ProjectFileInfo;
  onDelete: (fileId: string) => void;
}) {
  const Icon = getFileIcon(file.filename);

  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-surface-dark-card dark:hover:bg-slate-800/70">
      {/* File icon */}
      <Icon className="h-5 w-5 shrink-0 text-slate-400 dark:text-slate-500" />

      {/* Filename + error */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
          {file.filename}
        </p>
        {file.error_message && (
          <p className="truncate text-xs text-red-500 dark:text-red-400">
            {file.error_message}
          </p>
        )}
      </div>

      {/* Type badge */}
      <span
        className={cn(
          "shrink-0 rounded-full px-2.5 py-0.5 text-2xs font-medium",
          getFileTypeColor(file.file_type),
        )}
      >
        {getFileTypeLabel(file.file_type)}
      </span>

      {/* Size */}
      <span className="hidden shrink-0 text-xs text-slate-400 dark:text-slate-500 sm:inline">
        {formatFileSize(file.file_size)}
      </span>

      {/* Status */}
      <div className="shrink-0">{getStatusBadge(file.status)}</div>

      {/* Citex status */}
      <div className="shrink-0" title={file.citex_ingested ? "Indexed in Citex" : "Not indexed"}>
        {file.citex_ingested ? (
          <Cloud className="h-4 w-4 text-teal-500" />
        ) : (
          <CloudOff className="h-4 w-4 text-slate-300 dark:text-slate-600" />
        )}
      </div>

      {/* Date */}
      <span className="hidden shrink-0 text-xs text-slate-400 dark:text-slate-500 lg:inline">
        {formatDate(file.created_at)}
      </span>

      {/* Delete */}
      <button
        onClick={() => onDelete(file.file_id)}
        className="shrink-0 rounded p-1 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 dark:hover:text-red-400"
        aria-label={`Delete ${file.filename}`}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

interface ProjectFilesTabProps {
  projectId: string;
}

export function ProjectFilesTab({ projectId }: ProjectFilesTabProps) {
  const [noteTitle, setNoteTitle] = useState("Project Note");
  const [noteContent, setNoteContent] = useState("");
  const {
    projectFiles,
    isUploadingFiles,
    uploadError,
    isSubmittingNote,
    noteError,
    lastNoteResult,
    uploadProjectFiles,
    submitProjectNote,
    clearNoteStatus,
    fetchProjectFiles,
    deleteProjectFile,
  } = useProjectStore();

  useEffect(() => {
    fetchProjectFiles(projectId);
  }, [projectId, fetchProjectFiles]);

  const handleFilesAccepted = async (files: File[]) => {
    try {
      await uploadProjectFiles(projectId, files);
    } catch {
      // Error is set in store
    }
  };

  const handleSubmitNote = async () => {
    if (!noteContent.trim()) return;
    try {
      await submitProjectNote(projectId, {
        title: noteTitle.trim() || "Project Note",
        content: noteContent.trim(),
      });
      setNoteContent("");
    } catch {
      // Error is set in store
    }
  };

  const handleDelete = async (fileId: string) => {
    try {
      await deleteProjectFile(projectId, fileId);
    } catch {
      // Error is set in store
    }
  };

  return (
    <div className="space-y-6">
      {/* Context note section */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <NotebookPen className="h-4 w-4 text-teal-500" />
            Add Context Note
          </h3>
          {isSubmittingNote && (
            <div className="flex items-center gap-2 text-xs text-teal-600 dark:text-teal-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Processing...
            </div>
          )}
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400">
          Paste meeting transcripts, face-to-face updates, direction changes,
          or other narrative context for AI semantic analysis.
        </p>

        <div className="space-y-3">
          <input
            type="text"
            value={noteTitle}
            onChange={(e) => {
              setNoteTitle(e.target.value);
              if (noteError || lastNoteResult) clearNoteStatus();
            }}
            maxLength={300}
            placeholder="Note title (e.g. Weekly COO Meeting)"
            className="input w-full"
          />

          <textarea
            value={noteContent}
            onChange={(e) => {
              setNoteContent(e.target.value);
              if (noteError || lastNoteResult) clearNoteStatus();
            }}
            maxLength={100000}
            rows={8}
            placeholder="Paste your transcript or operational notes here..."
            className="input w-full resize-y"
          />

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 dark:text-slate-500">
              {noteContent.length.toLocaleString()} / 100,000 characters
            </span>
            <button
              onClick={handleSubmitNote}
              disabled={isSubmittingNote || !noteContent.trim()}
              className="btn-primary"
            >
              {isSubmittingNote ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                "Submit Note"
              )}
            </button>
          </div>
        </div>

        {lastNoteResult?.status === "completed" && (
          <div className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-400">
            Note processed. {lastNoteResult.insights_created} insight
            {lastNoteResult.insights_created === 1 ? "" : "s"} extracted.
          </div>
        )}

        {noteError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {noteError}
          </div>
        )}
      </div>

      {/* Upload section */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <Upload className="h-4 w-4 text-teal-500" />
            Upload Project Files
          </h3>
          {isUploadingFiles && (
            <div className="flex items-center gap-2 text-xs text-teal-600 dark:text-teal-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Uploading...
            </div>
          )}
        </div>

        <DropZone
          onFilesAccepted={handleFilesAccepted}
          disabled={isUploadingFiles}
        />

        <p className="text-xs text-slate-400 dark:text-slate-500">
          Supported: JSON (Slack exports), XLSX (Jira exports), PDF, DOCX, MD,
          TXT
        </p>

        {uploadError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {uploadError}
          </div>
        )}
      </div>

      {/* File list */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
            <FileText className="h-4 w-4 text-teal-500" />
            Uploaded Files
          </h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {projectFiles.length} file{projectFiles.length !== 1 ? "s" : ""}
          </span>
        </div>

        {projectFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800">
              <File className="h-6 w-6 text-slate-400 dark:text-slate-500" />
            </div>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
              No files uploaded yet
            </p>
            <p className="mt-1 max-w-xs text-xs text-slate-400 dark:text-slate-500">
              Upload Slack JSON exports, Jira XLSX spreadsheets, or
              documentation files to enrich this project's context for analysis.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {projectFiles.map((file) => (
              <FileRow
                key={file.file_id}
                file={file}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
