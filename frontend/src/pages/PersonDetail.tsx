import { useParams } from "react-router-dom";
import { Users } from "lucide-react";

export function PersonDetail() {
  const { personId } = useParams<{ personId: string }>();

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Person Detail
        </h1>
        <span className="badge-teal">ID: {personId}</span>
      </div>
      <div className="card">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Person detail view with health scores and activity will be rendered here.
        </p>
      </div>
    </div>
  );
}
