import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

export interface PieChartConfig {
  mode?: "pie" | "donut";
  colors?: string[];
  show_legend?: boolean;
  legend_position?: "bottom" | "right";
  show_labels?: boolean;
  show_percentages?: boolean;
  other_threshold?: number;
  inner_radius?: string;
  outer_radius?: string;
  center_label?: string;
  center_value?: string;
  value_format?: string;
}

export interface PieChartProps {
  data: ChartDataPoint[];
  config?: PieChartConfig;
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
  "#3c3c76", // navy-900
  "#e26913", // warm-600
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PieChart({ data, config = {} }: PieChartProps) {
  const {
    mode = "donut",
    colors = CHIEFOPS_COLORS,
    show_legend = true,
    legend_position = "bottom",
    show_labels = true,
    show_percentages = true,
    other_threshold = 2,
    inner_radius,
    outer_radius,
    center_label,
    center_value,
    value_format,
  } = config;

  const option: EChartsOption = useMemo(() => {
    // Roll up small slices into "Other"
    const total = data.reduce((sum, d) => sum + d.value, 0);
    const thresholdValue = total * (other_threshold / 100);

    const significantSlices: ChartDataPoint[] = [];
    let otherValue = 0;

    for (const d of data) {
      if (d.value < thresholdValue && data.length > 5) {
        otherValue += d.value;
      } else {
        significantSlices.push(d);
      }
    }

    if (otherValue > 0) {
      significantSlices.push({ label: "Other", value: otherValue, color: "#94a3b8" });
    }

    // Sort by value descending for visual clarity
    significantSlices.sort((a, b) => b.value - a.value);

    const pieData = significantSlices.map((d, idx) => ({
      name: d.label,
      value: d.value,
      itemStyle: {
        color: d.color ?? colors[idx % colors.length],
        borderColor: "#fff",
        borderWidth: 2,
      },
    }));

    const isDonut = mode === "donut";
    const computedInner = inner_radius ?? (isDonut ? "52%" : "0%");
    const computedOuter = outer_radius ?? "78%";

    const legendRight = legend_position === "right";

    const centerGraphic: EChartsOption["graphic"] =
      isDonut && (center_label ?? center_value)
        ? [
            {
              type: "group",
              left: "center",
              top: "center",
              children: [
                ...(center_value
                  ? [
                      {
                        type: "text" as const,
                        style: {
                          text: center_value,
                          fill: "#0f172a",
                          fontSize: 22,
                          fontWeight: 700,
                          textAlign: "center" as const,
                        },
                        left: "center",
                        top: -14,
                      },
                    ]
                  : []),
                ...(center_label
                  ? [
                      {
                        type: "text" as const,
                        style: {
                          text: center_label,
                          fill: "#64748b",
                          fontSize: 11,
                          fontWeight: 400,
                          textAlign: "center" as const,
                        },
                        left: "center",
                        top: center_value ? 12 : 0,
                      },
                    ]
                  : []),
              ],
            },
          ]
        : undefined;

    return {
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "transparent",
        textStyle: { color: "#f1f5f9", fontSize: 12 },
        formatter: (params: unknown) => {
          const p = params as {
            marker?: string;
            name?: string;
            value?: number;
            percent?: number;
          };
          let displayVal = (p.value ?? 0).toLocaleString();
          if (value_format === "percent") displayVal += "%";
          if (value_format === "currency") displayVal = "$" + displayVal;
          return `<div style="display:flex;align-items:center;gap:6px">
            ${p.marker ?? ""}
            <span>${p.name ?? ""}</span>
          </div>
          <div style="margin-top:4px;font-weight:600">
            ${displayVal}
            <span style="color:#94a3b8;font-weight:400;margin-left:6px">(${(p.percent ?? 0).toFixed(1)}%)</span>
          </div>`;
        },
      },
      legend: {
        show: show_legend,
        orient: legendRight ? "vertical" : "horizontal",
        ...(legendRight
          ? { right: 12, top: "middle" }
          : { bottom: 0, left: "center" }),
        textStyle: { color: "#64748b", fontSize: 11 },
        itemWidth: 10,
        itemHeight: 10,
        itemGap: legendRight ? 12 : 16,
        icon: "circle",
        formatter: (name: string) => {
          if (!show_percentages) return name;
          const item = significantSlices.find((d) => d.label === name);
          if (!item || total === 0) return name;
          const pct = ((item.value / total) * 100).toFixed(1);
          return `${name}  ${pct}%`;
        },
      },
      graphic: centerGraphic,
      series: [
        {
          type: "pie",
          radius: [computedInner, computedOuter],
          center: legendRight ? ["40%", "50%"] : ["50%", "46%"],
          avoidLabelOverlap: true,
          label: {
            show: show_labels,
            position: "outside",
            color: "#475569",
            fontSize: 11,
            formatter: (params: { name?: string; percent?: number }) => {
              if (show_percentages) {
                return `${params.name}\n{pct|${(params.percent ?? 0).toFixed(1)}%}`;
              }
              return params.name ?? "";
            },
            rich: {
              pct: {
                color: "#94a3b8",
                fontSize: 10,
                lineHeight: 16,
              },
            },
          },
          labelLine: {
            show: show_labels,
            length: 12,
            length2: 8,
            lineStyle: { color: "#cbd5e1" },
          },
          emphasis: {
            scaleSize: 6,
            itemStyle: {
              shadowBlur: 14,
              shadowColor: "rgba(0, 0, 0, 0.18)",
            },
          },
          data: pieData,
          animationType: "scale",
          animationEasing: "cubicOut",
          animationDuration: 600,
        },
      ],
    };
  }, [
    data,
    mode,
    colors,
    show_legend,
    legend_position,
    show_labels,
    show_percentages,
    other_threshold,
    inner_radius,
    outer_radius,
    center_label,
    center_value,
    value_format,
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

export default PieChart;
