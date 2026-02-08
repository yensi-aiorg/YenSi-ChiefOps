import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChartDataPoint {
  label: string;
  value: number;
  category?: string;
  color?: string;
}

export interface BarChartConfig {
  orientation?: "vertical" | "horizontal";
  stacked?: boolean;
  colors?: string[];
  x_axis_label?: string;
  y_axis_label?: string;
  show_grid?: boolean;
  show_legend?: boolean;
  bar_width?: number | string;
  value_format?: string;
  max_value?: number;
}

export interface BarChartProps {
  data: ChartDataPoint[];
  config?: BarChartConfig;
}

// ---------------------------------------------------------------------------
// ChiefOps color palette for ECharts
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
// Component
// ---------------------------------------------------------------------------

export function BarChart({ data, config = {} }: BarChartProps) {
  const {
    orientation = "vertical",
    stacked = false,
    colors = CHIEFOPS_COLORS,
    x_axis_label,
    y_axis_label,
    show_grid = true,
    show_legend = true,
    bar_width,
    value_format,
    max_value,
  } = config;

  const isHorizontal = orientation === "horizontal";

  const option: EChartsOption = useMemo(() => {
    // Group data by category for multi-series support
    const categories = [...new Set(data.map((d) => d.category).filter(Boolean))];
    const labels = [...new Set(data.map((d) => d.label))];

    const hasCategorySeries = categories.length > 0;

    const series: EChartsOption["series"] = hasCategorySeries
      ? categories.map((cat, idx) => ({
          name: cat,
          type: "bar" as const,
          stack: stacked ? "total" : undefined,
          barWidth: bar_width ?? (labels.length > 15 ? "60%" : "40%"),
          data: labels.map((label) => {
            const point = data.find(
              (d) => d.label === label && d.category === cat,
            );
            return point?.value ?? 0;
          }),
          itemStyle: {
            borderRadius: stacked ? [0, 0, 0, 0] : isHorizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
            color: colors[idx % colors.length],
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: "rgba(0, 0, 0, 0.15)",
            },
          },
        }))
      : [
          {
            name: y_axis_label ?? "Value",
            type: "bar" as const,
            barWidth: bar_width ?? (labels.length > 15 ? "60%" : "40%"),
            data: data.map((d, idx) => ({
              value: d.value,
              itemStyle: {
                color: d.color ?? colors[idx % colors.length],
                borderRadius: isHorizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
              },
            })),
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: "rgba(0, 0, 0, 0.15)",
              },
            },
          },
        ];

    const categoryAxis = {
      type: "category" as const,
      data: labels,
      name: isHorizontal ? y_axis_label : x_axis_label,
      nameLocation: "middle" as const,
      nameGap: 35,
      nameTextStyle: {
        color: "#64748b",
        fontSize: 12,
        fontWeight: 500 as const,
      },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: "#64748b",
        fontSize: 11,
        rotate: !isHorizontal && labels.length > 8 ? 30 : 0,
        overflow: "truncate" as const,
        width: isHorizontal ? 100 : 80,
      },
    };

    const valueAxis = {
      type: "value" as const,
      name: isHorizontal ? x_axis_label : y_axis_label,
      nameLocation: "middle" as const,
      nameGap: 45,
      nameTextStyle: {
        color: "#64748b",
        fontSize: 12,
        fontWeight: 500 as const,
      },
      max: max_value ?? undefined,
      splitLine: {
        show: show_grid,
        lineStyle: {
          color: "#e2e8f0",
          type: "dashed" as const,
        },
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
    };

    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "transparent",
        textStyle: { color: "#f1f5f9", fontSize: 12 },
        axisPointer: {
          type: "shadow",
          shadowStyle: { color: "rgba(7, 199, 177, 0.06)" },
        },
        formatter: (params: unknown) => {
          const items = Array.isArray(params) ? params : [params];
          const first = items[0] as { axisValue?: string };
          let html = `<div style="font-weight:600;margin-bottom:6px">${first?.axisValue ?? ""}</div>`;
          for (const item of items) {
            const p = item as { marker?: string; seriesName?: string; value?: number };
            let displayVal = (p.value ?? 0).toLocaleString();
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
        show: show_legend && hasCategorySeries,
        bottom: 0,
        textStyle: { color: "#64748b", fontSize: 11 },
        itemWidth: 12,
        itemHeight: 12,
        itemGap: 16,
        icon: "roundRect",
      },
      grid: {
        left: 16,
        right: 16,
        top: 24,
        bottom: show_legend && hasCategorySeries ? 48 : 24,
        containLabel: true,
      },
      xAxis: isHorizontal ? valueAxis : categoryAxis,
      yAxis: isHorizontal ? categoryAxis : valueAxis,
      series,
      animationDuration: 600,
      animationEasing: "cubicOut",
    };
  }, [
    data,
    isHorizontal,
    stacked,
    colors,
    x_axis_label,
    y_axis_label,
    show_grid,
    show_legend,
    bar_width,
    value_format,
    max_value,
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

export default BarChart;
