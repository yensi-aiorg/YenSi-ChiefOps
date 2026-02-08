import { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Users,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Upload,
  ArrowRight,
  X,
} from "lucide-react";
import { usePeopleStore } from "@/stores/peopleStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn, debounce, getInitials } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/utils";
import type { Person, ActivityLevel } from "@/types";

/* ================================================================== */
/*  Activity level badge                                               */
/* ================================================================== */

const activityStyles: Record<string, { bg: string; label: string }> = {
  very_active: {
    bg: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
    label: "Very Active",
  },
  active: {
    bg: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-400",
    label: "Active",
  },
  moderate: {
    bg: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
    label: "Moderate",
  },
  quiet: {
    bg: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    label: "Quiet",
  },
  inactive: {
    bg: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
    label: "Inactive",
  },
};

function ActivityBadge({ level }: { level: string }) {
  const cfg = activityStyles[level] ?? activityStyles.moderate;
  return <span className={cn("badge text-2xs", cfg.bg)}>{cfg.label}</span>;
}

/* ================================================================== */
/*  Person Card                                                        */
/* ================================================================== */

function PersonCard({ person }: { person: Person }) {
  const navigate = useNavigate();
  const initials = getInitials(person.name);
  const completionRate =
    person.tasks_assigned > 0
      ? Math.round((person.tasks_completed / person.tasks_assigned) * 100)
      : 0;

  return (
    <button
      onClick={() => navigate(`/people/${person.person_id}`)}
      className="card-interactive w-full text-left"
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        {person.avatar_url ? (
          <img
            src={person.avatar_url}
            alt={person.name}
            className="h-11 w-11 flex-shrink-0 rounded-full object-cover"
          />
        ) : (
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-chief-500 text-sm font-bold text-white">
            {initials}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-slate-900 dark:text-white">
              {person.name}
            </h3>
            <ActivityBadge level={person.activity_level} />
          </div>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {person.role}
            {person.department && ` -- ${person.department}`}
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
        <div>
          <p className="text-2xs text-slate-400 dark:text-slate-500">Tasks</p>
          <p className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-300">
            {person.tasks_completed}/{person.tasks_assigned}
          </p>
        </div>
        <div>
          <p className="text-2xs text-slate-400 dark:text-slate-500">
            Completion
          </p>
          <p className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-300">
            {completionRate}%
          </p>
        </div>
        <div>
          <p className="text-2xs text-slate-400 dark:text-slate-500">
            Last Active
          </p>
          <p className="truncate text-sm text-slate-700 dark:text-slate-300">
            {formatRelativeTime(person.last_active_date)}
          </p>
        </div>
      </div>

      {/* Projects */}
      {person.projects.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {person.projects.slice(0, 3).map((pid) => (
            <span
              key={pid}
              className="badge-neutral text-2xs"
            >
              {pid.slice(0, 8)}
            </span>
          ))}
          {person.projects.length > 3 && (
            <span className="text-2xs text-slate-400">
              +{person.projects.length - 3}
            </span>
          )}
        </div>
      )}
    </button>
  );
}

/* ================================================================== */
/*  Skeleton card                                                      */
/* ================================================================== */

function SkeletonPersonCard() {
  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-3">
        <div className="skeleton h-11 w-11 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-28" />
          <div className="skeleton h-3 w-40" />
        </div>
      </div>
      <div className="skeleton h-px w-full" />
      <div className="grid grid-cols-3 gap-2">
        <div className="skeleton h-8 w-full" />
        <div className="skeleton h-8 w-full" />
        <div className="skeleton h-8 w-full" />
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Filter Bar                                                         */
/* ================================================================== */

const activityOptions: { value: string; label: string }[] = [
  { value: "", label: "All Activity" },
  { value: "very_active", label: "Very Active" },
  { value: "active", label: "Active" },
  { value: "moderate", label: "Moderate" },
  { value: "quiet", label: "Quiet" },
  { value: "inactive", label: "Inactive" },
];

/* ================================================================== */
/*  People Directory Page                                              */
/* ================================================================== */

export function PeopleDirectory() {
  const {
    people,
    total,
    filters,
    isLoading,
    fetchPeople,
    setFilters,
    setSelectedPerson,
  } = usePeopleStore();

  const { projects, fetchProjects } = useProjectStore();

  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 20;

  // Initial fetch
  useEffect(() => {
    fetchPeople();
    fetchProjects();
  }, [fetchPeople, fetchProjects]);

  // Debounced search
  const debouncedSearch = useMemo(
    () =>
      debounce((query: string) => {
        setPage(0);
        // search is passed as part of filters or via query param
        // The store's fetchPeople reads filters from state,
        // so we add search to the filter params
        const params: Record<string, string | number> = {
          skip: 0,
          limit: pageSize,
        };
        if (filters.activity_level) params.activity_level = filters.activity_level;
        if (filters.department) params.department = filters.department;
        if (filters.project_id) params.project_id = filters.project_id;
        if (query) params.search = query;
        fetchPeople(undefined, 0, pageSize);
      }, 300),
    [filters, fetchPeople, pageSize],
  );

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchInput(value);
      debouncedSearch(value);
    },
    [debouncedSearch],
  );

  const handleActivityFilter = useCallback(
    (value: string) => {
      setPage(0);
      setFilters({
        ...filters,
        activity_level: value ? (value as ActivityLevel) : undefined,
      });
      fetchPeople(
        {
          ...filters,
          activity_level: value ? (value as ActivityLevel) : undefined,
        },
        0,
        pageSize,
      );
    },
    [filters, setFilters, fetchPeople, pageSize],
  );

  const handleDepartmentFilter = useCallback(
    (value: string) => {
      setPage(0);
      setFilters({ ...filters, department: value || undefined });
      fetchPeople(
        { ...filters, department: value || undefined },
        0,
        pageSize,
      );
    },
    [filters, setFilters, fetchPeople, pageSize],
  );

  const handleProjectFilter = useCallback(
    (value: string) => {
      setPage(0);
      setFilters({ ...filters, project_id: value || undefined });
      fetchPeople(
        { ...filters, project_id: value || undefined },
        0,
        pageSize,
      );
    },
    [filters, setFilters, fetchPeople, pageSize],
  );

  const handlePageChange = useCallback(
    (newPage: number) => {
      setPage(newPage);
      fetchPeople(filters, newPage * pageSize, pageSize);
    },
    [filters, fetchPeople, pageSize],
  );

  const clearAllFilters = useCallback(() => {
    setSearchInput("");
    setPage(0);
    setFilters({});
    fetchPeople({}, 0, pageSize);
  }, [setFilters, fetchPeople, pageSize]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const hasActiveFilters =
    !!filters.activity_level ||
    !!filters.department ||
    !!filters.project_id ||
    !!searchInput;

  // Derive department list from loaded people
  const departments = useMemo(() => {
    const set = new Set<string>();
    people.forEach((p) => {
      if (p.department) set.add(p.department);
    });
    return Array.from(set).sort();
  }, [people]);

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          People Directory
        </h1>
        {total > 0 && (
          <span className="badge-neutral ml-2">{total} people</span>
        )}
      </div>

      {/* Filter bar */}
      <div className="card flex flex-wrap items-center gap-3 p-4">
        {/* Search */}
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search by name, role, email..."
            className="input pl-10"
          />
        </div>

        {/* Activity level dropdown */}
        <select
          value={filters.activity_level ?? ""}
          onChange={(e) => handleActivityFilter(e.target.value)}
          className="input w-auto min-w-[140px]"
        >
          {activityOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Department dropdown */}
        <select
          value={filters.department ?? ""}
          onChange={(e) => handleDepartmentFilter(e.target.value)}
          className="input w-auto min-w-[140px]"
        >
          <option value="">All Departments</option>
          {departments.map((dept) => (
            <option key={dept} value={dept}>
              {dept}
            </option>
          ))}
        </select>

        {/* Project dropdown */}
        <select
          value={filters.project_id ?? ""}
          onChange={(e) => handleProjectFilter(e.target.value)}
          className="input w-auto min-w-[140px]"
        >
          <option value="">All Projects</option>
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.name}
            </option>
          ))}
        </select>

        {/* Clear filters */}
        {hasActiveFilters && (
          <button onClick={clearAllFilters} className="btn-ghost gap-1 text-xs">
            <X className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* Loading skeletons */}
      {isLoading && people.length === 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonPersonCard key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && people.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
            <Users className="h-10 w-10 text-teal-600 dark:text-teal-400" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
            {hasActiveFilters
              ? "No people match your filters"
              : "Upload data to discover your team"}
          </h2>
          <p className="mb-6 max-w-md text-sm text-slate-500 dark:text-slate-400">
            {hasActiveFilters
              ? "Try adjusting your filters or clearing them to see all team members."
              : "Upload your Slack exports and Jira CSVs. ChiefOps will automatically identify team members, roles, and activity levels."}
          </p>
          {hasActiveFilters ? (
            <button onClick={clearAllFilters} className="btn-secondary">
              Clear Filters
            </button>
          ) : (
            <Link to="/upload" className="btn-primary">
              <Upload className="h-4 w-4" />
              Upload Data
            </Link>
          )}
        </div>
      )}

      {/* Person cards grid */}
      {people.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {people.map((person) => (
            <PersonCard key={person.person_id} person={person} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Showing {page * pageSize + 1}--
            {Math.min((page + 1) * pageSize, total)} of {total}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page === 0}
              className="btn-ghost p-2 disabled:opacity-40"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }).map((_, i) => {
              const pageNum =
                totalPages <= 7
                  ? i
                  : page <= 3
                    ? i
                    : page >= totalPages - 4
                      ? totalPages - 7 + i
                      : page - 3 + i;
              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={cn(
                    "btn-ghost h-8 w-8 p-0 text-xs",
                    pageNum === page &&
                      "bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
                  )}
                >
                  {pageNum + 1}
                </button>
              );
            })}
            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages - 1}
              className="btn-ghost p-2 disabled:opacity-40"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
