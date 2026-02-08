import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
} from "axios";
import toast from "react-hot-toast";

/**
 * Generate a unique request ID for tracing.
 */
function generateRequestId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 10);
  return `req_${timestamp}_${random}`;
}

/**
 * Resolve the API base URL from environment variable or default to relative /api path.
 * In development with Vite proxy, /api is proxied to the backend on port 23101.
 */
function getBaseURL(): string {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  return "/api";
}

/**
 * Pre-configured Axios instance for all ChiefOps API calls.
 */
const api: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

/* ------------------------------------------------------------------ */
/*  Request interceptor                                               */
/* ------------------------------------------------------------------ */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const requestId = generateRequestId();
    config.headers.set("X-Request-ID", requestId);

    if (import.meta.env.DEV) {
      const method = (config.method ?? "GET").toUpperCase();
      const url = config.url ?? "";
      console.log(
        `%c[API] ${method} ${url}`,
        "color: #07c7b1; font-weight: bold;",
        { requestId, params: config.params, data: config.data },
      );
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

/* ------------------------------------------------------------------ */
/*  Response interceptor                                              */
/* ------------------------------------------------------------------ */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    if (import.meta.env.DEV) {
      const requestId = response.config.headers?.["X-Request-ID"] ?? "unknown";
      console.log(
        `%c[API] Response ${response.status}`,
        "color: #07c7b1;",
        { requestId, data: response.data },
      );
    }
    return response;
  },
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    const status = error.response?.status;
    const detail =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message;

    switch (status) {
      case 401:
        toast.error("Session expired. Please sign in again.");
        break;

      case 403:
        toast.error("You do not have permission to perform this action.");
        break;

      case 404:
        if (import.meta.env.DEV) {
          console.warn(`[API] Resource not found: ${error.config?.url}`);
        }
        break;

      case 409:
        toast.error(detail ?? "A conflict occurred. Please try again.");
        break;

      case 422:
        toast.error(detail ?? "Invalid data submitted. Please check your input.");
        break;

      case 429:
        toast.error("Too many requests. Please slow down and try again.");
        break;

      case 500:
      case 502:
      case 503:
        toast.error(
          "A server error occurred. Our team has been notified. Please try again later.",
        );
        break;

      default:
        if (!error.response) {
          toast.error(
            "Network error. Please check your connection and try again.",
          );
        } else {
          toast.error(detail ?? "An unexpected error occurred.");
        }
        break;
    }

    if (import.meta.env.DEV) {
      console.error(
        `%c[API] Error ${status ?? "NETWORK"}`,
        "color: #ef4444; font-weight: bold;",
        {
          url: error.config?.url,
          status,
          detail,
          error,
        },
      );
    }

    return Promise.reject(error);
  },
);

export { api };
export default api;
