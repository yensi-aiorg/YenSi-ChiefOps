import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface KpiData {
  value: number;
  label: string;
  trend_direction?: "up" | "down" | "stable";
  trend_value?: number;
  trend_label?: string;
  prefix?: string;
  suffix?: string;
  sparkline?: number[];
}

export interface KpiCardConfig {
  value_format?: "number" | "currency" | "percent" | "compact";
  decimals?: number;
  trend_positive_direction?: "up" | "down";
  background_color?: string;
  background_gradient?: [string, string];
  show_sparkline?: boolean;
  sparkline_color?: string;
  text_color?: string;
  accent_color?: string;
}

export interface KpiCardProps {
  data: KpiData;
  config?: KpiCardConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatKpiValue(
  value: number,
  format: string,
  decimals: number,
  prefix?: string,
  suffix?: string,
): string {
  let formatted: string;

  switch (format) {
    case "currency":
      formatted = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
        notation: value >= 1_000_000 ? "compact" : "standard",
      }).format(value);
      break;

    case "percent":
      formatted = `${value.toFixed(decimals)}%`;
      break;

    case "compact":
      if (value >= 1_000_000_000) {
        formatted = `${(value / 1_000_000_000).toFixed(decimals)}B`;
      } else if (value >= 1_000_000) {
        formatted = `${(value / 1_000_000).toFixed(decimals)}M`;
      } else if (value >= 1_000) {
        formatted = `${(value / 1_000).toFixed(decimals)}K`;
      } else {
        formatted = value.toFixed(decimals);
      }
      break;

    default:
      formatted = new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 0,
        maximumFractionDigits: decimals,
      }).format(value);
      break;
  }

  return `${prefix ?? ""}${formatted}${suffix ?? ""}`;
}

// ---------------------------------------------------------------------------
// Sparkline subcomponent
// ---------------------------------------------------------------------------

function Sparkline({
  data,
  color = "#07c7b1",
}: {
  data: number[];
  color?: string;
}) {
  const option: EChartsOption = useMemo(
    () => ({
      grid: { left: 0, right: 0, top: 2, bottom: 2 },
      xAxis: {
        type: "category",
        show: false,
        data: data.map((_, i) => i),
      },
      yAxis: {
        type: "value",
        show: false,
        min: Math.min(...data) * 0.9,
        max: Math.max(...data) * 1.05,
      },
      series: [
        {
          type: "line",
          data,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: color + "40" },
                { offset: 1, color: color + "05" },
              ],
            },
          },
        },
      ],
      animation: true,
      animationDuration: 600,
    }),
    [data, color],
  );

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 40 }}
      opts={{ renderer: "svg" }}
      notMerge
      lazyUpdate
    />
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function KpiCard({ data, config = {} }: KpiCardProps) {
  const {
    value_format = "number",
    decimals = 0,
    trend_positive_direction = "up",
    background_color,
    background_gradient,
    show_sparkline = true,
    sparkline_color = "#07c7b1",
    text_color,
    accent_color,
  } = config;

  const formattedValue = formatKpiValue(
    data.value,
    value_format,
    decimals,
    data.prefix,
    data.suffix,
  );

  // Determine trend semantic: is the trend direction "good" or "bad"?
  const trendIsPositive =
    data.trend_direction === "stable"
      ? null
      : data.trend_direction === trend_positive_direction;

  const trendColor =
    trendIsPositive === null
      ? "text-slate-400"
      : trendIsPositive
        ? "text-green-600 dark:text-green-400"
        : "text-red-600 dark:text-red-400";

  const trendBg =
    trendIsPositive === null
      ? "bg-slate-100 dark:bg-slate-800"
      : trendIsPositive
        ? "bg-green-50 dark:bg-green-900/30"
        : "bg-red-50 dark:bg-red-900/30";

  const TrendIcon =
    data.trend_direction === "up"
      ? TrendingUp
      : data.trend_direction === "down"
        ? TrendingDown
        : Minus;

  // Background style
  const bgStyle: React.CSSProperties = {};
  if (background_gradient) {
    bgStyle.background = `linear-gradient(135deg, ${background_gradient[0]}, ${background_gradient[1]})`;
  } else if (background_color) {
    bgStyle.backgroundColor = background_color;
  }

  const hasCustomBg = Boolean(background_color || background_gradient);

  return (
    <div
      className={cn(
        "flex h-full flex-col justify-between",
        hasCustomBg && "rounded-xl p-5",
      )}
      style={bgStyle}
    >
      {/* Value */}
      <div>
        <p
          className={cn(
            "text-3xl font-bold tracking-tight",
            hasCustomBg && text_color
              ? ""
              : "text-slate-900 dark:text-white",
          )}
          style={text_color ? { color: text_color } : undefined}
        >
          {formattedValue}
        </p>

        {/* Label */}
        <p
          className={cn(
            "mt-1 text-sm font-medium",
            hasCustomBg && text_color
              ? "opacity-75"
              : "text-slate-500 dark:text-slate-400",
          )}
          style={text_color ? { color: text_color, opacity: 0.75 } : undefined}
        >
          {data.label}
        </p>
      </div>

      {/* Trend indicator */}
      {data.trend_direction && (
        <div className="mt-3 flex items-center gap-2">
          <div
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
              hasCustomBg ? "bg-white/20" : trendBg,
            )}
          >
            <TrendIcon
              className={cn(
                "h-3.5 w-3.5",
                hasCustomBg ? "" : trendColor,
              )}
              style={
                hasCustomBg
                  ? { color: accent_color ?? text_color ?? "#fff" }
                  : undefined
              }
            />
            <span
              className={cn(hasCustomBg ? "" : trendColor)}
              style={
                hasCustomBg
                  ? { color: accent_color ?? text_color ?? "#fff" }
                  : undefined
              }
            >
              {data.trend_value !== undefined
                ? `${data.trend_value > 0 ? "+" : ""}${data.trend_value}%`
                : data.trend_direction}
            </span>
          </div>
          {data.trend_label && (
            <span
              className={cn(
                "text-xs",
                hasCustomBg
                  ? "opacity-60"
                  : "text-slate-400 dark:text-slate-500",
              )}
              style={
                hasCustomBg
                  ? { color: text_color ?? "#fff", opacity: 0.6 }
                  : undefined
              }
            >
              {data.trend_label}
            </span>
          )}
        </div>
      )}

      {/* Sparkline */}
      {show_sparkline && data.sparkline && data.sparkline.length > 1 && (
        <div className="mt-3">
          <Sparkline
            data={data.sparkline}
            color={hasCustomBg ? (accent_color ?? "#fff") : sparkline_color}
          />
        </div>
      )}
    </div>
  );
}

export default KpiCard;
