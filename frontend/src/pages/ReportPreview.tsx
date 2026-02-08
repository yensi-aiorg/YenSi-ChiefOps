import { useParams } from "react-router-dom";
import { FileText } from "lucide-react";

export function ReportPreview() {
  const { reportId } = useParams<{ reportId: string }>();

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Report Preview
        </h1>
        <span className="badge-neutral">ID: {reportId}</span>
      </div>
      <div className="card">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Report preview with export controls will be rendered here.
        </p>
      </div>
    </div>
  );
}
