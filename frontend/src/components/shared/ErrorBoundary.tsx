import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  ErrorBoundary – catches render errors with a recovery UI           */
/* ------------------------------------------------------------------ */

export interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback component to render instead of the default error UI */
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log to console in development, could send to monitoring in production
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary] Caught error:", error);
      console.error("[ErrorBoundary] Component stack:", errorInfo.componentStack);
    }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[300px] items-center justify-center p-8">
          <div className="mx-auto max-w-md text-center">
            {/* Icon */}
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 dark:bg-red-900/20">
              <AlertTriangle className="h-8 w-8 text-red-500" />
            </div>

            {/* Heading */}
            <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
              Something went wrong
            </h2>

            {/* Description */}
            <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
              An unexpected error occurred while rendering this section. You can
              try again or refresh the page.
            </p>

            {/* Error details (development only) */}
            {import.meta.env.DEV && this.state.error && (
              <details className="mb-6 rounded-lg border border-slate-200 bg-slate-50 p-3 text-left dark:border-slate-700 dark:bg-slate-800">
                <summary className="cursor-pointer text-xs font-medium text-slate-600 dark:text-slate-300">
                  Error details
                </summary>
                <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs text-red-600 dark:text-red-400">
                  {this.state.error.message}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}

            {/* Retry button */}
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:ring-offset-2 active:bg-teal-800"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
