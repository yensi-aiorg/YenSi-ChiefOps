import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import type { ReportSpec } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface ReportState {
  reports: ReportSpec[];
  activeReport: ReportSpec | null;
  isGenerating: boolean;
  isExporting: boolean;
  error: string | null;
}

interface ReportActions {
  /** Generate a new report from a natural-language request. */
  generateReport: (message: string, projectId?: string) => Promise<void>;

  /** Fetch a paginated list of reports. */
  fetchReports: (skip?: number, limit?: number) => Promise<void>;

  /** Fetch a single report by ID. */
  fetchReport: (reportId: string) => Promise<void>;

  /** Edit an existing report by sending a free-text instruction. */
  editReport: (reportId: string, instruction: string) => Promise<void>;

  /** Export a report as PDF. Triggers a download in the browser. */
  exportPdf: (reportId: string) => Promise<void>;

  /** Delete a report. */
  deleteReport: (reportId: string) => Promise<void>;

  /** Set the active report in local state. */
  setActiveReport: (report: ReportSpec | null) => void;

  /** Clear the error state. */
  clearError: () => void;
}

type ReportStore = ReportState & ReportActions;

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useReportStore = create<ReportStore>()(
  devtools(
    (set) => ({
      // -- state --
      reports: [],
      activeReport: null,
      isGenerating: false,
      isExporting: false,
      error: null,

      // -- actions --

      generateReport: async (message, projectId?) => {
        set(
          { isGenerating: true, error: null },
          false,
          "generateReport/start",
        );
        try {
          const body: { message: string; project_id?: string } = { message };
          if (projectId) body.project_id = projectId;

          const { data } = await api.post<ReportSpec>(
            "/v1/reports/generate",
            body,
          );

          set(
            (s) => ({
              reports: [data, ...s.reports],
              activeReport: data,
              isGenerating: false,
            }),
            false,
            "generateReport/success",
          );
        } catch (err) {
          const errorMessage =
            err instanceof Error ? err.message : "Failed to generate report";
          set(
            { error: errorMessage, isGenerating: false },
            false,
            "generateReport/error",
          );
          throw err;
        }
      },

      fetchReports: async (skip = 0, limit = 20) => {
        set({ error: null }, false, "fetchReports/start");
        try {
          const { data } = await api.get<
            ReportSpec[] | { reports: ReportSpec[] }
          >("/v1/reports", {
            params: { skip, limit },
          });

          const reports = Array.isArray(data)
            ? data
            : (data as Record<string, unknown>).reports as ReportSpec[] ??
              (data as Record<string, unknown>).items as ReportSpec[] ??
              [];

          set({ reports }, false, "fetchReports/success");
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to fetch reports";
          set({ error: message }, false, "fetchReports/error");
          throw err;
        }
      },

      fetchReport: async (reportId) => {
        set({ error: null }, false, "fetchReport/start");
        try {
          const { data } = await api.get<ReportSpec>(
            `/v1/reports/${reportId}`,
          );

          set({ activeReport: data }, false, "fetchReport/success");
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch report details";
          set({ error: message }, false, "fetchReport/error");
          throw err;
        }
      },

      editReport: async (reportId, instruction) => {
        set(
          { isGenerating: true, error: null },
          false,
          "editReport/start",
        );
        try {
          const { data } = await api.post<ReportSpec>(
            `/v1/reports/${reportId}/edit`,
            { instruction },
          );

          set(
            (s) => ({
              reports: s.reports.map((r) =>
                r.report_id === reportId ? data : r,
              ),
              activeReport:
                s.activeReport?.report_id === reportId
                  ? data
                  : s.activeReport,
              isGenerating: false,
            }),
            false,
            "editReport/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to edit report";
          set(
            { error: message, isGenerating: false },
            false,
            "editReport/error",
          );
          throw err;
        }
      },

      exportPdf: async (reportId) => {
        set({ isExporting: true, error: null }, false, "exportPdf/start");
        try {
          const response = await api.get<Blob>(
            `/v1/reports/${reportId}/export/pdf`,
            { responseType: "blob" },
          );

          // Trigger browser download.
          const url = window.URL.createObjectURL(response.data);
          const link = document.createElement("a");
          link.href = url;

          // Try to extract filename from Content-Disposition header.
          const disposition = response.headers["content-disposition"] as
            | string
            | undefined;
          let filename = `report-${reportId}.pdf`;
          if (disposition) {
            const match = /filename="?([^";\n]+)"?/.exec(disposition);
            if (match?.[1]) {
              filename = match[1];
            }
          }

          link.setAttribute("download", filename);
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);

          set({ isExporting: false }, false, "exportPdf/success");
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to export PDF";
          set(
            { error: message, isExporting: false },
            false,
            "exportPdf/error",
          );
          throw err;
        }
      },

      deleteReport: async (reportId) => {
        set({ error: null }, false, "deleteReport/start");
        try {
          await api.delete(`/v1/reports/${reportId}`);

          set(
            (s) => ({
              reports: s.reports.filter((r) => r.report_id !== reportId),
              activeReport:
                s.activeReport?.report_id === reportId
                  ? null
                  : s.activeReport,
            }),
            false,
            "deleteReport/success",
          );
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to delete report";
          set({ error: message }, false, "deleteReport/error");
          throw err;
        }
      },

      setActiveReport: (report) => {
        set({ activeReport: report }, false, "setActiveReport");
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "ReportStore" },
  ),
);
