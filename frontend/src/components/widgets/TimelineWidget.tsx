import { useState, useCallback } from "react";
import {
  CheckCircle,
  Upload,
  AlertTriangle,
  FileText,
  Clock,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn, formatRelativeTime, formatDate } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  detail?: string;
  type: "completion" | "ingestion" | "alert" | "report" | "general";
  actor?: string;
  metadata?: Record<string, string>;
}

export interface TimelineWidgetConfig {
  initial_count?: number;
  load_more_count?: number;
  show_relative_time?: boolean;
  alternating?: boolean;
  animate?: boolean;
}

export interface TimelineWidgetProps {
  data: TimelineEvent[];
  config?: TimelineWidgetConfig;
}

// ---------------------------------------------------------------------------
// Event icon & color map
// ---------------------------------------------------------------------------

interface EventStyle {
  Icon: React.ComponentType<{ className?: string }>;
  bg: string;
  ring: string;
  text: string;
}

const EVENT_STYLES: Record<string, EventStyle> = {
  completion: {
    Icon: CheckCircle,
    bg: "bg-green-500",
    ring: "ring-green-100 dark:ring-green-900/40",
    text: "text-white",
  },
  ingestion: {
    Icon: Upload,
    bg: "bg-chief-500",
    ring: "ring-chief-100 dark:ring-chief-900/40",
    text: "text-white",
  },
  alert: {
    Icon: AlertTriangle,
    bg: "bg-warm-500",
    ring: "ring-warm-100 dark:ring-warm-900/40",
    text: "text-white",
  },
  report: {
    Icon: FileText,
    bg: "bg-teal-500",
    ring: "ring-teal-100 dark:ring-teal-900/40",
    text: "text-white",
  },
  general: {
    Icon: Clock,
    bg: "bg-slate-400",
    ring: "ring-slate-100 dark:ring-slate-800",
    text: "text-white",
  },
};

// ---------------------------------------------------------------------------
// Single event card
// ---------------------------------------------------------------------------

function TimelineEventCard({
  event,
  index,
  alternating,
  animate,
  showRelativeTime,
}: {
  event: TimelineEvent;
  index: number;
  alternating: boolean;
  animate: boolean;
  showRelativeTime: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const isRight = alternating && index % 2 === 1;
  const style = EVENT_STYLES[event.type] ?? EVENT_STYLES.general!;
  const IconComponent = style.Icon;

  return (
    <div
      className={cn(
        "group relative flex",
        alternating
          ? isRight
            ? "flex-row"
            : "flex-row-reverse"
          : "flex-row",
        animate && "animate-fade-in-up",
      )}
      style={animate ? { animationDelay: `${index * 60}ms` } : undefined}
    >
      {/* Spacer (for alternating mode) */}
      {alternating && <div className="hidden w-1/2 md:block" />}

      {/* Event icon on the vertical line */}
      <div className="absolute left-4 z-10 flex -translate-x-1/2 md:left-1/2">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full ring-4",
            style.bg,
            style.ring,
          )}
        >
          <IconComponent className={cn("h-4 w-4", style.text)} />
        </div>
      </div>

      {/* Card */}
      <div
        className={cn(
          "ml-10 w-full md:w-1/2",
          alternating
            ? isRight
              ? "md:ml-0 md:pl-8"
              : "md:mr-0 md:pr-8"
            : "md:pl-8",
        )}
      >
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-soft transition-shadow hover:shadow-soft-md dark:border-slate-700 dark:bg-surface-dark-card">
          {/* Timestamp */}
          <div className="mb-1 flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
            <time dateTime={event.timestamp}>
              {showRelativeTime
                ? formatRelativeTime(event.timestamp)
                : formatDate(event.timestamp, "MMM d, yyyy HH:mm")}
            </time>
            {event.actor && (
              <>
                <span className="text-slate-300 dark:text-slate-600">|</span>
                <span className="font-medium text-slate-500 dark:text-slate-400">
                  {event.actor}
                </span>
              </>
            )}
          </div>

          {/* Title */}
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            {event.title}
          </h4>

          {/* Detail (expandable) */}
          {event.detail && (
            <>
              <div
                className={cn(
                  "overflow-hidden transition-all duration-200",
                  expanded ? "mt-2 max-h-96" : "max-h-0",
                )}
              >
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {event.detail}
                </p>
                {event.metadata && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {Object.entries(event.metadata).map(([key, val]) => (
                      <span
                        key={key}
                        className="rounded-full bg-slate-100 px-2 py-0.5 text-2xs text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                      >
                        {key}: {val}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => setExpanded((prev) => !prev)}
                className="mt-1.5 inline-flex items-center gap-0.5 text-xs font-medium text-teal-600 transition-colors hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
              >
                {expanded ? (
                  <>
                    Hide details <ChevronUp className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    Show details <ChevronDown className="h-3 w-3" />
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TimelineWidget({ data, config = {} }: TimelineWidgetProps) {
  const {
    initial_count = 10,
    load_more_count = 10,
    show_relative_time = true,
    alternating = true,
    animate = true,
  } = config;

  const [visibleCount, setVisibleCount] = useState(initial_count);

  const handleLoadMore = useCallback(() => {
    setVisibleCount((prev) => Math.min(prev + load_more_count, data.length));
  }, [load_more_count, data.length]);

  const visibleEvents = data.slice(0, visibleCount);
  const hasMore = visibleCount < data.length;

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-10 text-sm text-slate-400">
        No events to display
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div
        className={cn(
          "absolute top-0 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-700",
          "left-4 -translate-x-1/2 md:left-1/2",
        )}
      />

      {/* Events */}
      <div className="space-y-6 pb-4">
        {visibleEvents.map((event, idx) => (
          <TimelineEventCard
            key={event.id}
            event={event}
            index={idx}
            alternating={alternating}
            animate={animate}
            showRelativeTime={show_relative_time}
          />
        ))}
      </div>

      {/* Load more button */}
      {hasMore && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={handleLoadMore}
            className="btn-secondary text-sm"
          >
            Load more ({data.length - visibleCount} remaining)
          </button>
        </div>
      )}
    </div>
  );
}

export default TimelineWidget;
