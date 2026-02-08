/**
 * API response wrapper types for the ChiefOps frontend.
 *
 * These types define the standard shapes returned by the backend API,
 * including generic wrappers for single-item and paginated responses,
 * health/readiness check payloads, and server-sent event envelopes.
 */

// ---------------------------------------------------------------------------
// Generic Response Wrappers
// ---------------------------------------------------------------------------

/** Standard API response wrapping a single data payload. */
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

/** Paginated list response with offset-based pagination metadata. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

// ---------------------------------------------------------------------------
// Health & Readiness
// ---------------------------------------------------------------------------

/** Basic health check response from GET /api/v1/health. */
export interface HealthStatus {
  status: string;
  mongo: boolean;
  redis: boolean;
  citex: boolean;
}

/** Detailed status for a single infrastructure dependency. */
export interface DependencyDetail {
  healthy: boolean;
  latency_ms: number;
  error: string | null;
}

/** Detailed readiness check response from GET /api/v1/ready. */
export interface ReadinessStatus {
  status: string;
  timestamp: string;
  environment: string;
  mongo: DependencyDetail;
  redis: DependencyDetail;
  citex: DependencyDetail;
}

// ---------------------------------------------------------------------------
// Server-Sent Events
// ---------------------------------------------------------------------------

/** A single server-sent event (SSE) message envelope. */
export interface SSEEvent {
  event: string;
  data: string;
}

// ---------------------------------------------------------------------------
// Error Responses
// ---------------------------------------------------------------------------

/** Standard error response body returned by the backend on failures. */
export interface ApiError {
  error: string;
  message: string;
  status_code?: number;
  details?: Record<string, string[]>;
}
