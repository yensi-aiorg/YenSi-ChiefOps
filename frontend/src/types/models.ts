/**
 * Domain model types for the ChiefOps frontend.
 *
 * These TypeScript interfaces and enums mirror the backend Pydantic models
 * defined in backend/app/models/. They cover people, projects, ingestion,
 * conversations, alerts, reports, and application settings.
 */

// ===========================================================================
// Shared Enums
// ===========================================================================

/** Data source systems integrated with ChiefOps. */
export enum SourceSystem {
  SLACK = "slack",
  JIRA = "jira",
  GDRIVE = "gdrive",
}

/** How a person's role was determined. */
export enum RoleSource {
  AI_IDENTIFIED = "ai_identified",
  COO_CORRECTED = "coo_corrected",
}

/**
 * Computed activity level based on message frequency, task activity,
 * and recency of interactions across all integrated sources.
 */
export enum ActivityLevel {
  VERY_ACTIVE = "very_active",
  ACTIVE = "active",
  MODERATE = "moderate",
  QUIET = "quiet",
  INACTIVE = "inactive",
}

/** Overall project health status. */
export enum ProjectStatus {
  ON_TRACK = "on_track",
  AT_RISK = "at_risk",
  BEHIND = "behind",
  COMPLETED = "completed",
}

/** Lifecycle status of a project milestone. */
export enum MilestoneStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  MISSED = "missed",
}

// ===========================================================================
// People
// ===========================================================================

/** Links a person record back to their identity in a source system. */
export interface SourceReference {
  source: SourceSystem;
  source_id: string;
}

/** Slack-derived engagement statistics for a person. */
export interface EngagementMetrics {
  messages_sent: number;
  threads_replied: number;
  reactions_given: number;
}

/**
 * Unified person record. One document per real human, regardless of how many
 * source systems they appear in. Identity resolution merges Slack users,
 * Jira assignees, and Drive file owners into a single record.
 */
export interface Person {
  person_id: string;
  name: string;
  email: string | null;
  source_ids: SourceReference[];
  role: string;
  role_source: RoleSource;
  department: string | null;
  activity_level: ActivityLevel;
  last_active_date: string;
  avatar_url: string | null;
  slack_user_id: string | null;
  jira_username: string | null;
  tasks_assigned: number;
  tasks_completed: number;
  engagement_metrics: EngagementMetrics;
  projects: string[];
  created_at: string;
  updated_at: string;
}

// ===========================================================================
// Projects
// ===========================================================================

/** A project milestone with a target date and current status. */
export interface Milestone {
  name: string;
  target_date: string;
  status: MilestoneStatus;
  description: string;
}

/** A person's involvement in a specific project. */
export interface ProjectMember {
  person_id: string;
  name: string;
  role: string;
  activity_level: string;
}

/** Aggregated task counts for a project, broken down by status. */
export interface TaskSummary {
  total: number;
  completed: number;
  in_progress: number;
  blocked: number;
  to_do: number;
}

/** Sprint-level health metrics for a project. */
export interface SprintHealth {
  completion_rate: number;
  velocity_trend: string;
  blocker_count: number;
  score: number;
}

/** A single item in a backward plan derived from gap analysis. */
export interface BackwardPlanItem {
  task: string;
  estimated_days: number;
  depends_on: string[];
  priority: string;
}

/** AI-detected gaps in project planning and execution. */
export interface GapAnalysis {
  missing_tasks: string[];
  missing_prerequisites: string[];
  backward_plan: BackwardPlanItem[];
}

/** A single technical readiness evaluation item. */
export interface ReadinessItem {
  area: string;
  status: string;
  details: string;
}

/** A single technical risk item. */
export interface RiskItem {
  risk: string;
  severity: string;
  mitigation: string;
}

/** AI-assessed technical feasibility of a project. */
export interface TechnicalFeasibility {
  readiness_items: ReadinessItem[];
  risk_items: RiskItem[];
  architect_questions: string[];
}

/**
 * A project identified from Jira project keys and Slack channel patterns.
 * One project may span multiple Jira projects and multiple Slack channels.
 * AI detects project boundaries; the COO confirms or adjusts.
 */
