import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Badge – small colored pill for statuses, roles, and labels         */
/* ------------------------------------------------------------------ */

type BadgeVariant = "success" | "warning" | "danger" | "info" | "neutral";

export interface BadgeProps {
  /** Text to display inside the badge */
  text: string;
  /** Color variant */
  variant?: BadgeVariant;
  /** Optional leading icon (lucide-react component) */
  icon?: React.ComponentType<{ className?: string }>;
  /** Additional CSS class */
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  success:
    "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
  warning:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
  danger:
    "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
  info:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
  neutral:
    "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
};

export function Badge({
  text,
  variant = "neutral",
  icon: Icon,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantClasses[variant],
        className,
      )}
    >
      {Icon && <Icon className="h-3 w-3 shrink-0" />}
      {text}
    </span>
  );
}
