import { useState, useCallback, useMemo, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Bell, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAlertStore } from "@/stores/alertStore";

/* ------------------------------------------------------------------ */
/*  TopBar component                                                   */
/* ------------------------------------------------------------------ */

export interface TopBarProps {
  /** Whether the sidebar is collapsed (adjusts left offset) */
  sidebarCollapsed?: boolean;
  /** Whether the chat panel is open */
  chatOpen?: boolean;
  /** Toggle the chat panel */
  onToggleChat?: () => void;
}

export function TopBar({
  sidebarCollapsed = false,
  chatOpen = false,
  onToggleChat,
}: TopBarProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");

  const triggeredAlerts = useAlertStore((s) => s.triggeredAlerts);

  /** Count of non-dismissed triggered alerts */
  const unreadCount = useMemo(
    () => triggeredAlerts.filter((a) => !a.acknowledged).length,
    [triggeredAlerts],
  );

  const handleSearchSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const trimmed = searchQuery.trim();
      if (trimmed) {
        navigate(`/chat?q=${encodeURIComponent(trimmed)}`);
        setSearchQuery("");
      }
    },
    [searchQuery, navigate],
  );

  return (
    <header
      className={cn(
        "fixed right-0 top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/80 px-4 backdrop-blur-lg transition-all duration-300 dark:border-slate-700 dark:bg-slate-900/80 lg:px-6",
        sidebarCollapsed ? "left-[72px]" : "left-[260px]",
        chatOpen && "lg:right-[380px]",
      )}
    >
      {/* ── Left: Search ─────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search people, projects, reports..."
            className="w-64 rounded-lg border border-slate-200 bg-slate-50 py-2 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-teal-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-teal-400 lg:w-80"
          />
        </form>
      </div>

      {/* ── Right: Actions ───────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Alert bell */}
        <button
          className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-none text-white shadow-sm">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>

        {/* Chat toggle */}
        <button
          onClick={onToggleChat}
          className={cn(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all",
            chatOpen
              ? "bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400"
              : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800",
          )}
          aria-label={chatOpen ? "Close AI Chat" : "Open AI Chat"}
        >
          <MessageSquare className="h-5 w-5" />
          <span className="hidden sm:inline">AI Chat</span>
        </button>
      </div>
    </header>
  );
}
