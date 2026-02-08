import { useState, useMemo, useCallback } from "react";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  width?: string;
  format?: "text" | "number" | "currency" | "percent" | "date";
}

export interface TableData {
  columns: TableColumn[];
  rows: Record<string, unknown>[];
}

export interface DataTableConfig {
  page_size?: number;
  page_size_options?: number[];
  show_search?: boolean;
  show_pagination?: boolean;
  striped?: boolean;
  compact?: boolean;
  highlight_hover?: boolean;
  sticky_header?: boolean;
  max_height?: string;
}

export interface DataTableProps {
  data: TableData;
  config?: DataTableConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type SortDir = "asc" | "desc" | null;

function formatCellValue(
  value: unknown,
  format?: string,
): string {
  if (value === null || value === undefined) return "-";

  switch (format) {
    case "number":
      return typeof value === "number"
        ? value.toLocaleString("en-US")
        : String(value);

    case "currency":
      return typeof value === "number"
        ? new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
          }).format(value)
        : String(value);

    case "percent":
      return typeof value === "number" ? `${value.toFixed(1)}%` : String(value);

    case "date":
      if (typeof value === "string") {
        try {
          return new Date(value).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          });
        } catch {
          return value;
        }
      }
      return String(value);

    default:
      return String(value);
  }
}

function matchesSearch(
  row: Record<string, unknown>,
  query: string,
  columns: TableColumn[],
): boolean {
  const lower = query.toLowerCase();
  return columns.some((col) => {
    const val = row[col.key];
    if (val === null || val === undefined) return false;
    return String(val).toLowerCase().includes(lower);
  });
}

function compareValues(a: unknown, b: unknown, format?: string): number {
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;

  if (format === "number" || format === "currency" || format === "percent") {
    return (Number(a) || 0) - (Number(b) || 0);
  }

  if (format === "date") {
    const da = new Date(String(a)).getTime();
    const db = new Date(String(b)).getTime();
    if (!isNaN(da) && !isNaN(db)) return da - db;
  }

  return String(a).localeCompare(String(b));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DataTable({ data, config = {} }: DataTableProps) {
  const {
    page_size: initialPageSize = 10,
    page_size_options = [10, 25, 50],
    show_search = true,
    show_pagination = true,
    striped = true,
    compact = false,
    highlight_hover = true,
    sticky_header = true,
    max_height,
  } = config;

  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const { columns, rows } = data;

  // Handle sort toggle
  const handleSort = useCallback(
    (key: string) => {
      if (sortKey === key) {
        if (sortDir === "asc") setSortDir("desc");
        else if (sortDir === "desc") {
          setSortKey(null);
          setSortDir(null);
        }
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
      setPage(0);
    },
    [sortKey, sortDir],
  );

  // Filter & sort
  const processedRows = useMemo(() => {
    let result = rows;

    // Search filter
    if (searchQuery.trim()) {
      result = result.filter((row) => matchesSearch(row, searchQuery, columns));
    }

    // Sort
    if (sortKey && sortDir) {
      const col = columns.find((c) => c.key === sortKey);
      result = [...result].sort((a, b) => {
        const cmp = compareValues(a[sortKey], b[sortKey], col?.format);
        return sortDir === "desc" ? -cmp : cmp;
      });
    }

    return result;
  }, [rows, searchQuery, sortKey, sortDir, columns]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(processedRows.length / pageSize));
  const paginatedRows = show_pagination
    ? processedRows.slice(page * pageSize, (page + 1) * pageSize)
    : processedRows;

  const handlePageSizeChange = useCallback((newSize: number) => {
    setPageSize(newSize);
    setPage(0);
  }, []);

  // Sort indicator
  const SortIndicator = ({ colKey }: { colKey: string }) => {
    if (sortKey !== colKey)
      return <ArrowUpDown className="h-3.5 w-3.5 opacity-30" />;
    if (sortDir === "asc") return <ArrowUp className="h-3.5 w-3.5 text-teal-600" />;
    return <ArrowDown className="h-3.5 w-3.5 text-teal-600" />;
  };

  return (
    <div className="flex h-full flex-col">
      {/* Search bar */}
      {show_search && (
        <div className="mb-3 flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(0);
              }}
              className="input pl-9 text-sm"
            />
          </div>
          <span className="shrink-0 text-xs text-slate-400">
            {processedRows.length} result{processedRows.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Table */}
      <div
        className={cn(
          "overflow-auto rounded-lg border border-slate-200 dark:border-slate-700",
          max_height && "max-h-[var(--table-max-h)]",
        )}
        style={
          max_height
            ? ({ "--table-max-h": max_height } as React.CSSProperties)
            : undefined
        }
      >
        <table className="w-full min-w-[600px] border-collapse text-sm">
          <thead
            className={cn(
              "bg-slate-50 dark:bg-surface-dark-muted",
              sticky_header && "sticky top-0 z-10",
            )}
          >
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "border-b border-slate-200 px-4 font-semibold text-slate-600 dark:border-slate-700 dark:text-slate-300",
                    compact ? "py-2" : "py-3",
                    col.align === "right"
                      ? "text-right"
                      : col.align === "center"
                        ? "text-center"
                        : "text-left",
                    col.sortable !== false && "cursor-pointer select-none",
                  )}
                  style={col.width ? { width: col.width } : undefined}
                  onClick={() => {
                    if (col.sortable !== false) handleSort(col.key);
                  }}
                >
                  <div
                    className={cn(
                      "inline-flex items-center gap-1.5",
                      col.align === "right" && "flex-row-reverse",
                    )}
                  >
                    <span>{col.label}</span>
                    {col.sortable !== false && (
                      <SortIndicator colKey={col.key} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {paginatedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center text-slate-400 dark:text-slate-500"
                >
                  {searchQuery ? "No matching results" : "No data available"}
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={cn(
                    "border-b border-slate-100 transition-colors dark:border-slate-800",
                    striped &&
                      rowIdx % 2 === 1 &&
                      "bg-slate-50/50 dark:bg-slate-800/20",
                    highlight_hover &&
                      "hover:bg-teal-50/40 dark:hover:bg-teal-900/10",
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-4 text-slate-700 dark:text-slate-300",
                        compact ? "py-2" : "py-3",
                        col.align === "right"
                          ? "text-right"
                          : col.align === "center"
                            ? "text-center"
                            : "text-left",
                        (col.format === "number" ||
                          col.format === "currency" ||
                          col.format === "percent") &&
                          "tabular-nums",
                      )}
                    >
                      {formatCellValue(row[col.key], col.format)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {show_pagination && processedRows.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          {/* Page size selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Rows per page:
            </span>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-surface-dark-card dark:text-slate-300"
            >
              {page_size_options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          {/* Page navigation */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {page * pageSize + 1}-
              {Math.min((page + 1) * pageSize, processedRows.length)} of{" "}
              {processedRows.length}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:opacity-30 dark:hover:bg-slate-800"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:opacity-30 dark:hover:bg-slate-800"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataTable;
