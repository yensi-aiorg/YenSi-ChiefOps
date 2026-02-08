import { useState, useEffect } from "react";
import {
  X,
  Shield,
  MessageSquare,
  ListTodo,
  FolderOpen,
  FileText,
  Hash,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  ChunkAuditViewer – modal showing chunks sent to AI for a request   */
/* ------------------------------------------------------------------ */

interface AuditChunk {
  chunk_id: string;
  source_type: string;
  source_label: string;
  preview_text: string;
  token_count: number;
  relevance_score?: number;
}

interface ChunkAuditData {
  request_id: string;
  query: string;
  chunks: AuditChunk[];
  total_tokens: number;
  timestamp: string;
}

interface ChunkAuditViewerProps {
  requestId: string;
  isOpen: boolean;
  onClose: () => void;
}

function getSourceIcon(sourceType: string) {
  const lower = sourceType.toLowerCase();
  if (lower.includes("slack")) return MessageSquare;
  if (lower.includes("jira")) return ListTodo;
  if (lower.includes("drive") || lower.includes("gdrive")) return FolderOpen;
  return FileText;
}

function getSourceColor(sourceType: string): {
  bg: string;
  text: string;
  border: string;
} {
  const lower = sourceType.toLowerCase();
  if (lower.includes("slack")) {
    return {
      bg: "bg-purple-50 dark:bg-purple-900/20",
      text: "text-purple-700 dark:text-purple-300",
      border: "border-purple-200 dark:border-purple-700",
    };
  }
  if (lower.includes("jira")) {
    return {
      bg: "bg-blue-50 dark:bg-blue-900/20",
      text: "text-blue-700 dark:text-blue-300",
      border: "border-blue-200 dark:border-blue-700",
    };
  }
  if (lower.includes("drive") || lower.includes("gdrive")) {
    return {
      bg: "bg-amber-50 dark:bg-amber-900/20",
      text: "text-amber-700 dark:text-amber-300",
      border: "border-amber-200 dark:border-amber-700",
    };
  }
  return {
    bg: "bg-slate-50 dark:bg-slate-800",
    text: "text-slate-700 dark:text-slate-300",
    border: "border-slate-200 dark:border-slate-600",
  };
}

export function ChunkAuditViewer({
  requestId,
  isOpen,
  onClose,
}: ChunkAuditViewerProps) {
  const [auditData, setAuditData] = useState<ChunkAuditData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !requestId) return;

    setIsLoading(true);
    setError(null);

    api
      .get<ChunkAuditData | { data: ChunkAuditData }>(
        `/v1/privacy/audit/${requestId}`,
      )
      .then((res) => {
        const data =
          "data" in res.data && (res.data as { data: ChunkAuditData }).data
            ? (res.data as { data: ChunkAuditData }).data
            : (res.data as ChunkAuditData);
        setAuditData(data);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to load audit data",
        );
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isOpen, requestId]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-4 z-50 m-auto flex max-h-[90vh] max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft-lg dark:border-slate-700 dark:bg-surface-dark sm:inset-x-auto sm:inset-y-8 sm:w-full">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 dark:bg-teal-900/40">
              <Shield className="h-4.5 w-4.5 text-teal-600 dark:text-teal-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                Chunk Audit Viewer
              </h2>
              <p className="text-2xs text-slate-500 dark:text-slate-400">
                Data sent to AI for request{" "}
                <code className="rounded bg-slate-100 px-1 font-mono dark:bg-slate-800">
                  {requestId}
                </code>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
            aria-label="Close audit viewer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
              <span className="ml-2 text-sm text-slate-500">
                Loading audit data...
              </span>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          {auditData && !isLoading && (
            <div className="space-y-4">
              {/* Query context */}
              <div className="rounded-lg bg-slate-50 px-4 py-3 dark:bg-slate-800">
                <p className="text-2xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  User Query
                </p>
                <p className="mt-1 text-sm text-slate-800 dark:text-slate-200">
                  {auditData.query}
                </p>
              </div>

              {/* Summary */}
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                  <FileText className="h-3.5 w-3.5" />
                  <span>
                    {auditData.chunks.length} chunk{auditData.chunks.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                  <Hash className="h-3.5 w-3.5" />
                  <span>{auditData.total_tokens.toLocaleString()} tokens</span>
                </div>
              </div>

              {/* Chunk list */}
              <div className="space-y-3">
                {auditData.chunks.map((chunk, index) => {
                  const Icon = getSourceIcon(chunk.source_type);
                  const colors = getSourceColor(chunk.source_type);

                  return (
                    <div
                      key={chunk.chunk_id || `chunk-${index}`}
                      className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700"
                    >
                      {/* Chunk header */}
                      <div className="flex items-center gap-3 border-b border-slate-100 bg-slate-50/50 px-4 py-2 dark:border-slate-700 dark:bg-slate-800/50">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-2xs font-medium",
                            colors.bg,
                            colors.text,
                            colors.border,
                          )}
                        >
                          <Icon className="h-3 w-3" />
                          {chunk.source_label}
                        </span>

                        <div className="flex flex-1 items-center justify-end gap-3 text-2xs text-slate-400 dark:text-slate-500">
                          <span>{chunk.token_count} tokens</span>
                          {chunk.relevance_score !== undefined && (
                            <span>
                              Relevance: {(chunk.relevance_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Chunk preview text */}
                      <div className="px-4 py-3">
                        <p className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                          {chunk.preview_text}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {auditData.chunks.length === 0 && (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <Shield className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    No data chunks were sent for this request.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3 dark:border-slate-700">
          <p className="text-2xs text-slate-400 dark:text-slate-500">
            Data transparency powered by ChiefOps Privacy Layer
          </p>
          <button onClick={onClose} className="btn-secondary text-sm">
            Close
          </button>
        </div>
      </div>
    </>
  );
}
