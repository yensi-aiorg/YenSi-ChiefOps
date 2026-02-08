import { useState, useCallback } from "react";
import {
  ArrowRight,
  Upload,
  Database,
  CheckCircle2,
  Sparkles,
  LayoutDashboard,
} from "lucide-react";
import { useSettingsStore } from "@/stores/settingsStore";
import { useIngestionStore } from "@/stores/ingestionStore";
import { cn } from "@/lib/utils";
import { DropZone } from "@/components/ingestion/DropZone";

/* ------------------------------------------------------------------ */
/*  OnboardingWizard – three-step first-run experience                 */
/* ------------------------------------------------------------------ */

type Step = "welcome" | "data_source" | "confirmation";

const STEPS: Step[] = ["welcome", "data_source", "confirmation"];

const STEP_LABELS: Record<Step, string> = {
  welcome: "Welcome",
  data_source: "Data Source",
  confirmation: "All Set",
};

interface OnboardingWizardProps {
  onComplete: () => void;
  className?: string;
}

export function OnboardingWizard({
  onComplete,
  className,
}: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>("welcome");
  const [loadingSample, setLoadingSample] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  const { updateSettings } = useSettingsStore();
  const { uploadFiles, isUploading } = useIngestionStore();

  const currentStepIndex = STEPS.indexOf(currentStep);

  const goToNext = useCallback(() => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex]!);
    }
  }, [currentStepIndex]);

  const handleSampleData = async () => {
    setLoadingSample(true);
    try {
      // Simulate loading sample data
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setUploadComplete(true);
      goToNext();
    } catch {
      // Error handled by store
    } finally {
      setLoadingSample(false);
    }
  };

  const handleUpload = async (files: File[]) => {
    const job = await uploadFiles(files);
    if (job) {
      setUploadComplete(true);
      goToNext();
    }
  };

  const handleFinish = async () => {
    await updateSettings({ has_completed_onboarding: true });
    onComplete();
  };

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-surface-dark dark:to-slate-900",
        className,
      )}
    >
      <div className="w-full max-w-lg px-4">
        {/* Step indicators */}
        <div className="mb-8 flex items-center justify-center gap-2">
          {STEPS.map((step, idx) => (
            <div key={step} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-all duration-300",
                  idx < currentStepIndex
                    ? "bg-teal-500 text-white"
                    : idx === currentStepIndex
                      ? "bg-teal-600 text-white shadow-glow"
                      : "bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
                )}
              >
                {idx < currentStepIndex ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  idx + 1
                )}
              </div>
              {idx < STEPS.length - 1 && (
                <div
                  className={cn(
                    "h-0.5 w-12 rounded-full transition-colors duration-300",
                    idx < currentStepIndex
                      ? "bg-teal-500"
                      : "bg-slate-200 dark:bg-slate-700",
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step label */}
        <p className="mb-6 text-center text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {STEP_LABELS[currentStep]}
        </p>

        {/* Step content */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft-lg dark:border-slate-700 dark:bg-surface-dark-card">
          {currentStep === "welcome" && (
            <WelcomeStep onNext={goToNext} />
          )}
          {currentStep === "data_source" && (
            <DataSourceStep
              onSampleData={handleSampleData}
              onUpload={handleUpload}
              loadingSample={loadingSample}
              isUploading={isUploading}
            />
          )}
          {currentStep === "confirmation" && (
            <ConfirmationStep onFinish={handleFinish} />
          )}
        </div>
      </div>
    </div>
  );
}

/* -- Step 1: Welcome ----------------------------------------------- */

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <div className="px-8 py-10 text-center">
      {/* Logo */}
      <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-teal-500 to-chief-600 shadow-glow">
        <span className="text-2xl font-bold text-white">CO</span>
      </div>

      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
        Welcome to ChiefOps
      </h1>
      <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-slate-500 dark:text-slate-400">
        Your AI-powered Chief of Staff. ChiefOps connects to your team's Slack,
        Jira, and Google Drive to give you instant insight into people, projects,
        and progress -- all from one intelligent dashboard.
      </p>

      <div className="mt-8 grid grid-cols-3 gap-4">
        <FeatureCard
          icon={<Sparkles className="h-5 w-5 text-teal-500" />}
          label="AI Insights"
        />
        <FeatureCard
          icon={<LayoutDashboard className="h-5 w-5 text-chief-500" />}
          label="Smart Dashboards"
        />
        <FeatureCard
          icon={<Database className="h-5 w-5 text-warm-500" />}
          label="Unified Data"
        />
      </div>

      <button
        onClick={onNext}
        className="btn-primary mt-8 w-full py-3 text-base"
      >
        Get Started
        <ArrowRight className="h-5 w-5" />
      </button>
    </div>
  );
}

