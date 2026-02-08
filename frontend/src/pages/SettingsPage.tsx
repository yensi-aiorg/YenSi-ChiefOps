import { Settings } from "lucide-react";

export function SettingsPage() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Settings
        </h1>
      </div>
      <div className="card">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Application settings and configuration will be rendered here.
        </p>
      </div>
    </div>
  );
}
