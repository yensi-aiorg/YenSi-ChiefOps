import { FileText } from "lucide-react";

export function ReportList() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Reports
        </h1>
      </div>
      <div className="card">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Report list with generation controls will be rendered here.
        </p>
      </div>
    </div>
  );
}