function FeatureCard({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl bg-slate-50 px-3 py-4 dark:bg-slate-800">
      {icon}
      <span className="text-2xs font-medium text-slate-600 dark:text-slate-400">
        {label}
      </span>
    </div>
  );
}

/* -- Step 2: Data Source ------------------------------------------- */

function DataSourceStep({
  onSampleData,
  onUpload,
  loadingSample,
  isUploading,
}: {
  onSampleData: () => void;
  onUpload: (files: File[]) => void;
  loadingSample: boolean;
  isUploading: boolean;
}) {
  const [mode, setMode] = useState<"choice" | "upload">("choice");

  return (
    <div className="px-8 py-8">
      <h2 className="text-center text-xl font-bold text-slate-900 dark:text-white">
        Choose Your Data Source
      </h2>
      <p className="mt-2 text-center text-sm text-slate-500 dark:text-slate-400">
        Load sample data to explore, or upload your own team exports.
      </p>

      {mode === "choice" ? (
        <div className="mt-8 space-y-4">
          {/* Sample data option */}
          <button
            onClick={onSampleData}
            disabled={loadingSample || isUploading}
            className={cn(
              "flex w-full items-center gap-4 rounded-xl border-2 border-dashed px-5 py-5 text-left transition-all",
              loadingSample
                ? "border-teal-300 bg-teal-50 dark:border-teal-600 dark:bg-teal-900/20"
                : "border-slate-200 hover:border-teal-400 hover:bg-teal-50/50 dark:border-slate-700 dark:hover:border-teal-600 dark:hover:bg-teal-900/10",
              (loadingSample || isUploading) && "pointer-events-none",
            )}
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-teal-100 dark:bg-teal-900/40">
              {loadingSample ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
              ) : (
                <Database className="h-6 w-6 text-teal-600 dark:text-teal-400" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Try with Sample Data
              </h3>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Explore ChiefOps with pre-loaded demo data from a fictional company.
              </p>
            </div>
          </button>

          {/* Upload option */}
          <button
            onClick={() => setMode("upload")}
            disabled={loadingSample || isUploading}
            className={cn(
              "flex w-full items-center gap-4 rounded-xl border-2 border-dashed px-5 py-5 text-left transition-all",
              "border-slate-200 hover:border-chief-400 hover:bg-chief-50/50 dark:border-slate-700 dark:hover:border-chief-600 dark:hover:bg-chief-900/10",
              (loadingSample || isUploading) && "pointer-events-none opacity-50",
            )}
          >
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-chief-100 dark:bg-chief-900/40">
              <Upload className="h-6 w-6 text-chief-600 dark:text-chief-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Upload Your Own
              </h3>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Upload Slack exports, Jira CSVs, or Google Drive documents.
              </p>
            </div>
          </button>
        </div>
      ) : (
        <div className="mt-6">
          <DropZone onFilesAccepted={onUpload} disabled={isUploading} />
          <button
            onClick={() => setMode("choice")}
            disabled={isUploading}
            className="btn-ghost mt-4 w-full"
          >
            Back to options
          </button>
        </div>
      )}
    </div>
  );
}

/* -- Step 3: Confirmation ------------------------------------------ */

function ConfirmationStep({ onFinish }: { onFinish: () => void }) {
  return (
    <div className="px-8 py-10 text-center">
      <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-green-100 dark:bg-green-900/30">
        <CheckCircle2 className="h-8 w-8 text-green-500" />
      </div>

      <h2 className="text-xl font-bold text-slate-900 dark:text-white">
        You're All Set!
      </h2>
      <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-slate-500 dark:text-slate-400">
        Your data has been loaded successfully. ChiefOps is ready to help you
        understand your team, track projects, and make better decisions.
      </p>

      <div className="mt-8 space-y-3">
        <button
          onClick={onFinish}
          className="btn-primary w-full py-3 text-base"
        >
          <LayoutDashboard className="h-5 w-5" />
          Go to Dashboard
        </button>
      </div>

      <p className="mt-4 text-2xs text-slate-400 dark:text-slate-500">
        You can upload more data anytime from the Upload Data page.
      </p>
    </div>
  );
}
