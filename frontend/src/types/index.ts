/**
 * Central type barrel for the ChiefOps frontend.
 *
 * Re-exports every type, interface, and enum from the domain-specific
 * type modules so consumers can import from "@/types" directly.
 */

// API response wrappers, health checks, and error shapes
export type {
  ApiResponse,
  PaginatedResponse,
  HealthStatus,
  DependencyDetail,
  ReadinessStatus,
  SSEEvent,
  ApiError,
} from "./api";

// Domain model types and enums
export {
  SourceSystem,
  RoleSource,
  ActivityLevel,
  ProjectStatus,
  MilestoneStatus,
  IngestionFileType,
  IngestionFileStatus,
  IngestionStatus,
  TurnSource,
  PageContext,
  TurnRole,
  FactType,
  AlertSeverity,
  AlertStatus,
  ReportType,
  SectionType,
  ReportStatus,
} from "./models";

export type {
  SourceReference,
  EngagementMetrics,
  Person,
  Milestone,
  ProjectMember,
  TaskSummary,
  SprintHealth,
  BackwardPlanItem,
  GapAnalysis,
  ReadinessItem,
  RiskItem,
  TechnicalFeasibility,
  Project,
  IngestionFileResult,
  IngestionJob,
  SourceUsed,
  ConversationTurn,
  HardFact,
  Alert,
  AlertTriggered,
  ReportSection,
  ReportSpec,
  AppSettings,
  PeopleFilters,
  ProjectFileInfo,
} from "./models";

// Widget and dashboard types and enums
export {
  WidgetType,
  QueryType,
  WidgetCreator,
  DashboardType,
} from "./widgets";

export type {
  WidgetPosition,
  DataQuery,
  WidgetSpec,
  Dashboard,
  ChartDataPoint,
  TimeSeriesPoint,
  TrendDirection,
  KpiData,
  TableColumn,
  TableData,
  GanttItem,
  PersonGridItem,
  TimelineEvent,
  ActivityFeedItem,
} from "./widgets";
