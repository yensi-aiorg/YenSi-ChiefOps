import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  ProgressBar – horizontal bar with animated width transition        */
/* ------------------------------------------------------------------ */

type ProgressVariant = "primary" | "success" | "warning" | "danger";
type ProgressSize = "sm" | "md";

export interface ProgressBarProps {
  /** Progress value between 0 and 100 */
  progress: number;
  /** Color variant */
  variant?: ProgressVariant;
  /** Whether to display the numeric percentage on the right */
  showPercentage?: boolean;
  /** Height preset */
  size?: ProgressSize;
  /** Additional CSS class for the outer container */
  className?: string;
}

const variantClasses: Record<ProgressVariant, string> = {
  primary: "bg-teal-500",
  success: "bg-green-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
};

const sizeClasses: Record<ProgressSize, string> = {
  sm: "h-1.5",
  md: "h-2.5",
};

export function ProgressBar({
  progress,
  variant = "primary",
  showPercentage = false,
  size = "md",
  className,
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, progress));

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {/* Track */}
      <div
        className={cn(
          "flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700",
          sizeClasses[size],
        )}
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {/* Filled portion */}
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500 ease-out",
            variantClasses[variant],
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>

      {/* Percentage label */}
      {showPercentage && (
        <span className="shrink-0 text-xs font-medium text-slate-600 dark:text-slate-400">
          {Math.round(clamped)}%
        </span>
      )}
    </div>
  );
}
