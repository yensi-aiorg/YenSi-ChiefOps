import { useState, useCallback } from "react";
import { MessageSquare, Trello, FolderOpen, Globe, Mail, GitBranch } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActivityFeedItem {
  id: string;
  source: "slack" | "jira" | "drive" | "github" | "email" | "other";
  timestamp: string;
  actor: string;
  action: string;
  detail?: string;
  url?: string;
  avatar_url?: string;
}

export interface ActivityFeedConfig {
  initial_count?: number;
  load_more_count?: number;
  compact?: boolean;
  show_source_icon?: boolean;
  show_avatar?: boolean;
  max_height?: string;
}

export interface ActivityFeedProps {
  data: ActivityFeedItem[];
  config?: ActivityFeedConfig;
}

// ---------------------------------------------------------------------------
// Source style map
// ---------------------------------------------------------------------------

interface SourceStyle {
  Icon: React.ComponentType<{ className?: string }>;
  bg: string;
  text: string;
  border: string;
  label: string;
}

const SOURCE_STYLES: Record<string, SourceStyle> = {
  slack: {
    Icon: MessageSquare,
    bg: "bg-purple-100 dark:bg-purple-900/30",
    text: "text-purple-600 dark:text-purple-400",
    border: "border-l-purple-500",
    label: "Slack",
  },
  jira: {
    Icon: Trello,
    bg: "bg-blue-100 dark:bg-blue-900/30",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-l-blue-500",
    label: "Jira",
  },
  drive: {
    Icon: FolderOpen,
    bg: "bg-green-100 dark:bg-green-900/30",
    text: "text-green-600 dark:text-green-400",
    border: "border-l-green-500",
    label: "Drive",
  },
  github: {
    Icon: GitBranch,
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-700 dark:text-slate-300",
    border: "border-l-slate-500",
    label: "GitHub",
  },
  email: {
    Icon: Mail,
    bg: "bg-warm-100 dark:bg-warm-900/30",
    text: "text-warm-600 dark:text-warm-400",
    border: "border-l-warm-500",
    label: "Email",
  },
  other: {
    Icon: Globe,
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-500 dark:text-slate-400",
    border: "border-l-slate-400",
    label: "Other",
  },
};

// ---------------------------------------------------------------------------
// Single feed entry
// ---------------------------------------------------------------------------

function FeedEntry({
  item,
  compact,
  showSourceIcon,
  showAvatar,
}: {
  item: ActivityFeedItem;
  compact: boolean;
  showSourceIcon: boolean;
  showAvatar: boolean;
}) {
  const style = SOURCE_STYLES[item.source] ?? SOURCE_STYLES.other!;
  const IconComponent = style.Icon;

  const initials = item.actor
    .split(" ")
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const content = (
    <div
      className={cn(
        "group flex items-start gap-3 border-l-2 transition-colors",
        compact ? "px-3 py-2" : "px-4 py-3",
        style.border,
        "hover:bg-slate-50 dark:hover:bg-slate-800/40",
      )}
    >
      {/* Source icon or avatar */}
      {showSourceIcon && (
        <div
          className={cn(
            "flex shrink-0 items-center justify-center rounded-lg",
            compact ? "h-7 w-7" : "h-8 w-8",
            style.bg,
          )}
        >
          <IconComponent
            className={cn(
              style.text,
              compact ? "h-3.5 w-3.5" : "h-4 w-4",
            )}
          />
        </div>
      )}

      {showAvatar && !showSourceIcon && (
        <div className="shrink-0">
          {item.avatar_url ? (
            <img
              src={item.avatar_url}
              alt={item.actor}
              className={cn(
                "rounded-full object-cover",
                compact ? "h-7 w-7" : "h-8 w-8",
              )}
            />
          ) : (
            <div
              className={cn(
                "flex items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-chief-500 text-white",
                compact ? "h-7 w-7 text-2xs" : "h-8 w-8 text-xs",
              )}
            >
              {initials}
            </div>
          )}
        </div>
      )}

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "font-semibold text-slate-900 dark:text-white",
              compact ? "text-xs" : "text-sm",
            )}
          >
            {item.actor}
          </span>
          <span
            className={cn(
              "shrink-0 text-slate-400 dark:text-slate-500",
              compact ? "text-2xs" : "text-xs",
            )}
          >
            {formatRelativeTime(item.timestamp)}
          </span>
        </div>

        <p
          className={cn(
            "text-slate-600 dark:text-slate-400",
            compact ? "text-xs" : "text-sm",
            compact ? "mt-0" : "mt-0.5",
          )}
        >
          {item.action}
        </p>

        {item.detail && !compact && (
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500 line-clamp-2">
            {item.detail}
          </p>
        )}

        {/* Source badge */}
        {!showSourceIcon && (
          <span
            className={cn(
              "mt-1 inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-2xs font-medium",
              style.bg,
              style.text,
            )}
          >
            <IconComponent className="h-2.5 w-2.5" />
            {style.label}
          </span>
        )}
      </div>
    </div>
  );

  if (item.url) {
    return (
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block no-underline"
      >
        {content}
      </a>
    );
  }

  return content;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ActivityFeed({ data, config = {} }: ActivityFeedProps) {
  const {
    initial_count = 15,
    load_more_count = 15,
    compact = false,
    show_source_icon = true,
    show_avatar = true,
    max_height,
  } = config;

  const [visibleCount, setVisibleCount] = useState(initial_count);

  const handleLoadMore = useCallback(() => {
    setVisibleCount((prev) => Math.min(prev + load_more_count, data.length));
  }, [load_more_count, data.length]);

  const visibleItems = data.slice(0, visibleCount);
  const hasMore = visibleCount < data.length;

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-10 text-sm text-slate-400">
        No activity to display
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col",
        max_height && "overflow-y-auto",
      )}
      style={max_height ? { maxHeight: max_height } : undefined}
    >
      {/* Feed entries */}
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {visibleItems.map((item) => (
          <FeedEntry
            key={item.id}
            item={item}
            compact={compact}
            showSourceIcon={show_source_icon}
            showAvatar={show_avatar}
          />
        ))}
      </div>

      {/* Load more */}
      {hasMore && (
        <div className={cn("flex justify-center", compact ? "py-2" : "py-3")}>
          <button
            onClick={handleLoadMore}
            className="text-xs font-medium text-teal-600 transition-colors hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
          >
            Load more ({data.length - visibleCount} remaining)
          </button>
        </div>
      )}
    </div>
  );
}

export default ActivityFeed;
