/**
 * Widget and dashboard types for the ChiefOps frontend.
 *
 * These TypeScript interfaces and enums mirror the backend Pydantic models
 * for the dynamic widget system, dashboards, and all widget data shapes
 * (charts, tables, KPIs, grids, timelines, and activity feeds).
 */

import type { ActivityLevel } from "./models";

// ===========================================================================
// Widget Enums
// ===========================================================================

/** Visualization types supported by the widget renderer. */
export enum WidgetType {
  BAR_CHART = "bar_chart",
  LINE_CHART = "line_chart",
  PIE_CHART = "pie_chart",
  GANTT = "gantt",
  TABLE = "table",
  KPI_CARD = "kpi_card",
  SUMMARY_TEXT = "summary_text",
  PERSON_GRID = "person_grid",
  TIMELINE = "timeline",
  ACTIVITY_FEED = "activity_feed",
}

/** How a data query aggregates its results. */
export enum QueryType {
  COUNT = "count",
  GROUP_COUNT = "group_count",
  TIME_SERIES = "time_series",
  TOP_N = "top_n",
  AGGREGATE = "aggregate",
}

/** How a widget was created. */
export enum WidgetCreator {
  COO_CONVERSATION = "coo_conversation",
  SYSTEM_DEFAULT = "system_default",
}

/** Dashboard level classification. */
export enum DashboardType {
  MAIN = "main",
  PROJECT_STATIC = "project_static",
  PROJECT_CUSTOM = "project_custom",
}

// ===========================================================================
// Widget Spec & Data Query
// ===========================================================================

/** Grid position for dashboard layout (12-column grid). */
export interface WidgetPosition {
  row: number;
  col: number;
  width: number;
  height: number;
}

/**
 * Defines what data to fetch and how to aggregate it for a widget.
 * The backend resolves this into MongoDB aggregation pipelines at render time.
 */
export interface DataQuery {
  collection: string;
  query_type: QueryType;
  match_filters: Record<string, unknown>;
  group_by: string | null;
  sort_by: string | null;
  sort_order: "asc" | "desc";
  limit: number | null;
  date_field: string | null;
  date_bucket: "hour" | "day" | "week" | "month" | null;
  aggregation: string | null;
}

/**
 * A dynamic widget specification stored in the dashboard_widgets collection.
 * The widget_type field determines which React component renders it.
 * The data_query field tells the backend what data to fetch.
 */
export interface WidgetSpec {
  widget_id: string;
  dashboard_id: string;
  widget_type: WidgetType;
  title: string;
  description: string;
  position: WidgetPosition;
  data_query: DataQuery;
  display_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ===========================================================================
// Dashboard
// ===========================================================================

/**
 * A dashboard containing an ordered set of widgets.
 * Dashboards can be the main global view, a fixed per-project static view,
 * or a fully customizable per-project view managed through conversation.
 */
export interface Dashboard {
  dashboard_id: string;
  project_id: string | null;
  dashboard_type: DashboardType;
  name: string;
  widget_ids: string[];
  layout: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ===========================================================================
// Chart Data Shapes
// ===========================================================================

/** A single data point for bar, pie, or donut charts. */
export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

/** A single data point in a time-series chart with optional series grouping. */
export interface TimeSeriesPoint {
  date: string;
  value: number;
  series?: string;
}

// ===========================================================================
// KPI Data Shape
// ===========================================================================

/** Trend direction for KPI cards. */
export type TrendDirection = "up" | "down" | "flat";

/** Data shape for KPI card widgets. */
export interface KpiData {
  value: number;
  label: string;
  trend_direction: TrendDirection;
  trend_value: number;
  trend_percentage: number;
}

// ===========================================================================
// Table Data Shape
// ===========================================================================

/** Column definition for table widgets. */
export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  type?: "string" | "number" | "date" | "badge" | "progress";
}

/** Data shape for table widgets. */
export interface TableData {
  columns: TableColumn[];
  rows: Record<string, unknown>[];
}

// ===========================================================================
// Gantt Data Shape
// ===========================================================================

/** A single item (bar) in a Gantt chart. */
export interface GanttItem {
  id: string;
  name: string;
  start: string;
  end: string;
  progress: number;
  status: string;
  assignee?: string;
}

// ===========================================================================
// Person Grid Data Shape
// ===========================================================================

/** A person card for the person grid widget. */
export interface PersonGridItem {
  person_id: string;
  name: string;
  role: string;
  avatar_url: string | null;
  tasks_assigned: number;
  tasks_completed: number;
  completion_rate: number;
  last_active: string;
  activity_level: ActivityLevel;
}

// ===========================================================================
// Timeline Data Shape
// ===========================================================================

/** A single event in a vertical timeline widget. */
export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  detail: string;
  icon?: string;
}

// ===========================================================================
// Activity Feed Data Shape
// ===========================================================================

/** A single item in the activity feed widget. */
export interface ActivityFeedItem {
  id: string;
  source: string;
  timestamp: string;
  actor: string;
  action: string;
  detail: string;
}
