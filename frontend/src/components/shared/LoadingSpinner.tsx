import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  LoadingSpinner – animated SVG spinner with optional label          */
/* ------------------------------------------------------------------ */

type SpinnerSize = "sm" | "md" | "lg";

export interface LoadingSpinnerProps {
  /** Visual size of the spinner */
  size?: SpinnerSize;
  /** Optional message displayed below the spinner */
  message?: string;
  /** Additional CSS class for the container */
  className?: string;
}

const sizeClasses: Record<SpinnerSize, { svg: string; text: string }> = {
  sm: { svg: "h-5 w-5", text: "text-xs" },
  md: { svg: "h-8 w-8", text: "text-sm" },
  lg: { svg: "h-12 w-12", text: "text-base" },
};

export function LoadingSpinner({
  size = "md",
  message,
  className,
}: LoadingSpinnerProps) {
  const classes = sizeClasses[size];

  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3", className)}
      role="status"
      aria-label={message ?? "Loading"}
    >
      <svg
        className={cn("animate-spin text-teal-500", classes.svg)}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>

      {message && (
        <p
          className={cn(
            "text-slate-500 dark:text-slate-400",
            classes.text,
          )}
        >
          {message}
        </p>
      )}
    </div>
  );
}
