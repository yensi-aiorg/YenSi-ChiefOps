import { useState } from "react";
import { Download, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { useReportStore } from "@/stores/reportStore";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  PdfExportButton – triggers PDF export and browser download         */
/* ------------------------------------------------------------------ */

interface PdfExportButtonProps {
  reportId: string;
  className?: string;
  variant?: "primary" | "secondary" | "ghost";
}

export function PdfExportButton({
  reportId,
  className,
  variant = "secondary",
}: PdfExportButtonProps) {
  const { exportPdf, exporting } = useReportStore();
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  const handleExport = async () => {
    if (status === "loading") return;

    setStatus("loading");
    try {
      const blobUrl = await exportPdf(reportId);

      if (blobUrl) {
        // Trigger browser download
        const link = document.createElement("a");
        link.href = blobUrl;
        link.download = `report-${reportId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Clean up the blob URL after a delay
        setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);

        setStatus("success");
        // Reset status after showing success
        setTimeout(() => setStatus("idle"), 2500);
      } else {
        setStatus("error");
        setTimeout(() => setStatus("idle"), 3000);
      }
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  };

  const isLoading = status === "loading" || exporting;

  const buttonClass = cn(
    variant === "primary" && "btn-primary",
    variant === "secondary" && "btn-secondary",
    variant === "ghost" && "btn-ghost",
    className,
  );

  return (
    <button
      onClick={handleExport}
      disabled={isLoading}
      className={buttonClass}
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Exporting...</span>
        </>
      ) : status === "success" ? (
        <>
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <span>Downloaded</span>
        </>
      ) : status === "error" ? (
        <>
          <XCircle className="h-4 w-4 text-red-500" />
          <span>Export Failed</span>
        </>
      ) : (
        <>
          <Download className="h-4 w-4" />
          <span>Export PDF</span>
        </>
      )}
    </button>
  );
}
