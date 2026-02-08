import { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import type { ReportSection as ReportSectionType } from "@/types";
import { SectionType } from "@/types";
import { cn, formatNumber } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  ReportSection – polymorphic section renderer                       */
/* ------------------------------------------------------------------ */

interface ReportSectionProps {
  section: ReportSectionType;
  className?: string;
}

/** Helper to safely extract typed content from the generic content record. */
function getContent<T>(content: Record<string, unknown>, key: string): T | undefined {
  return content[key] as T | undefined;
}

/* -- Narrative Section --------------------------------------------- */

function NarrativeSection({ content }: { content: Record<string, unknown> }) {
  const text =
    (getContent<string>(content, "text") ??
    getContent<string>(content, "body") ??
    getContent<string>(content, "narrative") ??
    (typeof content === "string" ? (content as string) : "")) || "";

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}

/* -- Metrics Grid Section ------------------------------------------ */

interface MetricGridItem {
  label: string;
  value: string | number;
  change?: number;
  unit?: string;
}

function MetricsGridSection({ content }: { content: Record<string, unknown> }) {
  const metrics =
    getContent<MetricGridItem[]>(content, "metrics") ??
    getContent<MetricGridItem[]>(content, "items") ??
    [];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {metrics.map((m, i) => (
        <div
          key={`${m.label}-${i}`}
          className="rounded-xl border border-slate-100 bg-white px-4 py-3 dark:border-slate-700 dark:bg-surface-dark-card"
        >
          <p className="text-2xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {m.label}
          </p>
          <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white">
            {typeof m.value === "number" ? formatNumber(m.value) : m.value}
            {m.unit && (
              <span className="ml-0.5 text-sm font-normal text-slate-400">
                {m.unit}
              </span>
            )}
          </p>
          {m.change !== undefined && m.change !== null && (
            <p
              className={cn(
                "mt-0.5 text-2xs font-medium",
                m.change > 0
                  ? "text-green-600 dark:text-green-400"
                  : m.change < 0
                    ? "text-red-600 dark:text-red-400"
                    : "text-slate-400",
              )}
            >
              {m.change > 0 ? "+" : ""}
              {m.change}%
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

/* -- Chart Section ------------------------------------------------- */

function ChartSection({ content }: { content: Record<string, unknown> }) {
  // Placeholder for ECharts integration - renders chart config summary
  const chartType = getContent<string>(content, "chart_type") ?? "bar";

  return (
    <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800/50">
      <div className="text-center">
        <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-teal-100 dark:bg-teal-900/40">
          <ArrowUpDown className="h-5 w-5 text-teal-600 dark:text-teal-400" />
        </div>
        <p className="text-sm font-medium capitalize text-slate-600 dark:text-slate-300">
          {chartType} Chart
        </p>
        <p className="text-2xs text-slate-400">
          Chart renders with widget system
        </p>
      </div>
    </div>
  );
}

/* -- Table Section ------------------------------------------------- */

interface TableColumnDef {
  key: string;
  label: string;
  sortable?: boolean;
}

function TableSection({ content }: { content: Record<string, unknown> }) {
  const columns =
    getContent<TableColumnDef[]>(content, "columns") ?? [];
  const rows =
    getContent<Record<string, unknown>[]>(content, "rows") ??
    getContent<Record<string, unknown>[]>(content, "data") ??
    [];

  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    return [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === bv) return 0;
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      const cmp = String(av).localeCompare(String(bv), undefined, {
        numeric: true,
      });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  if (columns.length === 0 && rows.length === 0) {
    return (
      <p className="text-sm text-slate-400 dark:text-slate-500">
        No table data available.
      </p>
    );
  }

  // Auto-detect columns from rows if not provided
  const effectiveColumns =
    columns.length > 0
      ? columns
      : rows.length > 0
        ? Object.keys(rows[0]!).map((key) => ({
            key,
            label: key.replace(/_/g, " "),
            sortable: true,
          }))
        : [];

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
            {effectiveColumns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  "px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400",
                  col.sortable !== false && "cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200",
                )}
                onClick={() =>
                  col.sortable !== false && handleSort(col.key)
                }
              >
                <div className="flex items-center gap-1">
                  <span className="capitalize">{col.label}</span>
                  {col.sortable !== false && sortKey === col.key && (
                    sortDir === "asc" ? (
                      <ArrowUp className="h-3 w-3" />
                    ) : (
                      <ArrowDown className="h-3 w-3" />
                    )
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, ri) => (
            <tr
              key={ri}
              className="border-b border-slate-100 last:border-0 dark:border-slate-700/50"
            >
              {effectiveColumns.map((col) => (
                <td
                  key={col.key}
                  className="px-4 py-2.5 text-slate-700 dark:text-slate-300"
                >
                  {row[col.key] !== null && row[col.key] !== undefined
                    ? String(row[col.key])
                    : "-"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* -- Card List Section --------------------------------------------- */

interface CardItemDef {
  title: string;
  description?: string;
  severity?: string;
  status?: string;
}

function CardListSection({ content }: { content: Record<string, unknown> }) {
  const cards =
    getContent<CardItemDef[]>(content, "cards") ??
    getContent<CardItemDef[]>(content, "items") ??
    [];

  function getSeverityColor(severity?: string): string {
    switch (severity?.toLowerCase()) {
      case "critical":
        return "border-l-red-500";
      case "high":
        return "border-l-orange-500";
      case "medium":
        return "border-l-yellow-500";
      case "low":
        return "border-l-blue-500";
      default:
        return "border-l-slate-300 dark:border-l-slate-600";
    }
  }

  function getSeverityIcon(severity?: string) {
    switch (severity?.toLowerCase()) {
      case "critical":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "high":
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case "medium":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  }

  return (
    <div className="space-y-2">
      {cards.map((card, i) => (
        <div
          key={`card-${i}`}
          className={cn(
            "rounded-lg border border-slate-200 border-l-4 bg-white px-4 py-3 dark:border-slate-700 dark:bg-surface-dark-card",
            getSeverityColor(card.severity),
          )}
        >
          <div className="flex items-start gap-2">
            {getSeverityIcon(card.severity)}
            <div className="min-w-0 flex-1">
              <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                {card.title}
              </h4>
              {card.description && (
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  {card.description}
                </p>
              )}
            </div>
            {card.status && (
              <span className="badge-neutral shrink-0">{card.status}</span>
            )}
          </div>
        </div>
      ))}
      {cards.length === 0 && (
        <p className="text-sm text-slate-400">No items.</p>
      )}
    </div>
  );
}

/* -- Checklist Section --------------------------------------------- */

interface ChecklistItemDef {
  label: string;
  checked: boolean;
  notes?: string;
}

function ChecklistSection({ content }: { content: Record<string, unknown> }) {
  const items =
    getContent<ChecklistItemDef[]>(content, "items") ??
    getContent<ChecklistItemDef[]>(content, "checklist") ??
    [];

  return (
    <div className="space-y-1.5">
      {items.map((item, i) => (
        <div
          key={`check-${i}`}
          className="flex items-start gap-2.5 rounded-lg px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          {item.checked ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
          ) : (
            <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
          )}
          <div>
            <span
              className={cn(
                "text-sm",
                item.checked
                  ? "text-slate-700 dark:text-slate-300"
                  : "font-medium text-slate-900 dark:text-white",
              )}
            >
              {item.label}
            </span>
            {item.notes && (
              <p className="mt-0.5 text-2xs text-slate-400 dark:text-slate-500">
                {item.notes}
              </p>
            )}
          </div>
        </div>
      ))}
      {items.length === 0 && (
        <p className="text-sm text-slate-400">No checklist items.</p>
      )}
    </div>
  );
}

/* -- Main ReportSection Component ---------------------------------- */

export function ReportSection({ section, className }: ReportSectionProps) {
  const content = section.content ?? {};

  const renderContent = () => {
    switch (section.section_type) {
      case SectionType.NARRATIVE:
        return <NarrativeSection content={content} />;
      case SectionType.METRIC_GRID:
        return <MetricsGridSection content={content} />;
      case SectionType.CHART:
        return <ChartSection content={content} />;
      case SectionType.TABLE:
        return <TableSection content={content} />;
      case SectionType.LIST:
        return <CardListSection content={content} />;
      case SectionType.CHECKLIST:
        return <ChecklistSection content={content} />;
      default:
        // Fallback: try narrative rendering
        return <NarrativeSection content={content} />;
    }
  };

  return (
    <div className={cn("space-y-3", className)} id={`section-${section.section_id}`}>
      <h3 className="text-base font-semibold text-slate-900 dark:text-white">
        {section.title}
      </h3>
      {renderContent()}
    </div>
  );
}
