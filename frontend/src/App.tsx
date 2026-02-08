import { useState, useCallback, lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  Users,
  FolderKanban,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  X,
  Menu,
  Search,
  Bell,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NavLink } from "react-router-dom";

/* ------------------------------------------------------------------ */
/*  Lazy-loaded page components                                       */
/* ------------------------------------------------------------------ */
const MainDashboard = lazy(() =>
  import("@/pages/MainDashboard").then((m) => ({ default: m.MainDashboard })),
);
const DataUpload = lazy(() =>
  import("@/pages/DataUpload").then((m) => ({ default: m.DataUpload })),
);
const PeopleDirectory = lazy(() =>
  import("@/pages/PeopleDirectory").then((m) => ({
    default: m.PeopleDirectory,
  })),
);
const PersonDetail = lazy(() =>
  import("@/pages/PersonDetail").then((m) => ({ default: m.PersonDetail })),
);
const ProjectDetail = lazy(() =>
  import("@/pages/ProjectDetail").then((m) => ({ default: m.ProjectDetail })),
);
const CustomDashboard = lazy(() =>
  import("@/pages/CustomDashboard").then((m) => ({
    default: m.CustomDashboard,
  })),
);
const ReportList = lazy(() =>
  import("@/pages/ReportList").then((m) => ({ default: m.ReportList })),
);
const ReportPreview = lazy(() =>
  import("@/pages/ReportPreview").then((m) => ({ default: m.ReportPreview })),
);
const SettingsPage = lazy(() =>
  import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);

/* ------------------------------------------------------------------ */
/*  Navigation items                                                  */
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
/*  Loading fallback                                                  */
/* ------------------------------------------------------------------ */
function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span className="text-sm text-slate-500 dark:text-slate-400">
          Loading...
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sidebar component                                                 */
/* ------------------------------------------------------------------ */
interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-30 flex h-full flex-col border-r border-slate-200 bg-white transition-all duration-300 dark:border-slate-700 dark:bg-surface-dark",
        collapsed ? "w-sidebar-collapsed" : "w-sidebar",
      )}
    >
      {/* Logo area */}
      <div className="flex h-topbar items-center gap-3 border-b border-slate-200 px-4 dark:border-slate-700">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-chief-600 text-sm font-bold text-white">
          CO
        </div>
        {!collapsed && (
          <div className="animate-fade-in overflow-hidden">
            <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
              ChiefOps
            </h1>
            <p className="text-2xs text-slate-500 dark:text-slate-400">
              AI Chief of Staff
            </p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                collapsed && "justify-center px-2",
                isActive
                  ? "bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200",
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && (
              <span className="animate-fade-in truncate">{item.label}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-slate-200 p-3 dark:border-slate-700">
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </button>
      </div>
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/*  TopBar component                                                  */
/* ------------------------------------------------------------------ */
interface TopBarProps {
  sidebarCollapsed: boolean;
  chatOpen: boolean;
  onToggleChat: () => void;
  onToggleMobileSidebar: () => void;
}

function TopBar({
  sidebarCollapsed,
  chatOpen,
  onToggleChat,
  onToggleMobileSidebar,
}: TopBarProps) {
  return (
    <header
      className={cn(
        "fixed right-0 top-0 z-20 flex h-topbar items-center justify-between border-b border-slate-200 bg-white/80 px-4 backdrop-blur-lg transition-all duration-300 dark:border-slate-700 dark:bg-surface-dark/80 lg:px-6",
        sidebarCollapsed ? "left-sidebar-collapsed" : "left-sidebar",
        chatOpen && "lg:right-chat-sidebar",
      )}
    >
      <div className="flex items-center gap-3">
        {/* Mobile menu button */}
        <button
          onClick={onToggleMobileSidebar}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
          aria-label="Toggle mobile menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Search */}
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search people, projects, reports..."
            className="input w-64 pl-10 lg:w-80"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Notifications */}
        <button
          className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-warm-500" />
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

/* ------------------------------------------------------------------ */
/*  ChatSidebar placeholder component                                 */
/* ------------------------------------------------------------------ */
interface ChatSidebarProps {
  open: boolean;
  onClose: () => void;
}

function ChatSidebar({ open, onClose }: ChatSidebarProps) {
  if (!open) return null;

  return (
    <aside className="fixed bottom-0 right-0 top-0 z-40 flex w-chat-sidebar flex-col border-l border-slate-200 bg-white shadow-lg transition-transform duration-300 dark:border-slate-700 dark:bg-surface-dark lg:z-20">
      <div className="flex h-topbar items-center justify-between border-b border-slate-200 px-4 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-chief-600">
            <MessageSquare className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-slate-900 dark:text-white">
            ChiefOps AI
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          aria-label="Close chat"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
            <MessageSquare className="h-7 w-7 text-teal-600 dark:text-teal-400" />
          </div>
          <h3 className="mb-1 text-sm font-semibold text-slate-900 dark:text-white">
            AI Assistant Ready
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Ask questions about your team, projects, or request reports.
          </p>
        </div>
      </div>

      <div className="border-t border-slate-200 p-4 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask ChiefOps AI..."
            className="input flex-1"
          />
          <button className="btn-primary shrink-0 px-3">Send</button>
        </div>
      </div>
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/*  App component                                                     */
/* ------------------------------------------------------------------ */
export function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [_mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const toggleChat = useCallback(() => {
    setChatOpen((prev) => !prev);
  }, []);

  const toggleMobileSidebar = useCallback(() => {
    setMobileSidebarOpen((prev) => !prev);
  }, []);

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />

      {/* Main area */}
      <div
        className={cn(
          "flex min-h-full flex-1 flex-col transition-all duration-300",
          sidebarCollapsed ? "ml-sidebar-collapsed" : "ml-sidebar",
          chatOpen && "lg:mr-chat-sidebar",
        )}
      >
        {/* TopBar */}
        <TopBar
          sidebarCollapsed={sidebarCollapsed}
          chatOpen={chatOpen}
          onToggleChat={toggleChat}
          onToggleMobileSidebar={toggleMobileSidebar}
        />

        {/* Page content */}
        <main className="flex-1 overflow-y-auto pt-topbar">
          <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<MainDashboard />} />
                <Route path="/upload" element={<DataUpload />} />
                <Route path="/people" element={<PeopleDirectory />} />
                <Route path="/people/:personId" element={<PersonDetail />} />
                <Route
                  path="/projects/:projectId"
                  element={<ProjectDetail />}
                />
                <Route
                  path="/projects/:projectId/custom"
                  element={<CustomDashboard />}
                />
                <Route path="/reports" element={<ReportList />} />
                <Route path="/reports/:reportId" element={<ReportPreview />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>

      {/* Chat sidebar */}
      <ChatSidebar open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  );
}
