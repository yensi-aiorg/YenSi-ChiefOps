import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { format, parseISO, isValid, differenceInDays } from "date-fns";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GanttItem {
  id: string;
  name: string;
  start: string;
  end: string;
  category?: string;
  status?: "not_started" | "in_progress" | "completed" | "blocked" | "at_risk";
  progress?: number;
  assignee?: string;
  milestone?: boolean;
}

export interface GanttChartConfig {
  colors?: Record<string, string>;
  group_by?: "category" | "assignee";
  show_today?: boolean;
  show_progress?: boolean;
  row_height?: number;
  date_format?: string;
}

export interface GanttChartProps {
  data: GanttItem[];
  config?: GanttChartConfig;
}

// ---------------------------------------------------------------------------
// Status color map
// ---------------------------------------------------------------------------

const DEFAULT_STATUS_COLORS: Record<string, string> = {
  not_started: "#94a3b8",  // slate-400
  in_progress: "#07c7b1",  // teal-500
  completed: "#22c55e",    // green-500
  blocked: "#ef4444",      // red-500
  at_risk: "#f1821d",      // warm-500
};

const MILESTONE_COLOR = "#5550b6"; // navy-700

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toTimestamp(dateStr: string): number {
  const parsed = parseISO(dateStr);
  return isValid(parsed) ? parsed.getTime() : 0;
}

