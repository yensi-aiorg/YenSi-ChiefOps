import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  SkeletonLoader – animated placeholder shapes for loading states    */
/* ------------------------------------------------------------------ */

type SkeletonVariant = "card" | "table" | "chart" | "text" | "widget";

export interface SkeletonLoaderProps {
  /** Layout variant */
  variant?: SkeletonVariant;
  /** Additional CSS class */
  className?: string;
}

/** Reusable shimmer bar */
function Bar({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-slate-200 dark:bg-slate-700", className)}
    />
  );
}

/* ─── Variant renderers ─────────────────────────────────────────────── */

function CardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <Bar className="h-4 w-24" />
        <Bar className="h-6 w-6 rounded-full" />
      </div>
      <Bar className="mt-4 h-8 w-20" />
      <Bar className="mt-3 h-3 w-full" />
      <Bar className="mt-2 h-3 w-3/4" />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
      {/* Table header */}
      <div className="flex items-center gap-4 border-b border-slate-200 px-5 py-3 dark:border-slate-700">
        <Bar className="h-3 w-32" />
        <Bar className="h-3 w-24" />
        <Bar className="h-3 w-20" />
        <Bar className="h-3 w-16" />
      </div>
      {/* Table rows */}
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 border-b border-slate-100 px-5 py-3 last:border-b-0 dark:border-slate-700/50"
        >
          <Bar className="h-8 w-8 rounded-full" />
          <Bar className="h-3 w-28" />
          <Bar className="h-3 w-20" />
          <Bar className="h-3 w-16" />
          <Bar className="h-5 w-14 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      <Bar className="mb-4 h-4 w-32" />
      <div className="flex items-end gap-2">
        {[60, 80, 45, 90, 55, 70, 85, 40, 75, 65].map((h, i) => (
          <Bar
            key={i}
            className="flex-1 rounded-t-sm"
            style={{ height: `${h}%`, minHeight: `${h * 1.5}px` }}
          />
        ))}
      </div>
    </div>
  );
}

function TextSkeleton() {
  return (
    <div className="space-y-3">
      <Bar className="h-4 w-3/4" />
      <Bar className="h-4 w-full" />
      <Bar className="h-4 w-5/6" />
      <Bar className="h-4 w-2/3" />
    </div>
  );
}

function WidgetSkeleton() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Bar className="h-3 w-20" />
          <Bar className="h-7 w-16" />
        </div>
        <Bar className="h-12 w-12 rounded-full" />
      </div>
      <Bar className="mt-4 h-2 w-full rounded-full" />
      <div className="mt-3 flex items-center gap-2">
        <Bar className="h-3 w-3 rounded-full" />
        <Bar className="h-3 w-24" />
      </div>
    </div>
  );
}

/* ─── Variant map ────────────────────────────────────────────────────── */

const variantMap: Record<SkeletonVariant, () => JSX.Element> = {
  card: CardSkeleton,
  table: TableSkeleton,
  chart: ChartSkeleton,
  text: TextSkeleton,
  widget: WidgetSkeleton,
};

export function SkeletonLoader({
  variant = "card",
  className,
}: SkeletonLoaderProps) {
  const Variant = variantMap[variant];

  return (
    <div className={cn("animate-fade-in", className)} aria-hidden="true">
      <Variant />
    </div>
  );
}
