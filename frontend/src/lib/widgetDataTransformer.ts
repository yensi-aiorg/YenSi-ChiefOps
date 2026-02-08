/**
 * Transforms raw widget data (from GET /v1/widgets/{id}/data) into
 * the shape each widget type expects for rendering.
 *
 * The widget data endpoint returns { data: dict[], row_count, ... }.
 * Each widget type needs a different structure:
 * - metric_card  -> { value, label, change, trend }
 * - pie_chart    -> ECharts option with series[0].type = "pie"
 * - bar_chart    -> ECharts option with xAxis categories + series
 * - table        -> { headers: string[], rows: (string|number)[][] }
 * - text         -> joined string
 */

// Raw response shape from the widget data endpoint
interface WidgetDataResponse {
  widget_id: string;
  title: string;
  widget_type: string;
  data: Record<string, unknown>[];
  row_count: number;
  executed_at: string;
}

// ---------------------------------------------------------------------------
// Metric card
// ---------------------------------------------------------------------------

interface MetricPayload {
  value: string | number;
  label: string;
  change?: string;
  trend?: "up" | "down" | "flat";
}

function transformMetricCard(data: Record<string, unknown>[]): MetricPayload {
  if (!data || data.length === 0) {
    return { value: "--", label: "" };
  }
  const row = data[0]!;
  return {
    value: row.value != null ? row.value as string | number : "--",
    label: (row.label as string) ?? "",
    change: row.change != null ? String(row.change) : undefined,
    trend: row.trend as MetricPayload["trend"],
  };
}

// ---------------------------------------------------------------------------
// Pie chart -> ECharts option
// ---------------------------------------------------------------------------

const PIE_COLORS = [
  "#0d9488", "#0891b2", "#6366f1", "#d97706", "#e11d48",
  "#16a34a", "#7c3aed", "#ea580c", "#2563eb", "#db2777",
];

function transformPieChart(data: Record<string, unknown>[]): Record<string, unknown> {
  if (!data || data.length === 0) {
    return {
      tooltip: { trigger: "item" },
      series: [{ type: "pie", data: [], radius: ["40%", "70%"] }],
    };
  }

  const pieData = data.map((row, i) => ({
    name: String(row.name ?? row.label ?? row._id ?? `Item ${i + 1}`),
    value: Number(row.value ?? row.count ?? 0),
    itemStyle: { color: PIE_COLORS[i % PIE_COLORS.length] },
  }));

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: {
      orient: "vertical",
      right: 10,
      top: "center",
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["40%", "50%"],
        avoidLabelOverlap: true,
        label: { show: false },
        emphasis: { label: { show: true, fontWeight: "bold" } },
        data: pieData,
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Bar chart -> ECharts option
// ---------------------------------------------------------------------------

const BAR_COLORS = ["#0d9488", "#f59e0b", "#ef4444", "#6366f1", "#10b981"];

function transformBarChart(data: Record<string, unknown>[]): Record<string, unknown> {
  if (!data || data.length === 0) {
    return {
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: [] },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: [] }],
    };
  }

  // Detect if this is grouped/stacked data (has "project" + "status" + "count")
  const firstRow = data[0]!;
  const keys = Object.keys(firstRow);

  if (keys.includes("project") && keys.includes("status") && keys.includes("count")) {
    return transformStackedBar(data);
  }

  // Detect multi-series (has "assigned" and "completed" alongside "name")
  if (keys.includes("name") && keys.includes("assigned") && keys.includes("completed")) {
    return transformMultiSeriesBar(data);
  }

  // Simple bar: first string key = category, first/second numeric key = value
  const nameKey = keys.find((k) => typeof firstRow[k] === "string") ?? keys[0]!;
  const valueKeys = keys.filter((k) => k !== nameKey && typeof firstRow[k] === "number");
  const valueKey = valueKeys[0] ?? keys.find((k) => k !== nameKey) ?? keys[1];

  const categories = data.map((r) => String(r[nameKey] ?? ""));
  const values = data.map((r) => Number(r[valueKey as string] ?? 0));

  return {
    tooltip: { trigger: "axis" },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: {
      type: "category",
      data: categories,
      axisLabel: { rotate: categories.length > 6 ? 30 : 0, fontSize: 11 },
    },
    yAxis: { type: "value" },
    series: [
      {
        type: "bar",
        data: values,
        itemStyle: { color: BAR_COLORS[0], borderRadius: [4, 4, 0, 0] },
      },
    ],
  };
}