function formatDate(dateStr: string, fmt: string): string {
  const parsed = parseISO(dateStr);
  return isValid(parsed) ? format(parsed, fmt) : dateStr;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function GanttChart({ data, config = {} }: GanttChartProps) {
  const {
    colors = {},
    group_by,
    show_today = true,
    show_progress = true,
    row_height = 30,
    date_format = "MMM d",
  } = config;

  const statusColors = { ...DEFAULT_STATUS_COLORS, ...colors };

  const option: EChartsOption = useMemo(() => {
    if (data.length === 0) {
      return { graphic: { type: "text", left: "center", top: "center", style: { text: "No tasks to display", fill: "#94a3b8", fontSize: 14 } } };
    }

    // Sort tasks by start date
    const sorted = [...data].sort(
      (a, b) => toTimestamp(a.start) - toTimestamp(b.start),
    );

    // Build category labels (Y axis)
    const categoryLabels = sorted.map((item) => {
      if (group_by === "assignee" && item.assignee) return item.assignee;
      if (group_by === "category" && item.category) return item.category;
      return item.name;
    });

    // Date range for X axis
    const allStarts = sorted.map((d) => toTimestamp(d.start)).filter(Boolean);
    const allEnds = sorted.map((d) => toTimestamp(d.end)).filter(Boolean);
    const minDate = Math.min(...allStarts);
    const maxDate = Math.max(...allEnds);
    const rangePadding = (maxDate - minDate) * 0.05 || 86400000;

    const now = Date.now();

    // Render items
    const renderItem = (
      _params: { coordSys: { x: number; y: number; width: number; height: number } },
      api: {
        value: (dim: number) => number;
        coord: (val: [number, number]) => [number, number];
        size: (val: [number, number]) => [number, number];
        style: (extra?: Record<string, unknown>) => Record<string, unknown>;
      },
    ) => {
      const categoryIndex = api.value(0);
      const startVal = api.value(1);
      const endVal = api.value(2);
      const isMilestone = api.value(4) === 1;
      const progress = api.value(5);

      if (isMilestone) {
        // Render diamond marker for milestones
        const point = api.coord([startVal, categoryIndex]);
        const diamondSize = 14;
        return {
          type: "polygon",
          shape: {
            points: [
              [point[0], point[1] - diamondSize],
              [point[0] + diamondSize, point[1]],
              [point[0], point[1] + diamondSize],
              [point[0] - diamondSize, point[1]],
            ],
          },
          style: api.style({ fill: MILESTONE_COLOR }),
        };
      }

      // Regular bar
      const start = api.coord([startVal, categoryIndex]);
      const end = api.coord([endVal, categoryIndex]);
      const barHeight = api.size([0, 1])[1] * 0.55;

      const rectX = start[0];
      const rectY = start[1] - barHeight / 2;
      const rectWidth = Math.max(end[0] - start[0], 4);

      const children: unknown[] = [
        {
          type: "rect",
          shape: {
            x: rectX,
            y: rectY,
            width: rectWidth,
            height: barHeight,
            r: [4, 4, 4, 4],
          },
          style: api.style({
            opacity: 0.85,
          }),
        },
      ];

      // Progress overlay
      if (show_progress && progress > 0 && progress < 100) {
        const progressWidth = rectWidth * (progress / 100);
        children.push({
          type: "rect",
          shape: {
            x: rectX,
            y: rectY,
            width: progressWidth,
            height: barHeight,
            r: [4, 0, 0, 4],
          },
          style: {
            fill: "rgba(255, 255, 255, 0.25)",
          },
        });
      }

      return {
        type: "group",
        children,
      };
    };

    // Build data array for custom series
    // [categoryIndex, startTimestamp, endTimestamp, statusColorIndex, isMilestone, progress]
    const seriesData = sorted.map((item, idx) => {
      const startTs = toTimestamp(item.start);
      const endTs = toTimestamp(item.end);
      const isMilestone = item.milestone || differenceInDays(endTs, startTs) === 0;
      const color = statusColors[item.status ?? "not_started"] ?? statusColors.not_started;

      return {
        value: [idx, startTs, endTs, 0, isMilestone ? 1 : 0, item.progress ?? 0],
        itemStyle: { color },
        name: item.name,
      };
    });

    // Today marker
    const markLine =
      show_today && now >= minDate - rangePadding && now <= maxDate + rangePadding
        ? {
            silent: true,
            symbol: "none",
            lineStyle: {
              color: "#ef4444",
              width: 1.5,
              type: "dashed" as const,
            },
            label: {
              show: true,
              formatter: "Today",
              position: "end" as const,
              color: "#ef4444",
              fontSize: 10,
              fontWeight: 600,
            },
            data: [{ xAxis: now }],
          }
        : undefined;

    return {
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        borderColor: "transparent",
        textStyle: { color: "#f1f5f9", fontSize: 12 },
        formatter: (params: unknown) => {
          const p = params as { dataIndex?: number };
          const idx = p.dataIndex ?? 0;
          const item = sorted[idx];
          if (!item) return "";

          const statusLabel = (item.status ?? "not_started").replace(/_/g, " ");
          const statusDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${statusColors[item.status ?? "not_started"]};margin-right:6px"></span>`;

          return `<div style="max-width:260px">
            <div style="font-weight:600;margin-bottom:4px">${item.name}</div>
            <div style="color:#94a3b8;font-size:11px;margin-bottom:6px">
              ${formatDate(item.start, "MMM d, yyyy")} - ${formatDate(item.end, "MMM d, yyyy")}
            </div>
            <div style="display:flex;align-items:center;text-transform:capitalize">
              ${statusDot}${statusLabel}
            </div>
            ${item.assignee ? `<div style="color:#94a3b8;margin-top:3px;font-size:11px">Assignee: ${item.assignee}</div>` : ""}
            ${item.progress !== undefined ? `<div style="color:#94a3b8;margin-top:3px;font-size:11px">Progress: ${item.progress}%</div>` : ""}
          </div>`;
        },
      },
      grid: {
        left: 16,
        right: 24,
        top: 20,
        bottom: 20,
        containLabel: true,
      },
      xAxis: {
        type: "time",
        min: minDate - rangePadding,
        max: maxDate + rangePadding,
        axisLine: { lineStyle: { color: "#e2e8f0" } },
        axisTick: { lineStyle: { color: "#e2e8f0" } },
        axisLabel: {
          color: "#64748b",
          fontSize: 11,
          formatter: (val: number) => {
            const d = new Date(val);
            return isValid(d) ? format(d, date_format) : "";
          },
        },
        splitLine: {
          show: true,
          lineStyle: { color: "#f1f5f9", type: "dashed" },
        },
      },
      yAxis: {
        type: "category",
        data: categoryLabels,
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: "#475569",
          fontSize: 11,
          width: 120,
          overflow: "truncate",
        },
      },
      dataZoom: [
        {
          type: "slider",
          xAxisIndex: 0,
          bottom: 0,
          height: 16,
          borderColor: "#e2e8f0",
          backgroundColor: "#f8fafc",
          fillerColor: "rgba(7, 199, 177, 0.10)",
          handleStyle: { color: "#07c7b1", borderColor: "#07c7b1" },
          textStyle: { color: "#64748b", fontSize: 10 },
        },
        { type: "inside", xAxisIndex: 0 },
      ],
      series: [
        {
          type: "custom",
          renderItem: renderItem as unknown as EChartsOption["series"],
          encode: { x: [1, 2], y: 0 },
          data: seriesData,
          markLine,
          clip: true,
        },
      ] as EChartsOption["series"],
      animationDuration: 500,
      animationEasing: "cubicOut",
    };
  }, [data, statusColors, group_by, show_today, show_progress, row_height, date_format]);

  const height = Math.max(300, data.length * (config.row_height ?? 30) + 80);

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: `${height}px`, minHeight: 300 }}
      opts={{ renderer: "canvas" }}
      notMerge
      lazyUpdate
    />
  );
}

export default GanttChart;
