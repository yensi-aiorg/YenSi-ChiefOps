import { clsx, type ClassValue } from "clsx";
import {
  format,
  formatDistanceToNow,
  parseISO,
  isValid,
} from "date-fns";

/**
 * Merge class names with clsx (Tailwind-safe).
 * Combines clsx for conditional classes.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/**
 * Format a date string or Date object to a readable format.
 * @param date - ISO string or Date object
 * @param formatStr - date-fns format string (default: "MMM d, yyyy")
 * @returns Formatted date string, or "Invalid date" on failure
 */
export function formatDate(
  date: string | Date | null | undefined,
  formatStr: string = "MMM d, yyyy",
): string {
  if (!date) return "N/A";

  const parsed = typeof date === "string" ? parseISO(date) : date;
  if (!isValid(parsed)) return "Invalid date";

  return format(parsed, formatStr);
}

/**
 * Format a date as relative time (e.g., "3 hours ago", "in 2 days").
 * @param date - ISO string or Date object
 * @returns Relative time string
 */
export function formatRelativeTime(
  date: string | Date | null | undefined,
): string {
  if (!date) return "N/A";

  const parsed = typeof date === "string" ? parseISO(date) : date;
  if (!isValid(parsed)) return "Invalid date";

  return formatDistanceToNow(parsed, { addSuffix: true });
}

/**
 * Format a number with locale-appropriate separators.
 * @param value - The number to format
 * @param options - Intl.NumberFormat options
 * @returns Formatted number string
 */
export function formatNumber(
  value: number | null | undefined,
  options?: Intl.NumberFormatOptions,
): string {
  if (value === null || value === undefined) return "N/A";

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
    ...options,
  }).format(value);
}

/**
 * Format a number as a percentage.
 * @param value - The number (0-100 or 0-1 depending on isDecimal)
 * @param isDecimal - If true, value is treated as 0-1 range
 * @returns Formatted percentage string (e.g., "85.3%")
 */
export function formatPercentage(
  value: number | null | undefined,
  isDecimal: boolean = false,
): string {
  if (value === null || value === undefined) return "N/A";

  const pct = isDecimal ? value * 100 : value;

  return `${pct.toFixed(1)}%`;
}

/**
 * Truncate text to a maximum length, appending an ellipsis.
 * @param text - The text to truncate
 * @param maxLength - Maximum character count (default: 100)
 * @returns Truncated text with ellipsis if needed
 */
export function truncateText(text: string, maxLength: number = 100): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + "...";
}

/**
 * Get a Tailwind color class based on a health score (0-100).
 *
 * Score ranges:
 *   90-100  -> green (excellent)
 *   70-89   -> teal (good)
 *   50-69   -> yellow (warning)
 *   30-49   -> orange (concern)
 *   0-29    -> red (critical)
 *
 * @param score - Health score between 0 and 100
 * @returns Tailwind text color class string
 */
export function getHealthScoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-slate-400";

  if (score >= 90) return "text-green-600 dark:text-green-400";
  if (score >= 70) return "text-teal-600 dark:text-teal-400";
  if (score >= 50) return "text-yellow-600 dark:text-yellow-400";
  if (score >= 30) return "text-orange-600 dark:text-orange-400";
  return "text-red-600 dark:text-red-400";
}

/**
 * Get a Tailwind background/text color class based on a health score (0-100).
 * Useful for badges and indicators.
 *
 * @param score - Health score between 0 and 100
 * @returns Object with bg and text Tailwind classes
 */
export function getHealthScoreBadge(score: number | null | undefined): {
  bg: string;
  text: string;
  label: string;
} {
  if (score === null || score === undefined) {
    return { bg: "bg-slate-100 dark:bg-slate-800", text: "text-slate-500", label: "Unknown" };
  }

  if (score >= 90) {
    return {
      bg: "bg-green-100 dark:bg-green-900/40",
      text: "text-green-700 dark:text-green-400",
      label: "Excellent",
    };
  }
  if (score >= 70) {
    return {
      bg: "bg-teal-100 dark:bg-teal-900/40",
      text: "text-teal-700 dark:text-teal-400",
      label: "Good",
    };
  }
  if (score >= 50) {
    return {
      bg: "bg-yellow-100 dark:bg-yellow-900/40",
      text: "text-yellow-700 dark:text-yellow-400",
      label: "Fair",
    };
  }
  if (score >= 30) {
    return {
      bg: "bg-orange-100 dark:bg-orange-900/40",
      text: "text-orange-700 dark:text-orange-400",
      label: "At Risk",
    };
  }
  return {
    bg: "bg-red-100 dark:bg-red-900/40",
    text: "text-red-700 dark:text-red-400",
    label: "Critical",
  };
}

/**
 * Get a Tailwind color class based on activity level.
 *
 * Levels: "high" | "medium" | "low" | "inactive"
 *
 * @param level - The activity level string
 * @returns Tailwind text color class string
 */
export function getActivityLevelColor(
  level: string | null | undefined,
): string {
  if (!level) return "text-slate-400";

  switch (level.toLowerCase()) {
    case "high":
      return "text-green-600 dark:text-green-400";
    case "medium":
      return "text-teal-600 dark:text-teal-400";
    case "low":
      return "text-yellow-600 dark:text-yellow-400";
    case "inactive":
      return "text-slate-400 dark:text-slate-500";
    default:
      return "text-slate-500 dark:text-slate-400";
  }
}

/**
 * Get initials from a full name (e.g., "John Doe" -> "JD").
 * @param name - Full name string
 * @returns Initials (1-2 characters, uppercase)
 */
export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0 || !parts[0]) return "?";

  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1]?.[0] ?? "" : "";

  return (first + last).toUpperCase();
}

/**
 * Debounce a function call.
 * @param fn - The function to debounce
 * @param delay - Delay in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: Parameters<T>) => void>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}