function transformStackedBar(data: Record<string, unknown>[]): Record<string, unknown> {
  const projectSet = new Set<string>();
  const statusSet = new Set<string>();
  const countMap = new Map<string, number>();

  for (const row of data) {
    const proj = String(row.project ?? "");
    const stat = String(row.status ?? "");
    projectSet.add(proj);
    statusSet.add(stat);
    countMap.set(`${proj}||${stat}`, Number(row.count ?? 0));
  }

  const projects = Array.from(projectSet);
  const statuses = Array.from(statusSet);

  const series = statuses.map((status, i) => ({
    name: status,
    type: "bar" as const,
    stack: "total",
    data: projects.map((proj) => countMap.get(`${proj}||${status}`) ?? 0),
    itemStyle: { color: BAR_COLORS[i % BAR_COLORS.length] },
  }));

  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: {
      type: "category",
      data: projects,
      axisLabel: { rotate: projects.length > 4 ? 30 : 0, fontSize: 11 },
    },
    yAxis: { type: "value" },
    series,
  };
}

function transformMultiSeriesBar(data: Record<string, unknown>[]): Record<string, unknown> {
  const names = data.map((r) => String(r.name ?? ""));
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
    xAxis: {
      type: "category",
      data: names,
      axisLabel: { rotate: names.length > 6 ? 30 : 0, fontSize: 11 },
    },
    yAxis: { type: "value" },
    series: [
      {
        name: "Assigned",
        type: "bar",
        data: data.map((r) => Number(r.assigned ?? 0)),
        itemStyle: { color: BAR_COLORS[0] },
      },
      {
        name: "Completed",
        type: "bar",
        data: data.map((r) => Number(r.completed ?? 0)),
        itemStyle: { color: BAR_COLORS[3] },
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Table -> { headers, rows }
// ---------------------------------------------------------------------------

interface TablePayload {
  headers: string[];
  rows: (string | number)[][];
}

function transformTable(data: Record<string, unknown>[]): TablePayload {
  if (!data || data.length === 0) {
    return { headers: [], rows: [] };
  }

  const headers = Object.keys(data[0]!);
  const rows = data.map((row) =>
    headers.map((h) => {
      const v = row[h];
      if (v == null) return "—";
      if (Array.isArray(v)) return v.join(", ");
      if (typeof v === "object") return JSON.stringify(v);
      return v as string | number;
    }),
  );

  return { headers, rows };
}

// ---------------------------------------------------------------------------
// Text
// ---------------------------------------------------------------------------

function transformText(data: Record<string, unknown>[]): string {
  if (!data || data.length === 0) return "No data available.";
  return data
    .map((row) => Object.values(row).join(" "))
    .join("\n");
}

// ---------------------------------------------------------------------------
// Main transformer
// ---------------------------------------------------------------------------

/**
 * Map backend widget_type strings to frontend WidgetType enum values.
 * Backend uses "metric_card" / "text"; frontend uses "kpi_card" / "summary_text".
 */
const BACKEND_TYPE_MAP: Record<string, string> = {
  metric_card: "kpi_card",
  text: "summary_text",
};

export function mapBackendWidgetType(backendType: string): string {
  return BACKEND_TYPE_MAP[backendType] ?? backendType;
}

/**
 * Transform raw widget data response into the shape expected by WidgetContent.
 *
 * @param widgetType - The backend widget_type string (e.g. "metric_card", "pie_chart")
 * @param response - The raw response from GET /v1/widgets/{id}/data
 * @returns Transformed payload ready for WidgetContent rendering
 */
export function transformWidgetData(
  widgetType: string,
  response: unknown,
): unknown {
  const resp = response as Partial<WidgetDataResponse>;
  const data = resp?.data ?? [];

  switch (widgetType) {
    case "metric_card":
    case "kpi_card":
      return transformMetricCard(data);

    case "pie_chart":
      return transformPieChart(data);

    case "bar_chart":
      return transformBarChart(data);

    case "line_chart":
      return transformBarChart(data); // same shape, renderer handles type

    case "table":
      return transformTable(data);

    case "text":
    case "summary_text":
      return transformText(data);

    default:
      // Pass through for unknown types
      return data;
  }
}
