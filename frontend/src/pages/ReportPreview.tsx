import { useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  FileText,
  ArrowLeft,
  Download,
  MessageSquare,
  Loader2,
  AlertCircle,
  Calendar,
} from "lucide-react";
import { useReportStore } from "@/stores/reportStore";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";

/* ================================================================== */
/*  Report type helpers                                                */
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
/*  Loading skeleton                                                   */
/* ================================================================== */

function ReportSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="skeleton h-7 w-56" />
        <div className="skeleton h-6 w-24 rounded-full" />
      </div>
      <div className="card space-y-4 p-8">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-5/6" />
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-2/3" />
        <div className="skeleton h-32 w-full" />
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Report Preview Page                                                */
/* ================================================================== */

export function ReportPreview() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const {
    activeReport: report,
    isExporting,
    error,
    fetchReport,
    exportPdf,
  } = useReportStore();

  useEffect(() => {
    if (reportId) {
      fetchReport(reportId);
    }
  }, [reportId, fetchReport]);

  const handleExportPdf = async () => {
    if (!reportId) return;
    await exportPdf(reportId);
  };

  const handleEditViaChat = () => {
    // Navigate to dashboard with chat sidebar opened with report context
    navigate(`/?chat=edit-report&reportId=${reportId}`);
  };

  // Loading
  if (!report && !error) {
    return (
      <div className="animate-fade-in">
        <ReportSkeleton />
      </div>
    );
  }

  // Error
  if (error && !report) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <AlertCircle className="mb-4 h-12 w-12 text-red-400" />
        <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
          Failed to load report
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          {error}
        </p>
        <Link to="/reports" className="btn-secondary">
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </Link>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          to="/reports"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </Link>

        <div className="flex items-center gap-2">
          <button onClick={handleEditViaChat} className="btn-secondary">
            <MessageSquare className="h-4 w-4" />
            Edit via Chat
          </button>
          <button
            onClick={handleExportPdf}
            disabled={isExporting}
            className="btn-primary"
          >
            {isExporting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Export PDF
              </>
            )}
          </button>
        </div>
      </div>

      {/* Report header */}
      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <FileText className="h-5 w-5 text-teal-500" />
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                {report.title}
              </h1>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span
                className={cn(
                  "badge text-2xs",
                  typeStyles[report.report_type] ?? typeStyles.custom,
                )}
              >
                {typeLabels[report.report_type] ?? report.report_type}
              </span>
              <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                <Calendar className="h-3.5 w-3.5" />
                {formatDate(report.created_at, "MMMM d, yyyy")}
              </span>
              {report.project_id && (
                <Link
                  to={`/projects/${report.project_id}`}
                  className="text-xs text-teal-600 hover:underline dark:text-teal-400"
                >
                  View Project
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Report body (rendered markdown) */}
      <div className="card p-8">
        <article className="prose prose-slate dark:prose-invert mx-auto max-w-none prose-headings:text-slate-900 prose-p:text-slate-600 prose-a:text-teal-600 prose-strong:text-slate-900 dark:prose-headings:text-white dark:prose-p:text-slate-300 dark:prose-a:text-teal-400 dark:prose-strong:text-white">
          <ReactMarkdown>{report.content}</ReactMarkdown>
        </article>
      </div>

      {/* Report sections if available */}
      {report.sections && report.sections.length > 0 && (
        <div className="space-y-4">
          {report.sections.map((section, idx) => (
            <div key={idx} className="card p-6">
              <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">
                {section.heading}
              </h2>
              <div className="prose prose-sm prose-slate dark:prose-invert max-w-none">
                <ReactMarkdown>{section.body}</ReactMarkdown>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
