import { useState, useCallback } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Users,
  FolderKanban,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Hexagon,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Navigation items                                                   */
/* ------------------------------------------------------------------ */

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Upload Data", path: "/upload", icon: Upload },
  { label: "People", path: "/people", icon: Users },
  { label: "Projects", path: "/projects", icon: FolderKanban },
  { label: "Reports", path: "/reports", icon: FileText },
  { label: "Settings", path: "/settings", icon: Settings },
];

/* ------------------------------------------------------------------ */
/*  Sidebar component                                                  */
/* ------------------------------------------------------------------ */

const APP_VERSION = "1.0.0";

export interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ collapsed: controlledCollapsed, onToggle }: SidebarProps) {
  const [internalCollapsed, setInternalCollapsed] = useState(false);

  const isCollapsed = controlledCollapsed ?? internalCollapsed;

  const handleToggle = useCallback(() => {
    if (onToggle) {
      onToggle();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  }, [onToggle]);

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-30 flex h-full flex-col bg-slate-900 text-white transition-all duration-300",
        isCollapsed ? "w-[72px]" : "w-[260px]",
      )}
    >
      {/* ── Logo / Brand ────────────────────────────────────────── */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-700/60 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-teal-600 shadow-lg shadow-teal-500/20">
          <Hexagon className="h-5 w-5 text-white" strokeWidth={2.5} />
        </div>

        {!isCollapsed && (
          <div className="animate-fade-in overflow-hidden">
            <h1 className="text-lg font-bold tracking-tight text-white">
              ChiefOps
            </h1>
            <p className="text-[10px] leading-tight text-slate-400">
              AI Chief of Staff
            </p>
          </div>
        )}
      </div>

      {/* ── Navigation links ────────────────────────────────────── */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4 scrollbar-none">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isCollapsed && "justify-center px-2",
                isActive
                  ? "bg-teal-500/15 text-teal-400 shadow-inner shadow-teal-500/5"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn(
                    "h-5 w-5 shrink-0 transition-colors",
                    isActive
                      ? "text-teal-400"
                      : "text-slate-500 group-hover:text-white",
                  )}
                />
                {!isCollapsed && (
                  <span className="animate-fade-in truncate">
                    {item.label}
                  </span>
                )}

                {/* Active indicator bar */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r-full bg-teal-400" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* ── Collapse toggle + version ───────────────────────────── */}
      <div className="border-t border-slate-700/60 p-3">
        {/* Version info */}
        {!isCollapsed && (
          <div className="mb-2 animate-fade-in px-3">
            <p className="text-[10px] text-slate-500">
              v{APP_VERSION}
            </p>
          </div>
        )}

        <button
          onClick={handleToggle}
          className={cn(
            "flex w-full items-center rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-800 hover:text-slate-300",
            isCollapsed ? "justify-center" : "justify-between px-3",
          )}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {!isCollapsed && (
            <span className="text-xs text-slate-500">Collapse</span>
          )}
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>
    </aside>
  );
}
