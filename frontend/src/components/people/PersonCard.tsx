import { cn, getInitials } from "@/lib/utils";
import type { Person } from "@/types";
import { ActivityLevel } from "@/types";
import { RoleBadge } from "./RoleBadge";

/* ------------------------------------------------------------------ */
/*  PersonCard – compact person summary card for directory listings    */
/* ------------------------------------------------------------------ */

interface PersonCardProps {
  person: Person;
  onClick?: (person: Person) => void;
  className?: string;
}

/**
 * Deterministic background color based on a person's name.
 * Maps the first character's char code to one of several Tailwind gradient pairs.
 */
function getAvatarGradient(name: string): string {
  const gradients = [
    "from-teal-400 to-teal-600",
    "from-chief-400 to-chief-600",
    "from-purple-400 to-purple-600",
    "from-warm-400 to-warm-600",
    "from-green-400 to-green-600",
    "from-blue-400 to-blue-600",
    "from-rose-400 to-rose-600",
    "from-indigo-400 to-indigo-600",
  ];
  const index = name.charCodeAt(0) % gradients.length;
  return gradients[index] ?? gradients[0]!;
}

function getActivityDot(level: ActivityLevel | string): {
  color: string;
  label: string;
} {
  switch (level) {
    case ActivityLevel.VERY_ACTIVE:
    case "very_active":
      return { color: "bg-green-500", label: "Very Active" };
    case ActivityLevel.ACTIVE:
    case "active":
      return { color: "bg-green-400", label: "Active" };
    case ActivityLevel.MODERATE:
    case "moderate":
      return { color: "bg-yellow-400", label: "Moderate" };
    case ActivityLevel.QUIET:
    case "quiet":
      return { color: "bg-orange-400", label: "Quiet" };
    case ActivityLevel.INACTIVE:
    case "inactive":
      return { color: "bg-red-400", label: "Inactive" };
    default:
      return { color: "bg-slate-300", label: "Unknown" };
  }
}

export function PersonCard({ person, onClick, className }: PersonCardProps) {
  const initials = getInitials(person.name);
  const gradient = getAvatarGradient(person.name);
  const activityDot = getActivityDot(person.activity_level);

  return (
    <div
      className={cn(
        "card-interactive group flex items-center gap-4",
        onClick && "cursor-pointer",
        className,
      )}
      onClick={() => onClick?.(person)}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick(person);
        }
      }}
    >
      {/* Avatar */}
      <div className="relative shrink-0">
        {person.avatar_url ? (
          <img
            src={person.avatar_url}
            alt={person.name}
            className="h-12 w-12 rounded-full object-cover ring-2 ring-white dark:ring-surface-dark-card"
          />
        ) : (
          <div
            className={cn(
              "flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white ring-2 ring-white dark:ring-surface-dark-card",
              gradient,
            )}
          >
            {initials}
          </div>
        )}
        {/* Activity dot */}
        <span
          className={cn(
            "absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white dark:border-surface-dark-card",
            activityDot.color,
          )}
          title={activityDot.label}
        />
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-sm font-semibold text-slate-900 group-hover:text-teal-700 dark:text-white dark:group-hover:text-teal-400">
            {person.name}
          </h3>
        </div>

        <div className="mt-0.5 flex items-center gap-2">
          <RoleBadge role={person.role} source={person.role_source} />
        </div>

        {person.department && (
          <p className="mt-1 truncate text-2xs text-slate-500 dark:text-slate-400">
            {person.department}
          </p>
        )}
      </div>

      {/* Task counts */}
      <div className="shrink-0 text-right">
        <div className="text-xs text-slate-500 dark:text-slate-400">
          <span className="font-semibold text-slate-700 dark:text-slate-200">
            {person.tasks_completed}
          </span>
          <span className="mx-0.5">/</span>
          <span>{person.tasks_assigned}</span>
        </div>
        <p className="text-2xs text-slate-400 dark:text-slate-500">tasks</p>
      </div>
    </div>
  );
}
