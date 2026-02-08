import { useEffect, useState } from "react";
import {
  Settings,
  Brain,
  Shield,
  Database,
  Info,
  Download,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { useSettingsStore } from "@/stores/settingsStore";
import { cn } from "@/lib/utils";

/* ================================================================== */
/*  Confirm Dialog                                                     */
/* ================================================================== */

function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  loading,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-soft-lg dark:bg-surface-dark-card">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
          {title}
        </h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {message}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onCancel} disabled={loading} className="btn-ghost">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="btn-destructive"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  Toggle Switch                                                      */
/* ================================================================== */

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 dark:focus:ring-offset-surface-dark",
        checked ? "bg-teal-500" : "bg-slate-300 dark:bg-slate-600",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-soft transition-transform duration-200",
          checked ? "translate-x-5" : "translate-x-0",
        )}
      />
    </button>
  );
}

/* ================================================================== */
/*  Settings Card Section                                              */
/* ================================================================== */

function SettingsCard({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card space-y-4 p-5">
      <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900 dark:text-white">
        {icon}
        {title}
      </h2>
      {children}
    </div>
  );
}

/* ================================================================== */
/*  Model selector options                                             */
/* ================================================================== */

const modelOptions = [
  { value: "gpt-4o", label: "GPT-4o (Default)" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini (Faster)" },
  { value: "claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
  { value: "claude-3-5-haiku", label: "Claude 3.5 Haiku (Faster)" },
  { value: "local", label: "Local Model (Ollama)" },
];

/* ================================================================== */
/*  Settings Page                                                      */
/* ================================================================== */

export function SettingsPage() {
  const {
    settings,
    isLoading,
    error,
    fetchSettings,
    updateSettings,
    exportData,
    clearAllData,
    clearError,
  } = useSettingsStore();

  const [showClearDialog, setShowClearDialog] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleModelChange = async (model: string) => {
    await updateSettings({ ai_model: model });
    flashSaveSuccess();
  };

  const handlePiiToggle = async (enabled: boolean) => {
    await updateSettings({ pii_redaction: enabled });
    flashSaveSuccess();
  };

  const handleExport = async () => {
    await exportData();
  };

  const handleClearData = async () => {
    setClearing(true);
    try {
      await clearAllData();
    } finally {
      setClearing(false);
      setShowClearDialog(false);
    }
  };

  const flashSaveSuccess = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  // Loading skeleton
  if (isLoading && !settings) {
    return (
      <div className="animate-fade-in space-y-6">
        <div className="flex items-center gap-3">
          <div className="skeleton h-6 w-6 rounded" />
          <div className="skeleton h-7 w-32" />
        </div>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card space-y-4 p-5">
            <div className="skeleton h-5 w-40" />
            <div className="skeleton h-10 w-full" />
            <div className="skeleton h-4 w-64" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="h-6 w-6 text-teal-600 dark:text-teal-400" />
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Settings
          </h1>
        </div>
        {saveSuccess && (
          <span className="flex items-center gap-1.5 text-sm font-medium text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            Saved
          </span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={clearError}
            className="rounded p-1 hover:bg-red-100 dark:hover:bg-red-900/50"
          >
            &times;
          </button>
        </div>
      )}

      {/* AI Configuration */}
      <SettingsCard
        icon={<Brain className="h-5 w-5 text-chief-500" />}
        title="AI Configuration"
      >
        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Language Model
          </label>
          <select
            value={settings?.ai_model ?? "gpt-4o"}
            onChange={(e) => handleModelChange(e.target.value)}
            className="input w-full max-w-md"
          >
            {modelOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Select the AI model used for analysis, report generation, and
            conversational interactions.
          </p>
        </div>
      </SettingsCard>

      {/* Privacy */}
      <SettingsCard
        icon={<Shield className="h-5 w-5 text-teal-500" />}
        title="Privacy"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              PII Redaction
            </p>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Automatically redact personally identifiable information (names,
              emails, phone numbers) from exported reports and API responses.
            </p>
          </div>
          <Toggle
            checked={settings?.pii_redaction ?? false}
            onChange={handlePiiToggle}
          />
        </div>
      </SettingsCard>

      {/* Data Management */}
      <SettingsCard
        icon={<Database className="h-5 w-5 text-warm-500" />}
        title="Data Management"
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Export All Data
              </p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Download all projects, people, reports, and settings as a JSON
                file.
              </p>
            </div>
            <button onClick={handleExport} className="btn-secondary">
              <Download className="h-4 w-4" />
              Export JSON
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-red-200 p-4 dark:border-red-900/40">
            <div>
              <p className="text-sm font-medium text-red-700 dark:text-red-400">
                Clear All Data
              </p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Permanently delete all projects, people, ingestion history, and
                reports. This action cannot be undone.
              </p>
            </div>
            <button
              onClick={() => setShowClearDialog(true)}
              className="btn-destructive"
            >
              <Trash2 className="h-4 w-4" />
              Clear Data
            </button>
          </div>
        </div>
      </SettingsCard>

      {/* About */}
      <SettingsCard
        icon={<Info className="h-5 w-5 text-navy-500" />}
        title="About"
      >
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Version
              </p>
              <p className="font-medium text-slate-700 dark:text-slate-300">
                {settings?.version ?? "1.0.0"}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Build
              </p>
              <p className="font-mono text-xs text-slate-700 dark:text-slate-300">
                {settings?.build_hash ?? "dev"}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Environment
              </p>
              <p className="font-medium text-slate-700 dark:text-slate-300">
                {settings?.environment ?? "development"}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 border-t border-slate-200 pt-3 dark:border-slate-700">
            <a
              href="https://github.com/YenSi/ChiefOps"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-teal-600 hover:underline dark:text-teal-400"
            >
              GitHub Repository
              <ExternalLink className="h-3 w-3" />
            </a>
            <a
              href="https://chiefops.dev/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-teal-600 hover:underline dark:text-teal-400"
            >
              Documentation
              <ExternalLink className="h-3 w-3" />
            </a>
            <a
              href="https://chiefops.dev/changelog"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-teal-600 hover:underline dark:text-teal-400"
            >
              Changelog
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </SettingsCard>

      {/* Clear data confirmation dialog */}
      <ConfirmDialog
        open={showClearDialog}
        title="Clear All Data"
        message="This will permanently delete all projects, people, reports, and ingestion history. This action cannot be undone. Are you absolutely sure?"
        confirmLabel="Clear Everything"
        loading={clearing}
        onConfirm={handleClearData}
        onCancel={() => setShowClearDialog(false)}
      />
    </div>
  );
}
