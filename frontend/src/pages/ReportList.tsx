import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileText,
  Plus,
  Download,
  Eye,
  Trash2,
  Loader2,
  AlertCircle,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { useReportStore } from "@/stores/reportStore";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";
import type { ReportSpec } from "@/types";

/* ================================================================== */
/*  Report type badge                                                  */
/* ================================================================== */

const typeStyles: Record<string, string> = {
  project_status:
    "bg-chief-100 text-chief-700 dark:bg-chief-900/40 dark:text-chief-300",
  sprint_review:
    "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
  risk_assessment:
    "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  team_summary:
    "bg-navy-100 text-navy-700 dark:bg-navy-900/40 dark:text-navy-300",
  custom:
    "bg-warm-100 text-warm-700 dark:bg-warm-900/40 dark:text-warm-300",
};

const typeLabels: Record<string, string> = {
  project_status: "Project Status",
  sprint_review: "Sprint Review",
  risk_assessment: "Risk Assessment",
  team_summary: "Team Summary",
  custom: "Custom",
};

/* ================================================================== */
/*  Confirm Dialog                                                     */
/* ================================================================== */

function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-soft-lg dark:bg-surface-dark-card">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
          {title}
        </h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {message}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onCancel} className="btn-ghost">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="btn-destructive"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Report List Page                                                   */
/* ================================================================== */

export function ReportList() {
  const navigate = useNavigate();
  const {
    reports,
    isGenerating,
    isExporting,
    error,
    fetchReports,
    exportPdf,
    deleteReport,
    clearError,
  } = useReportStore();

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleExport = async (reportId: string) => {
    await exportPdf(reportId);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteReport(deleteTarget);
    setDeleteTarget(null);
  };

  const handleGenerateReport = () => {
    // Opens the chat sidebar with a report generation prompt context.
    // In a full implementation this would dispatch an event or navigate
    // with a query parameter. For now, we navigate to the chat.
    navigate("/?chat=report");
  };

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-teal-600 dark:text-teal-400" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Reports
          </h1>
          {reports.length > 0 && (
            <span className="badge-neutral">{reports.length}</span>
          )}
        </div>
        <button
          onClick={handleGenerateReport}
          disabled={isGenerating}
          className="btn-primary"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <MessageSquare className="h-4 w-4" />
              Generate Report
            </>
          )}
        </button>
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
            <span className="sr-only">Dismiss</span>&times;
          </button>
        </div>
      )}

      {/* Empty state */}
      {reports.length === 0 && !isGenerating && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
            <Sparkles className="h-10 w-10 text-teal-600 dark:text-teal-400" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
            Generate your first report via conversation
          </h2>
          <p className="mb-6 max-w-md text-sm text-slate-500 dark:text-slate-400">
            Ask ChiefOps to create a project status report, sprint review,
            risk assessment, or any custom report. Reports are generated
            using AI and can be exported as PDF.
          </p>
          <button onClick={handleGenerateReport} className="btn-primary">
            <MessageSquare className="h-4 w-4" />
            Start a Conversation
          </button>
        </div>
      )}

      {/* Report table */}
      {reports.length > 0 && (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <th className="px-5 py-3">Title</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Scope</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {reports.map((report) => (
                <tr
                  key={report.report_id}
                  className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  <td className="px-5 py-3">
                    <Link
                      to={`/reports/${report.report_id}`}
                      className="font-medium text-slate-900 hover:text-teal-700 dark:text-white dark:hover:text-teal-400"
                    >
                      {report.title}
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={cn(
                        "badge text-2xs",
                        typeStyles[report.report_type] ?? typeStyles.custom,
                      )}
                    >
                      {typeLabels[report.report_type] ?? report.report_type}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-600 dark:text-slate-400">
                    {formatDate(report.created_at, "MMM d, yyyy")}
                  </td>
                  <td className="px-5 py-3 text-slate-600 dark:text-slate-400">
                    {report.project_id ? (
                      <Link
                        to={`/projects/${report.project_id}`}
                        className="text-teal-600 hover:underline dark:text-teal-400"
                      >
                        {report.project_id.slice(0, 8)}...
                      </Link>
                    ) : (
                      <span className="text-slate-400">Organization</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Link
                        to={`/reports/${report.report_id}`}
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
                        title="View"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                      <button
                        onClick={() => handleExport(report.report_id)}
                        disabled={isExporting}
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
                        title="Export PDF"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setDeleteTarget(report.report_id)}
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Report"
        message="Are you sure you want to delete this report? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
