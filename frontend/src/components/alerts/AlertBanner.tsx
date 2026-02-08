import { useState, useEffect } from "react";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  X,
} from "lucide-react";
import { useAlertStore } from "@/stores/alertStore";
import { AlertSeverity } from "@/types";
import type { AlertTriggered } from "@/types";
import { cn, formatRelativeTime } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  AlertBanner – positioned below TopBar, shows active alerts         */
/* ------------------------------------------------------------------ */

interface AlertBannerProps {
  className?: string;
}

function getSeverityConfig(severity: AlertSeverity | string) {
  const s = (typeof severity === "string" ? severity : String(severity)).toLowerCase();
  switch (s) {
    case "critical":
    case AlertSeverity.CRITICAL:
      return {
        icon: AlertCircle,
        bg: "bg-red-50 dark:bg-red-900/15",
        border: "border-red-200 dark:border-red-800",
        text: "text-red-800 dark:text-red-300",
        iconColor: "text-red-500",
        badge: "bg-red-500",
      };
    case "warning":
    case AlertSeverity.WARNING:
      return {
        icon: AlertTriangle,
        bg: "bg-amber-50 dark:bg-amber-900/15",
        border: "border-amber-200 dark:border-amber-800",
        text: "text-amber-800 dark:text-amber-300",
        iconColor: "text-amber-500",
        badge: "bg-amber-500",
      };
    case "info":
    case AlertSeverity.INFO:
    default:
      return {
        icon: Info,
        bg: "bg-blue-50 dark:bg-blue-900/15",
        border: "border-blue-200 dark:border-blue-800",
        text: "text-blue-800 dark:text-blue-300",
        iconColor: "text-blue-500",
        badge: "bg-blue-500",
      };
  }
}

/** Determine the most severe active alert for the banner color. */
function getMostSevereSeverity(
  alerts: { severity: AlertSeverity | string }[],
): AlertSeverity | string {
  const severityOrder = ["critical", "warning", "info"];
  for (const level of severityOrder) {
    if (
      alerts.some(
        (a) =>
          String(a.severity).toLowerCase() === level,
      )
    ) {
      return level;
    }
  }
  return "info";
}

export function AlertBanner({ className }: AlertBannerProps) {
  const { triggeredAlerts, fetchTriggeredAlerts, dismissAlert } =
    useAlertStore();
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchTriggeredAlerts();
  }, [fetchTriggeredAlerts]);

  // Filter to only non-acknowledged alerts
  const activeAlerts: AlertTriggered[] = triggeredAlerts.filter(
    (a) => !a.acknowledged,
  );

  if (activeAlerts.length === 0) {
    return null;
  }

  const bannerSeverity = getMostSevereSeverity(activeAlerts as { severity: AlertSeverity | string }[]);
  const bannerConfig = getSeverityConfig(bannerSeverity);
  const BannerIcon = bannerConfig.icon;

  return (
    <div
      className={cn(
        "overflow-hidden border-b transition-all duration-300",
        bannerConfig.bg,
        bannerConfig.border,
        className,
      )}
    >
      {/* Summary row */}
      <div className="flex items-center gap-3 px-4 py-2.5 lg:px-6">
        <div className="flex items-center gap-2">
          <BannerIcon className={cn("h-4.5 w-4.5", bannerConfig.iconColor)} />
          <span
            className={cn("text-sm font-medium", bannerConfig.text)}
          >
            {activeAlerts.length} active alert{activeAlerts.length !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="flex flex-1 items-center justify-end gap-2">
          {activeAlerts.length > 1 && (
            <button
              onClick={() => activeAlerts.forEach((a) => dismissAlert(a.trigger_id))}
              className="text-xs font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              Dismiss all
            </button>
          )}
          <button
            onClick={() => setExpanded((e) => !e)}
            className={cn(
              "flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition-colors",
              bannerConfig.text,
              "hover:bg-white/50 dark:hover:bg-white/5",
            )}
          >
            {expanded ? (
              <>
                <span>Hide</span>
                <ChevronUp className="h-3.5 w-3.5" />
              </>
            ) : (
              <>
                <span>Show</span>
                <ChevronDown className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Expanded alert list */}
      {expanded && (
        <div className="border-t border-slate-200/50 px-4 pb-3 pt-2 dark:border-slate-700/50 lg:px-6">
          <div className="space-y-2">
            {activeAlerts.map((alert) => {
              const config = getSeverityConfig(alert.severity);
              const Icon = config.icon;
              const triggerId = alert.trigger_id;

              return (
                <div
                  key={triggerId}
                  className="flex items-start gap-3 rounded-lg bg-white/60 px-3 py-2.5 dark:bg-slate-800/40"
                >
                  <Icon
                    className={cn("mt-0.5 h-4 w-4 shrink-0", config.iconColor)}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {alert.message}
                    </p>
                    <p className="mt-0.5 text-2xs text-slate-500 dark:text-slate-400">
                      {formatRelativeTime(alert.triggered_at)}
                    </p>
                  </div>
                  <button
                    onClick={() => dismissAlert(triggerId)}
                    className="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-300"
                    aria-label="Dismiss alert"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
