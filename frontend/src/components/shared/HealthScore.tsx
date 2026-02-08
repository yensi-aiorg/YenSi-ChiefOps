import { useMemo } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { getHealthScoreColor } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Health Score – animated circular progress indicator                 */
/* ------------------------------------------------------------------ */

type SizeVariant = "sm" | "md" | "lg";
type TrendDirection = "up" | "down" | "stable";

export interface HealthScoreProps {
  /** Score from 0 to 100 */
  score: number;
  /** Size of the circle */
  size?: SizeVariant;
  /** Whether to show the trend indicator below the circle */
  showTrend?: boolean;
  /** Direction of the trend arrow */
  trendDirection?: TrendDirection;
  /** Numeric trend value (e.g. +5, -3) */
  trendValue?: number;
  /** Additional CSS class */
  className?: string;
}

/** Dimension configs for each size variant */
const sizeConfig: Record<
  SizeVariant,
  {
    container: number;
    radius: number;
    stroke: number;
    fontSize: string;
    trendSize: string;
    trendIcon: number;
  }
> = {
  sm: {
    container: 48,
    radius: 18,
    stroke: 3,
    fontSize: "text-xs font-bold",
    trendSize: "text-[10px]",
    trendIcon: 12,
  },
  md: {
    container: 80,
    radius: 32,
    stroke: 4,
    fontSize: "text-lg font-bold",
    trendSize: "text-xs",
    trendIcon: 14,
  },
  lg: {
    container: 120,
    radius: 48,
    stroke: 6,
    fontSize: "text-2xl font-bold",
    trendSize: "text-sm",
    trendIcon: 16,
  },
};

/**
 * Return a hex stroke color for the health ring based on score.
 */
function getStrokeColor(score: number): string {
  if (score < 40) return "#ef4444"; // red-500
  if (score <= 70) return "#f59e0b"; // amber-500
  return "#07c7b1"; // teal-500
}

export function HealthScore({
  score,
  size = "md",
  showTrend = false,
  trendDirection,
  trendValue,
  className,
}: HealthScoreProps) {
  const cfg = sizeConfig[size];
  const clampedScore = Math.min(100, Math.max(0, score));

  const { circumference, offset } = useMemo(() => {
    const c = 2 * Math.PI * cfg.radius;
    const o = c - (clampedScore / 100) * c;
    return { circumference: c, offset: o };
  }, [cfg.radius, clampedScore]);

  const strokeColor = getStrokeColor(clampedScore);
  const center = cfg.container / 2;

  const TrendIcon =
    trendDirection === "up"
      ? TrendingUp
      : trendDirection === "down"
        ? TrendingDown
        : Minus;

  const trendColorClass =
    trendDirection === "up"
      ? "text-green-500"
      : trendDirection === "down"
        ? "text-red-500"
        : "text-slate-400";

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      {/* SVG circle */}
      <div
        className="relative"
        style={{ width: cfg.container, height: cfg.container }}
      >
        <svg
          width={cfg.container}
          height={cfg.container}
          viewBox={`0 0 ${cfg.container} ${cfg.container}`}
          className="-rotate-90"
        >
          {/* Background track */}
          <circle
            cx={center}
            cy={center}
            r={cfg.radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={cfg.stroke}
            className="text-slate-200 dark:text-slate-700"
          />

          {/* Progress ring */}
          <circle
            cx={center}
            cy={center}
            r={cfg.radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={cfg.stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-700 ease-out"
          />
        </svg>

        {/* Centered score label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn(cfg.fontSize, getHealthScoreColor(clampedScore))}>
            {Math.round(clampedScore)}
          </span>
        </div>
      </div>

      {/* Optional trend indicator */}
      {showTrend && trendDirection && (
        <div
          className={cn(
            "flex items-center gap-0.5",
            cfg.trendSize,
            trendColorClass,
          )}
        >
          <TrendIcon size={cfg.trendIcon} />
          {trendValue !== undefined && (
            <span className="font-medium">
              {trendDirection === "down" ? "" : "+"}
              {trendValue}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
