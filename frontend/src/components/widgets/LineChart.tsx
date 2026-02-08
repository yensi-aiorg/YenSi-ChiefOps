import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { format, parseISO, isValid } from "date-fns";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  series?: string;
}

export interface LineChartConfig {
  colors?: string[];
  x_axis_label?: string;
  y_axis_label?: string;
  smooth?: boolean;
  area_fill?: boolean;
  show_markers?: boolean;
  show_grid?: boolean;
  show_legend?: boolean;
  show_zoom?: boolean;
  date_format?: string;
  value_format?: string;
  max_value?: number;
  min_value?: number;
  line_width?: number;
}

export interface LineChartProps {
  data: TimeSeriesPoint[];
  config?: LineChartConfig;
}

// ---------------------------------------------------------------------------
// ChiefOps color palette
// ---------------------------------------------------------------------------

const CHIEFOPS_COLORS = [
  "#07c7b1", // teal-500
  "#1570f5", // chief-600
  "#5550b6", // navy-700
  "#f1821d", // warm-500
  "#20e3ca", // teal-400
  "#2c8fff", // chief-500
  "#777ddd", // navy-500
  "#f49d42", // warm-400
  "#068076", // teal-700
  "#0e5ae1", // chief-700
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(ts: string, fmt: string): string {
  const parsed = parseISO(ts);
  if (!isValid(parsed)) return ts;
  return format(parsed, fmt);
}

function makeGradient(color: string, opacity: number) {
  return {
    type: "linear" as const,
    x: 0,
    y: 0,
    x2: 0,
    y2: 1,
    colorStops: [
      { offset: 0, color: color + Math.round(opacity * 255).toString(16).padStart(2, "0") },
      { offset: 1, color: color + "05" },
    ],
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LineChart({ data, config = {} }: LineChartProps) {
  const {
    colors = CHIEFOPS_COLORS,
    x_axis_label,
    y_axis_label,
    smooth = true,
    area_fill = false,
    show_markers = true,
    show_grid = true,
    show_legend = true,
    show_zoom = false,
    date_format = "MMM d",
    value_format,
    max_value,
    min_value,
    line_width = 2.5,
  } = config;

  const option: EChartsOption = useMemo(() => {
    // Group by series
    const seriesNames = [...new Set(data.map((d) => d.series ?? "Value"))];
    const allTimestamps = [...new Set(data.map((d) => d.timestamp))].sort();

    // Determine whether zoom is useful
    const enableZoom = show_zoom || allTimestamps.length > 60;

    const seriesList: EChartsOption["series"] = seriesNames.map(
      (name, idx) => {
        const seriesData = allTimestamps.map((ts) => {
          const point = data.find(
            (d) => d.timestamp === ts && (d.series ?? "Value") === name,
          );
          return point?.value ?? null;
        });

        const color = colors[idx % colors.length] ?? CHIEFOPS_COLORS[0]!;

        return {
          name,
          type: "line" as const,
          smooth,
          symbol: show_markers ? "circle" : "none",
          symbolSize: 5,
          lineStyle: { width: line_width, color },
          itemStyle: { color, borderWidth: 2, borderColor: "#fff" },
          areaStyle: area_fill
            ? { color: makeGradient(color, 0.25) }
            : undefined,
          emphasis: {
            focus: "series" as const,
            itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,0.2)" },
          },
          data: seriesData,
          connectNulls: false,
        };
      },
    );

    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "transparent",
        textStyle: { color: "#f1f5f9", fontSize: 12 },
        axisPointer: {
          type: "cross",
          crossStyle: { color: "#94a3b8" },
          lineStyle: { color: "#94a3b8", type: "dashed" },
          label: { backgroundColor: "#334155" },
        },
        formatter: (params: unknown) => {
          const items = Array.isArray(params) ? params : [params];
          const first = items[0] as { axisValue?: string };
          const dateStr = first?.axisValue
            ? formatTimestamp(first.axisValue, "MMM d, yyyy HH:mm")
            : "";
          let html = `<div style="font-weight:600;margin-bottom:6px">${dateStr}</div>`;
          for (const item of items) {
            const p = item as {
              marker?: string;
              seriesName?: string;
              value?: number | null;
            };
            if (p.value === null || p.value === undefined) continue;
            let displayVal = p.value.toLocaleString();
            if (value_format === "percent") displayVal += "%";
            if (value_format === "currency") displayVal = "$" + displayVal;
            html += `<div style="display:flex;align-items:center;gap:6px;margin-top:3px">
              ${p.marker ?? ""}
              <span>${p.seriesName ?? ""}</span>
              <span style="font-weight:600;margin-left:auto">${displayVal}</span>
            </div>`;
          }
          return html;
        },
      },
      legend: {
        show: show_legend && seriesNames.length > 1,
        bottom: enableZoom ? 40 : 0,
        textStyle: { color: "#64748b", fontSize: 11 },
        itemWidth: 16,
        itemHeight: 3,
        itemGap: 16,
        icon: "roundRect",
      },
      grid: {
        left: 16,
        right: 16,
        top: 24,
        bottom:
          (show_legend && seriesNames.length > 1 ? 28 : 0) +
          (enableZoom ? 56 : 24),
        containLabel: true,
      },
      xAxis: {
        type: "category",
        data: allTimestamps,
        name: x_axis_label,
        nameLocation: "middle",
        nameGap: 35,
        nameTextStyle: {
          color: "#64748b",
          fontSize: 12,
          fontWeight: 500,
        },
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#e2e8f0" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#64748b",
          fontSize: 11,
          formatter: (val: string) => formatTimestamp(val, date_format),
          rotate: allTimestamps.length > 20 ? 30 : 0,
        },
      },
      yAxis: {
        type: "value",
        name: y_axis_label,
        nameLocation: "middle",
        nameGap: 50,
        nameTextStyle: {
          color: "#64748b",
          fontSize: 12,
          fontWeight: 500,
        },
        max: max_value ?? undefined,
        min: min_value ?? undefined,
        splitLine: {
          show: show_grid,
          lineStyle: { color: "#e2e8f0", type: "dashed" },
        },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: "#64748b",
          fontSize: 11,
          formatter: (val: number) => {
            if (value_format === "percent") return `${val}%`;
            if (value_format === "currency") return `$${val.toLocaleString()}`;
            if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
            if (val >= 1_000) return `${(val / 1_000).toFixed(1)}K`;
            return val.toLocaleString();
          },
        },
      },
      dataZoom: enableZoom
        ? [
            {
              type: "slider",
              bottom: 8,
              height: 22,
              borderColor: "#e2e8f0",
              backgroundColor: "#f8fafc",
              fillerColor: "rgba(7, 199, 177, 0.12)",
              handleStyle: { color: "#07c7b1", borderColor: "#07c7b1" },
              textStyle: { color: "#64748b", fontSize: 10 },
              dataBackground: {
                lineStyle: { color: "#cbd5e1" },
                areaStyle: { color: "#f1f5f9" },
              },
            },
            { type: "inside", zoomOnMouseWheel: true, moveOnMouseMove: true },
          ]
        : undefined,
      series: seriesList,
      animationDuration: 800,
      animationEasing: "cubicOut",
    };
  }, [
    data,
    colors,
    x_axis_label,
    y_axis_label,
    smooth,
    area_fill,
    show_markers,
    show_grid,
    show_legend,
    show_zoom,
    date_format,
    value_format,
    max_value,
    min_value,
    line_width,
  ]);

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: "100%", minHeight: 300 }}
      opts={{ renderer: "svg" }}
      notMerge
      lazyUpdate
    />
  );
}

export default LineChart;
