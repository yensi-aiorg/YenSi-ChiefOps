import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  StreamingResponse – renders streaming text with a blinking cursor  */
/* ------------------------------------------------------------------ */

interface StreamingResponseProps {
  content: string;
  isStreaming: boolean;
  className?: string;
}

export function StreamingResponse({
  content,
  isStreaming,
  className,
}: StreamingResponseProps) {
  return (
    <div className={cn("relative", className)}>
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <span className="whitespace-pre-wrap">{content}</span>
        {isStreaming && (
          <span
            className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-500 dark:bg-teal-400"
            aria-label="Streaming in progress"
          />
        )}
      </div>

      {isStreaming && !content && (
        <div className="flex items-center gap-1.5 py-2">
          <span
            className="inline-block h-2 w-2 animate-pulse rounded-full bg-teal-400"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="inline-block h-2 w-2 animate-pulse rounded-full bg-teal-400"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="inline-block h-2 w-2 animate-pulse rounded-full bg-teal-400"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      )}
    </div>
  );
}
