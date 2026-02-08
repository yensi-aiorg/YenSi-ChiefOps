import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Card – reusable container with optional header and actions         */
/* ------------------------------------------------------------------ */

export interface CardProps {
  /** Optional card title */
  title?: string;
  /** Optional subtitle beneath the title */
  subtitle?: string;
  /** Card body content */
  children: ReactNode;
  /** Additional CSS class */
  className?: string;
  /** Action elements rendered in the top-right of the header */
  actions?: ReactNode;
  /** If provided, the card becomes clickable with a hover effect */
  onClick?: () => void;
}

export function Card({
  title,
  subtitle,
  children,
  className,
  actions,
  onClick,
}: CardProps) {
  const isClickable = Boolean(onClick);

  const Wrapper = isClickable ? "button" : "div";
  const clickableProps = isClickable
    ? {
        onClick,
        type: "button" as const,
      }
    : {};

  return (
    <Wrapper
      {...clickableProps}
      className={cn(
        "rounded-xl border border-slate-200 bg-white p-5 shadow-soft text-left transition-all dark:border-slate-700 dark:bg-slate-800",
        isClickable &&
          "cursor-pointer hover:border-teal-300 hover:shadow-soft-md active:scale-[0.99] dark:hover:border-teal-600",
        className,
      )}
    >
      {/* Header row */}
      {(title || actions) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {title && (
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                {subtitle}
              </p>
            )}
          </div>

          {actions && (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          )}
        </div>
      )}

      {/* Body */}
      {children}
    </Wrapper>
  );
}
