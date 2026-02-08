import { Link } from "react-router-dom";
import { Home, MapPin } from "lucide-react";

/* ================================================================== */
/*  404 Not Found Page                                                 */
/* ================================================================== */

export function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      {/* Subtle illustration */}
      <div className="relative mb-8">
        <div className="flex h-32 w-32 items-center justify-center rounded-3xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900">
          <MapPin className="h-16 w-16 text-slate-300 dark:text-slate-600" />
        </div>
        <div className="absolute -right-4 -top-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 shadow-soft dark:from-teal-900/40 dark:to-chief-900/40">
          <span className="text-lg font-bold text-teal-600 dark:text-teal-400">
            ?
          </span>
        </div>
      </div>

      {/* Large 404 text */}
      <h1 className="mb-2 text-7xl font-extrabold tracking-tight text-slate-200 dark:text-slate-800">
        404
      </h1>

      {/* Message */}
      <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
        Page not found
      </h2>
      <p className="mb-8 max-w-sm text-sm text-slate-500 dark:text-slate-400">
        The page you are looking for does not exist or has been moved.
        Check the URL or head back to the dashboard.
      </p>

      {/* Action */}
      <Link to="/" className="btn-primary">
        <Home className="h-4 w-4" />
        Go to Dashboard
      </Link>
    </div>
  );
}
