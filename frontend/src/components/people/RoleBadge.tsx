import { Brain, CheckCircle2 } from "lucide-react";
import { RoleSource } from "@/types";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  RoleBadge – displays a person's role with source indicator         */
/* ------------------------------------------------------------------ */

interface RoleBadgeProps {
  role: string;
  source: RoleSource;
  className?: string;
}

const SOURCE_CONFIG: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    border: string;
    iconColor: string;
  }
> = {
  [RoleSource.AI_IDENTIFIED]: {
    icon: Brain,
    label: "AI-identified",
    border: "border-purple-300 dark:border-purple-600",
    iconColor: "text-purple-500 dark:text-purple-400",
  },
  [RoleSource.COO_CORRECTED]: {
    icon: CheckCircle2,
    label: "COO-confirmed",
    border: "border-teal-300 dark:border-teal-600",
    iconColor: "text-teal-500 dark:text-teal-400",
  },
};

const DEFAULT_SOURCE = {
  icon: CheckCircle2,
  label: "Imported",
  border: "border-slate-300 dark:border-slate-600",
  iconColor: "text-slate-400 dark:text-slate-500",
};

export function RoleBadge({ role, source, className }: RoleBadgeProps) {
  const config =
    SOURCE_CONFIG[source as string] ?? DEFAULT_SOURCE;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border bg-white px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-surface-dark-card dark:text-slate-300",
        config.border,
        className,
      )}
      title={config.label}
    >
      <Icon className={cn("h-3 w-3", config.iconColor)} />
      {role}
    </span>
  );
}
