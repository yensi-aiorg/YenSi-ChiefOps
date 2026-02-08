import { useParams } from "react-router-dom";
import { FolderKanban } from "lucide-react";

export function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center gap-3">
        <FolderKanban className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Project Dashboard
        </h1>
        <span className="badge-chief">ID: {projectId}</span>
      </div>
      <div className="card">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Project dashboard with metrics and team view will be rendered here.
        </p>
      </div>
    </div>
  );
}