export interface Project {
  project_id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  completion_percentage: number;
  deadline: string | null;
  milestones: Milestone[];
  people_involved: ProjectMember[];
  task_summary: TaskSummary;
  health_score: number;
  key_risks: string[];
  missing_tasks: string[];
  technical_concerns: string[];
  slack_channels: string[];
  jira_project_keys: string[];
  sprint_health: SprintHealth | null;
  gap_analysis: GapAnalysis | null;
  technical_feasibility: TechnicalFeasibility | null;
  created_at: string;
  updated_at: string;
  last_analyzed_at: string;
}

// ===========================================================================
// Project Files
// ===========================================================================

/** Metadata for a file uploaded to a specific project. */
export interface ProjectFileInfo {
  file_id: string;
  filename: string;
  file_type: string; // "slack_json" | "jira_xlsx" | "documentation"
  content_type: string;
  file_size: number;
  status: string; // "completed" | "failed" | "skipped"
  citex_ingested: boolean;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ===========================================================================
// Ingestion
// ===========================================================================

/** Type of data source file being ingested. */
export enum IngestionFileType {
  SLACK_ADMIN_EXPORT = "slack_admin_export",
  SLACK_API_EXTRACT = "slack_api_extract",
  SLACK_MANUAL_EXPORT = "slack_manual_export",
  JIRA_CSV = "jira_csv",
  DRIVE_DOCUMENT = "drive_document",
}

/** Processing status of an individual file within an ingestion job. */
export enum IngestionFileStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
}

/** Lifecycle status of an ingestion job. */
export enum IngestionStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

/** Tracks the processing outcome for a single file within an ingestion job. */
export interface IngestionFileResult {
  filename: string;
  file_type: IngestionFileType;
  status: IngestionFileStatus;
  records_processed: number;
  records_skipped: number;
  error_message: string | null;
  content_hash: string | null;
}

/**
 * Tracks a file ingestion pipeline from upload to completion.
 * Each job may process multiple files and reports per-file results.
 */
export interface IngestionJob {
  job_id: string;
  status: IngestionStatus;
  files: IngestionFileResult[];
  started_at: string | null;
  completed_at: string | null;
  error_count: number;
  total_records: number;
  created_at: string;
  updated_at: string;
}

// ===========================================================================
// Conversations
// ===========================================================================

/** Where a conversation turn originated. */
export enum TurnSource {
  COO_CHAT = "coo_chat",
  SLACK_MESSAGE = "slack_message",
  JIRA_COMMENT = "jira_comment",
}

/** Which UI page the COO was viewing during the turn. */
export enum PageContext {
  MAIN_DASHBOARD = "main_dashboard",
  PROJECT_VIEW = "project_view",
  CUSTOM_DASHBOARD = "custom_dashboard",
  REPORT_PREVIEW = "report_preview",
}

/** Role of the speaker in a conversation turn. */
export enum TurnRole {
  USER = "user",
  ASSISTANT = "assistant",
}

/** A data source used during a conversation turn response. */
export interface SourceUsed {
  source_type: string;
  item_count: number;
  date_range: string | null;
}

/**
 * A single turn in a conversation between the COO and ChiefOps.
 * Every user message and every assistant response is a separate document.
 */
export interface ConversationTurn {
  turn_id: string;
  project_id: string | null;
  stream_type: string;
  role: TurnRole;
  content: string;
  timestamp: string;
  turn_number: number;
  sources_used: SourceUsed[];
}

// ===========================================================================
// Hard Facts
// ===========================================================================

/** Category of a conversation-extracted fact. */
export enum FactType {
  CORRECTION = "correction",
  DECISION = "decision",
  PREFERENCE = "preference",
  OBSERVATION = "observation",
}

/**
 * A hard fact extracted from a conversation turn. Facts are never compacted
 * or deleted -- they are the permanent record of what the COO has communicated.
 */
export interface HardFact {
  fact_id: string;
  project_id: string | null;
  fact_text: string;
  category: FactType;
  source: string;
  confidence: number;
  active: boolean;
  created_at: string;
}

// ===========================================================================
// Alerts
// ===========================================================================

/** Severity level of a triggered alert. */
export enum AlertSeverity {
  CRITICAL = "critical",
  WARNING = "warning",
  INFO = "info",
}

/** Alert lifecycle status. */
export enum AlertStatus {
  ACTIVE = "active",
  RESOLVED = "resolved",
  ACKNOWLEDGED = "acknowledged",
}

/**
 * A configured alert with threshold monitoring. Alerts fire when a
 * monitored metric crosses a threshold and resolve when the condition clears.
 */
