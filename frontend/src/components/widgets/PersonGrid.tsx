import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { cn, getInitials } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PersonGridItem {
  id: string;
  name: string;
  role?: string;
  avatar_url?: string;
  task_count?: number;
  completion_percent?: number;
  activity_level?: "high" | "medium" | "low" | "inactive";
}

export interface PersonGridConfig {
  columns?: number;
  show_completion_ring?: boolean;
  show_activity_dot?: boolean;
  show_task_count?: boolean;
  clickable?: boolean;
  compact?: boolean;
  avatar_colors?: string[];
}

export interface PersonGridProps {
  data: PersonGridItem[];
  config?: PersonGridConfig;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const AVATAR_COLORS = [
  "from-teal-500 to-teal-600",
  "from-chief-500 to-chief-600",
  "from-navy-500 to-navy-600",
  "from-warm-500 to-warm-600",
  "from-teal-600 to-chief-500",
  "from-chief-600 to-navy-500",
  "from-navy-600 to-teal-500",
  "from-warm-400 to-warm-600",
];

const ACTIVITY_DOT_STYLES: Record<string, { color: string; label: string }> = {
  high: { color: "bg-green-500", label: "Active" },
  medium: { color: "bg-yellow-500", label: "Moderate" },
  low: { color: "bg-orange-400", label: "Low activity" },
  inactive: { color: "bg-slate-400", label: "Inactive" },
};

const ROLE_BADGE_STYLES: Record<string, string> = {
  engineer: "bg-chief-100 text-chief-700 dark:bg-chief-900/30 dark:text-chief-400",
  designer: "bg-navy-100 text-navy-700 dark:bg-navy-900/30 dark:text-navy-400",
  manager: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
  lead: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
  director: "bg-warm-100 text-warm-700 dark:bg-warm-900/30 dark:text-warm-400",
};

function getRoleBadgeStyle(role?: string): string {
  if (!role) return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
  const lower = role.toLowerCase();
  for (const [key, style] of Object.entries(ROLE_BADGE_STYLES)) {
    if (lower.includes(key)) return style;
  }
  return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
}

// ---------------------------------------------------------------------------
// Completion Ring SVG
// ---------------------------------------------------------------------------

function CompletionRing({
  percent,
  size = 36,
}: {
  percent: number;
  size?: number;
}) {
  const strokeWidth = 3;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (percent / 100) * circumference;

  const color =
    percent >= 80 ? "#22c55e" : percent >= 50 ? "#07c7b1" : percent >= 25 ? "#f1821d" : "#ef4444";

  return (
    <svg
      width={size}
      height={size}
      className="shrink-0 -rotate-90"
      aria-label={`${percent}% complete`}
    >
      {/* Background track */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        className="text-slate-200 dark:text-slate-700"
        strokeWidth={strokeWidth}
      />
      {/* Progress arc */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        className="transition-all duration-500"
      />
      {/* Center text */}
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#64748b"
        fontSize={size < 36 ? 8 : 9}
        fontWeight={600}
        transform={`rotate(90, ${size / 2}, ${size / 2})`}
      >
        {Math.round(percent)}%
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PersonGrid({ data, config = {} }: PersonGridProps) {
  const {
    show_completion_ring = true,
    show_activity_dot = true,
    show_task_count = true,
    clickable = true,
    compact = false,
  } = config;

  const navigate = useNavigate();

  const handleClick = useCallback(
    (personId: string) => {
      if (clickable) {
        navigate(`/people/${personId}`);
      }
    },
    [clickable, navigate],
  );

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-10 text-sm text-slate-400">
        No people to display
      </div>
    );
  }

  return (
    <div
      className={cn(
        "grid gap-3",
        "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
      )}
    >
      {data.map((person, idx) => {
        const initials = getInitials(person.name);
        const avatarGradient = AVATAR_COLORS[idx % AVATAR_COLORS.length];
        const activityInfo = ACTIVITY_DOT_STYLES[person.activity_level ?? "inactive"];
        const roleBadge = getRoleBadgeStyle(person.role);

        return (
          <div
            key={person.id}
            onClick={() => handleClick(person.id)}
            className={cn(
              "group flex items-center gap-3 rounded-xl border border-slate-200 bg-white transition-all dark:border-slate-700 dark:bg-surface-dark-card",
              compact ? "px-3 py-2.5" : "px-4 py-3.5",
              clickable &&
                "cursor-pointer hover:border-teal-300 hover:shadow-soft-md dark:hover:border-teal-600",
            )}
          >
            {/* Avatar */}
            <div className="relative shrink-0">
              {person.avatar_url ? (
                <img
                  src={person.avatar_url}
                  alt={person.name}
                  className={cn(
                    "rounded-full object-cover",
                    compact ? "h-9 w-9" : "h-10 w-10",
                  )}
                />
              ) : (
                <div
                  className={cn(
                    "flex items-center justify-center rounded-full bg-gradient-to-br font-semibold text-white",
                    compact ? "h-9 w-9 text-xs" : "h-10 w-10 text-sm",
                    avatarGradient,
                  )}
                >
                  {initials}
                </div>
              )}

              {/* Activity indicator dot */}
              {show_activity_dot && activityInfo && (
                <span
                  className={cn(
                    "absolute -bottom-0.5 -right-0.5 block rounded-full ring-2 ring-white dark:ring-surface-dark-card",
                    compact ? "h-2.5 w-2.5" : "h-3 w-3",
                    activityInfo.color,
                  )}
                  title={activityInfo.label}
                />
              )}
            </div>

            {/* Info */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p
                  className={cn(
                    "truncate font-semibold text-slate-900 dark:text-white",
                    compact ? "text-xs" : "text-sm",
                  )}
                >
                  {person.name}
                </p>
              </div>

              <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                {person.role && (
                  <span
                    className={cn(
                      "inline-block truncate rounded-full px-2 py-0.5 text-2xs font-medium",
                      roleBadge,
                    )}
                  >
                    {person.role}
                  </span>
                )}

                {show_task_count && person.task_count !== undefined && (
                  <span className="text-2xs text-slate-400 dark:text-slate-500">
                    {person.task_count} task{person.task_count !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>

            {/* Completion ring */}
            {show_completion_ring && person.completion_percent !== undefined && (
              <CompletionRing
                percent={person.completion_percent}
                size={compact ? 32 : 36}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default PersonGrid;
