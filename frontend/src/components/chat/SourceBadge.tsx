import { MessageSquare, ListTodo, FolderOpen } from "lucide-react";
import type { SourceUsed } from "@/types";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  SourceBadge – small data source indicator with icon and count      */
/* ------------------------------------------------------------------ */

interface SourceBadgeProps {
  source: SourceUsed;
  className?: string;
}

const SOURCE_CONFIG: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    bg: string;
    text: string;
    border: string;
  }
> = {
  slack: {
    icon: MessageSquare,
    label: "Slack",
    bg: "bg-purple-50 dark:bg-purple-900/30",
    text: "text-purple-700 dark:text-purple-300",
    border: "border-purple-200 dark:border-purple-700",
  },
  jira: {
    icon: ListTodo,
    label: "Jira",
    bg: "bg-blue-50 dark:bg-blue-900/30",
    text: "text-blue-700 dark:text-blue-300",
    border: "border-blue-200 dark:border-blue-700",
  },
  gdrive: {
    icon: FolderOpen,
    label: "Drive",
    bg: "bg-amber-50 dark:bg-amber-900/30",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-700",
  },
  drive: {
    icon: FolderOpen,
    label: "Drive",
    bg: "bg-amber-50 dark:bg-amber-900/30",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-700",
  },
};

const DEFAULT_CONFIG = {
  icon: FolderOpen,
  label: "Source",
  bg: "bg-slate-50 dark:bg-slate-800",
  text: "text-slate-700 dark:text-slate-300",
  border: "border-slate-200 dark:border-slate-600",
};

export function SourceBadge({ source, className }: SourceBadgeProps) {
  const config =
    SOURCE_CONFIG[source.source_type.toLowerCase()] ?? DEFAULT_CONFIG;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-2xs font-medium",
        config.bg,
        config.text,
        config.border,
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      <span>{config.label}</span>
      {source.item_count > 0 && (
        <span className="opacity-70">({source.item_count})</span>
      )}
    </span>
  );
}
