import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  EmptyState – centered placeholder for empty data views             */
/* ------------------------------------------------------------------ */

export interface EmptyStateProps {
  /** Lucide icon component to display at the top */
  icon: React.ComponentType<{ className?: string }>;
  /** Primary heading text */
  title: string;
  /** Supporting description text */
  description: string;
  /** Optional action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Additional CSS class */
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-[240px] flex-col items-center justify-center px-6 py-12 text-center",
        className,
      )}
    >
      {/* Large icon */}
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800">
        <Icon className="h-8 w-8 text-slate-400 dark:text-slate-500" />
      </div>

      {/* Title */}
      <h3 className="mb-1 text-base font-semibold text-slate-900 dark:text-white">
        {title}
      </h3>

      {/* Description */}
      <p className="mb-6 max-w-sm text-sm text-slate-500 dark:text-slate-400">
        {description}
      </p>

      {/* Action button */}
      {action && (
        <button
          onClick={action.onClick}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:ring-offset-2 active:bg-teal-800 dark:bg-teal-500 dark:hover:bg-teal-600"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
