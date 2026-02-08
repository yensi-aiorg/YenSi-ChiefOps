import {
  lazy,
  Suspense,
  Component,
  type ReactNode,
  type ErrorInfo,
} from "react";
import { RefreshCw, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Lazy-loaded widget components
// ---------------------------------------------------------------------------

const BarChart = lazy(() =>
  import("@/components/widgets/BarChart").then((m) => ({ default: m.BarChart })),
);
const LineChart = lazy(() =>
  import("@/components/widgets/LineChart").then((m) => ({
    default: m.LineChart,
  })),
);
const PieChart = lazy(() =>
  import("@/components/widgets/PieChart").then((m) => ({
    default: m.PieChart,
  })),
);
const GanttChart = lazy(() =>
  import("@/components/widgets/GanttChart").then((m) => ({
    default: m.GanttChart,
  })),
);
const KpiCard = lazy(() =>
  import("@/components/widgets/KpiCard").then((m) => ({
    default: m.KpiCard,
  })),
);
const DataTable = lazy(() =>
  import("@/components/widgets/DataTable").then((m) => ({
    default: m.DataTable,
  })),
);
const SummaryText = lazy(() =>
  import("@/components/widgets/SummaryText").then((m) => ({
    default: m.SummaryText,
  })),
);
const PersonGrid = lazy(() =>
  import("@/components/widgets/PersonGrid").then((m) => ({
    default: m.PersonGrid,
  })),
);
const TimelineWidget = lazy(() =>
  import("@/components/widgets/TimelineWidget").then((m) => ({
    default: m.TimelineWidget,
  })),
);
const ActivityFeed = lazy(() =>
  import("@/components/widgets/ActivityFeed").then((m) => ({
    default: m.ActivityFeed,
  })),
);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WidgetType =
  | "bar_chart"
  | "line_chart"
  | "pie_chart"
  | "gantt_chart"
  | "kpi_card"
  | "data_table"
  | "summary_text"
  | "person_grid"
  | "timeline"
  | "activity_feed";

export interface WidgetSpec {
  id: string;
  title: string;
  description?: string;
  widget_type: WidgetType;
  display_config?: Record<string, unknown>;
  span?: number;
}

export interface WidgetRendererProps {
  widget: WidgetSpec;
  data: unknown;
  isLoading: boolean;
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Error Boundary
// ---------------------------------------------------------------------------

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class WidgetErrorBoundary extends Component<
  { children: ReactNode; widgetTitle: string; onRetry?: () => void },
  ErrorBoundaryState
> {
  constructor(props: {
    children: ReactNode;
    widgetTitle: string;
    onRetry?: () => void;
  }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(
      `[WidgetRenderer] Error in "${this.props.widgetTitle}":`,
      error,
      info.componentStack,
    );
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 py-10">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/20">
            <AlertCircle className="h-6 w-6 text-red-500" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Widget failed to render
            </p>
            <p className="mt-1 max-w-xs text-xs text-slate-400">
              {this.state.error?.message ?? "An unexpected error occurred"}
            </p>
          </div>
          {this.props.onRetry && (
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                this.props.onRetry?.();
              }}
              className="btn-secondary text-xs"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function WidgetSkeleton() {
  return (
    <div className="flex h-full min-h-[200px] flex-col gap-3 p-1">
      <div className="skeleton h-4 w-2/3 rounded" />
      <div className="skeleton h-3 w-1/3 rounded" />
      <div className="skeleton mt-2 flex-1 rounded-lg" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading overlay
// ---------------------------------------------------------------------------

function LoadingOverlay() {
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center rounded-xl bg-white/60 backdrop-blur-sm dark:bg-surface-dark-card/60">
      <div className="flex flex-col items-center gap-2">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Refreshing...
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Widget content dispatcher
// ---------------------------------------------------------------------------

function WidgetContent({
  widgetType,
  data,
  displayConfig,
}: {
  widgetType: WidgetType;
  data: unknown;
  displayConfig?: Record<string, unknown>;
}) {
  switch (widgetType) {
    case "bar_chart":
      return (
        <BarChart
          data={data as import("@/components/widgets/BarChart").ChartDataPoint[]}
          config={displayConfig as import("@/components/widgets/BarChart").BarChartConfig}
        />
      );

    case "line_chart":
      return (
        <LineChart
          data={
            data as import("@/components/widgets/LineChart").TimeSeriesPoint[]
          }
          config={
            displayConfig as import("@/components/widgets/LineChart").LineChartConfig
          }
        />
      );

    case "pie_chart":
      return (
        <PieChart
          data={data as import("@/components/widgets/PieChart").ChartDataPoint[]}
          config={
            displayConfig as import("@/components/widgets/PieChart").PieChartConfig
          }
        />
      );

    case "gantt_chart":
      return (
        <GanttChart
          data={data as import("@/components/widgets/GanttChart").GanttItem[]}
          config={
            displayConfig as import("@/components/widgets/GanttChart").GanttChartConfig
          }
        />
      );

    case "kpi_card":
      return (
        <KpiCard
          data={data as import("@/components/widgets/KpiCard").KpiData}
          config={
            displayConfig as import("@/components/widgets/KpiCard").KpiCardConfig
          }
        />
      );

    case "data_table":
      return (
        <DataTable
          data={data as import("@/components/widgets/DataTable").TableData}
          config={
            displayConfig as import("@/components/widgets/DataTable").DataTableConfig
          }
        />
      );

    case "summary_text":
      return (
        <SummaryText
          data={
            data as import("@/components/widgets/SummaryText").SummaryTextData
          }
          config={
            displayConfig as import("@/components/widgets/SummaryText").SummaryTextConfig
          }
        />
      );

    case "person_grid":
      return (
        <PersonGrid
          data={
            data as import("@/components/widgets/PersonGrid").PersonGridItem[]
          }
          config={
            displayConfig as import("@/components/widgets/PersonGrid").PersonGridConfig
          }
        />
      );

    case "timeline":
      return (
        <TimelineWidget
          data={
            data as import("@/components/widgets/TimelineWidget").TimelineEvent[]
          }
          config={
            displayConfig as import("@/components/widgets/TimelineWidget").TimelineWidgetConfig
          }
        />
      );

    case "activity_feed":
      return (
        <ActivityFeed
          data={
            data as import("@/components/widgets/ActivityFeed").ActivityFeedItem[]
          }
          config={
            displayConfig as import("@/components/widgets/ActivityFeed").ActivityFeedConfig
          }
        />
      );

    default: {
      const exhaustiveCheck: never = widgetType;
      return (
        <div className="flex items-center justify-center py-10 text-sm text-slate-400">
          Unknown widget type: {String(exhaustiveCheck)}
        </div>
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function WidgetRenderer({
  widget,
  data,
  isLoading,
  onRefresh,
}: WidgetRendererProps) {
  const isKpi = widget.widget_type === "kpi_card";

  return (
    <div
      className={cn(
        "card relative flex flex-col overflow-hidden",
        isKpi ? "p-4" : "p-5",
      )}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3
            className={cn(
              "truncate font-semibold text-slate-900 dark:text-white",
              isKpi ? "text-sm" : "text-base",
            )}
          >
            {widget.title}
          </h3>
          {widget.description && (
            <p className="mt-0.5 truncate text-xs text-slate-400 dark:text-slate-500">
              {widget.description}
            </p>
          )}
        </div>

        {/* Refresh button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className={cn(
              "shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300",
              isLoading && "animate-spin",
            )}
            aria-label={`Refresh ${widget.title}`}
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Widget content */}
      <div className="relative min-h-0 flex-1">
        {/* Loading overlay (when refreshing with existing data) */}
        {isLoading && data !== null && data !== undefined && <LoadingOverlay />}

        <WidgetErrorBoundary
          widgetTitle={widget.title}
          onRetry={onRefresh}
        >
          <Suspense fallback={<WidgetSkeleton />}>
            {data !== null && data !== undefined ? (
              <WidgetContent
                widgetType={widget.widget_type}
                data={data}
                displayConfig={widget.display_config}
              />
            ) : isLoading ? (
              <WidgetSkeleton />
            ) : (
              <div className="flex items-center justify-center py-10 text-sm text-slate-400">
                No data available
              </div>
            )}
          </Suspense>
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}

export default WidgetRenderer;