export interface Alert {
  alert_id: string;
  alert_type: string;
  name: string;
  description: string;
  metric: string;
  operator: string;
  threshold: number;
  active: boolean;
  created_at: string;
}

/**
 * Record of a triggered alert instance with the measured value at trigger time.
 */
export interface AlertTriggered {
  trigger_id: string;
  alert_id: string;
  current_value: number;
  threshold: number;
  message: string;
  severity: AlertSeverity;
  acknowledged: boolean;
  triggered_at: string;
}

// ===========================================================================
// Reports
// ===========================================================================

/** Report category types supported by ChiefOps. */
export enum ReportType {
  BOARD_SUMMARY = "board_summary",
  PROJECT_STATUS = "project_status",
  TEAM_PERFORMANCE = "team_performance",
  RISK_ASSESSMENT = "risk_assessment",
  SPRINT_REPORT = "sprint_report",
  RESOURCE_UTILIZATION = "resource_utilization",
  TECHNICAL_DUE_DILIGENCE = "technical_due_diligence",
  CUSTOM = "custom",
}

/** The type of content rendered in a report section. */
export enum SectionType {
  NARRATIVE = "narrative",
  METRIC_GRID = "metric_grid",
  CHART = "chart",
  TABLE = "table",
  CHECKLIST = "checklist",
  LIST = "list",
}

/** Report lifecycle status. */
export enum ReportStatus {
  DRAFT = "draft",
  FINALIZED = "finalized",
  EXPORTED = "exported",
}

/** A single section within a generated report. */
export interface ReportSection {
  section_id: string;
  section_type: SectionType;
  title: string;
  content: Record<string, unknown>;
  order: number;
}

/**
 * Full report specification. Reports are created through conversation and
 * iteratively refined. The sections array contains the complete structure;
 * each section has its own type that determines how the frontend renders it.
 */
export interface ReportSpec {
  report_id: string;
  report_type: ReportType;
  title: string;
  time_scope: Record<string, string>;
  audience: string;
  projects: string[];
  sections: ReportSection[];
  metadata: Record<string, unknown>;
  status: ReportStatus;
  created_at: string;
  updated_at: string;
}

// ===========================================================================
// Application Settings
// ===========================================================================

/** Global application settings configurable by the COO. */
export interface AppSettings {
  ai_adapter: string;
  ai_cli_tool: string;
  ai_model: string;
  openrouter_model: string;
  pii_redaction_enabled: boolean;
  has_completed_onboarding: boolean;
  [key: string]: unknown;
}

// ===========================================================================
// Filters
// ===========================================================================

/** Query filters for the people directory. */
export interface PeopleFilters {
  activity_level?: ActivityLevel;
  department?: string;
  project_id?: string;
}

// ===========================================================================
// COO Briefings
// ===========================================================================

/** Per-file summary metadata from the COO pipeline. */
export interface FileSummaryInfo {
  summary_id: string;
  file_id: string;
  filename: string;
  file_type: string;
  status: string; // "completed" | "failed" | "processing"
  summary_markdown: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

/** An item requiring COO attention. */
export interface AttentionItem {
  title: string;
  severity: "red" | "amber" | "green";
  details: string;
}

/** Overall project health assessment. */
export interface ProjectHealthInfo {
  status: "red" | "yellow" | "green";
  score: number;
  rationale: string;
}

/** Team member capacity assessment. */
export interface TeamCapacityItem {
  person: string;
  status: "overloaded" | "balanced" | "underutilized";
  details: string;
}

/** Upcoming deadline or milestone. */
export interface DeadlineItem {
  item: string;
  date: string;
  status: "on_track" | "at_risk" | "overdue";
}

/** A recent change or event. */
export interface RecentChangeItem {
  change: string;
  impact: string;
}

/** Structured COO briefing data (5 sections). */
export interface COOBriefing {
  briefing_id: string;
  project_id: string;
  status: string; // "completed" | "failed" | "processing"
  briefing: {
    executive_summary: string;
    attention_items: AttentionItem[];
    project_health: ProjectHealthInfo | null;
    team_capacity: TeamCapacityItem[];
    upcoming_deadlines: DeadlineItem[];
    recent_changes: RecentChangeItem[];
  } | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

/** Pipeline progress status. */
export interface COOBriefingStatus {
  project_id: string;
  pipeline_status: "idle" | "processing" | "completed" | "failed";
  summaries_total: number;
  summaries_completed: number;
  summaries_failed: number;
  summaries_processing: number;
  briefing_status: string | null;
}
