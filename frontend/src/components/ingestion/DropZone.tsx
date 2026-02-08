import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  FileSpreadsheet,
  FileArchive,
  FileCode,
  File,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  DropZone – drag-and-drop file upload area                          */
/* ------------------------------------------------------------------ */

interface DropZoneProps {
  onFilesAccepted: (files: File[]) => void;
  disabled?: boolean;
  className?: string;
}

const ACCEPTED_TYPES: Record<string, string[]> = {
  "application/zip": [".zip"],
  "application/x-zip-compressed": [".zip"],
  "text/csv": [".csv"],
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
    ".docx",
  ],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [
    ".pptx",
  ],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
    ".xlsx",
  ],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
  "text/html": [".html"],
  "application/json": [".json"],
};

function getFileIcon(filename: string): React.ComponentType<{ className?: string }> {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "zip":
      return FileArchive;
    case "csv":
    case "xlsx":
      return FileSpreadsheet;
    case "pdf":
    case "docx":
    case "pptx":
      return FileText;
    case "json":
    case "html":
    case "md":
      return FileCode;
    default:
      return File;
  }
}

function getFileTypeColor(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "zip":
      return "text-amber-500";
    case "csv":
    case "xlsx":
      return "text-green-500";
    case "pdf":
      return "text-red-500";
    case "docx":
    case "pptx":
      return "text-blue-500";
    case "json":
      return "text-purple-500";
    case "html":
    case "md":
      return "text-teal-500";
    default:
      return "text-slate-400";
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DropZone({
  onFilesAccepted,
  disabled = false,
  className,
}: DropZoneProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setSelectedFiles((prev) => {
        const combined = [...prev, ...acceptedFiles];
        // Deduplicate by name
        const seen = new Set<string>();
        return combined.filter((f) => {
          if (seen.has(f.name)) return false;
          seen.add(f.name);
          return true;
        });
      });
    },
    [],
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: ACCEPTED_TYPES,
      disabled,
      multiple: true,
    });

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = () => {
    if (selectedFiles.length > 0) {
      onFilesAccepted(selectedFiles);
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Drop zone area */}
      <div
        {...getRootProps()}
        className={cn(
          "relative cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-200",
          isDragActive && !isDragReject
            ? "border-teal-400 bg-teal-50/50 dark:border-teal-500 dark:bg-teal-900/10"
            : isDragReject
              ? "border-red-400 bg-red-50/50 dark:border-red-500 dark:bg-red-900/10"
              : "border-slate-300 bg-slate-50/50 hover:border-teal-300 hover:bg-teal-50/30 dark:border-slate-600 dark:bg-slate-800/50 dark:hover:border-teal-600",
          disabled && "pointer-events-none opacity-50",
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-3">
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-2xl transition-colors",
              isDragActive
                ? "bg-teal-100 dark:bg-teal-900/40"
                : "bg-slate-100 dark:bg-slate-800",
            )}
          >
            <Upload
              className={cn(
                "h-7 w-7 transition-colors",
                isDragActive
                  ? "text-teal-600 dark:text-teal-400"
                  : "text-slate-400 dark:text-slate-500",
              )}
            />
          </div>

          {isDragActive && !isDragReject ? (
            <div>
              <p className="text-sm font-semibold text-teal-700 dark:text-teal-300">
                Drop files here
              </p>
              <p className="mt-1 text-xs text-teal-600 dark:text-teal-400">
                Release to add files to the upload queue
              </p>
            </div>
          ) : isDragReject ? (
            <div>
              <p className="text-sm font-semibold text-red-700 dark:text-red-400">
                Unsupported file type
              </p>
              <p className="mt-1 text-xs text-red-600 dark:text-red-300">
                Please use ZIP, CSV, PDF, DOCX, PPTX, XLSX, TXT, MD, HTML, or JSON files
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                Drag and drop your files here
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                or click to browse. Supports ZIP, CSV, PDF, DOCX, PPTX, XLSX, TXT, MD, HTML, JSON
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Selected files list */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""} selected
            </h4>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-xs text-slate-400 hover:text-red-500 dark:hover:text-red-400"
            >
              Clear all
            </button>
          </div>

          <div className="max-h-52 space-y-1.5 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-surface-dark-card">
            {selectedFiles.map((file, index) => {
              const Icon = getFileIcon(file.name);
              const colorClass = getFileTypeColor(file.name);
              const ext = file.name.split(".").pop()?.toUpperCase() ?? "";

              return (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <Icon className={cn("h-5 w-5 shrink-0", colorClass)} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
                      {file.name}
                    </p>
                    <p className="text-2xs text-slate-400">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                  <span className="badge-neutral shrink-0 text-2xs uppercase">
                    {ext}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="shrink-0 rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-red-500 dark:hover:bg-slate-700 dark:hover:text-red-400"
                    aria-label={`Remove ${file.name}`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>

          <button
            onClick={handleUpload}
            disabled={disabled}
            className="btn-primary w-full"
          >
            <Upload className="h-4 w-4" />
            Upload {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""}
          </button>
        </div>
      )}
    </div>
  );
}
