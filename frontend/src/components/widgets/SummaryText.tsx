import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { ChevronDown, ChevronUp, Quote } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SummaryTextData {
  content: string;
  highlights?: SummaryHighlight[];
}

export interface SummaryHighlight {
  text: string;
  type?: "info" | "success" | "warning" | "error";
}

export interface SummaryTextConfig {
  max_height?: number;
  show_quotes?: boolean;
  typography_size?: "sm" | "base" | "lg";
  accent_color?: string;
}

export interface SummaryTextProps {
  data: SummaryTextData;
  config?: SummaryTextConfig;
}

// ---------------------------------------------------------------------------
// Highlight type style map
// ---------------------------------------------------------------------------

const HIGHLIGHT_STYLES: Record<string, { border: string; bg: string; text: string; icon: string }> = {
  info: {
    border: "border-chief-400 dark:border-chief-500",
    bg: "bg-chief-50 dark:bg-chief-900/20",
    text: "text-chief-800 dark:text-chief-300",
    icon: "text-chief-500",
  },
  success: {
    border: "border-green-400 dark:border-green-500",
    bg: "bg-green-50 dark:bg-green-900/20",
    text: "text-green-800 dark:text-green-300",
    icon: "text-green-500",
  },
  warning: {
    border: "border-warm-400 dark:border-warm-500",
    bg: "bg-warm-50 dark:bg-warm-900/20",
    text: "text-warm-800 dark:text-warm-300",
    icon: "text-warm-500",
  },
  error: {
    border: "border-red-400 dark:border-red-500",
    bg: "bg-red-50 dark:bg-red-900/20",
    text: "text-red-800 dark:text-red-300",
    icon: "text-red-500",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SummaryText({ data, config = {} }: SummaryTextProps) {
  const {
    max_height = 400,
    show_quotes = true,
    typography_size = "base",
  } = config;

  const [expanded, setExpanded] = useState(false);
  const [needsTruncation, setNeedsTruncation] = useState(false);

  const contentRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (node) {
        setNeedsTruncation(node.scrollHeight > max_height);
      }
    },
    [max_height],
  );

  const typographyClass =
    typography_size === "sm"
      ? "text-sm leading-relaxed"
      : typography_size === "lg"
        ? "text-lg leading-relaxed"
        : "text-base leading-relaxed";

  return (
    <div className="flex h-full flex-col">
      {/* Highlighted quotes / callouts */}
      {show_quotes && data.highlights && data.highlights.length > 0 && (
        <div className="mb-4 space-y-3">
          {data.highlights.map((highlight, idx) => {
            const styles =
              HIGHLIGHT_STYLES[highlight.type ?? "info"] ??
              HIGHLIGHT_STYLES.info!;
            return (
              <div
                key={idx}
                className={cn(
                  "flex items-start gap-3 rounded-lg border-l-4 px-4 py-3",
                  styles.border,
                  styles.bg,
                )}
              >
                <Quote
                  className={cn("mt-0.5 h-4 w-4 shrink-0", styles.icon)}
                />
                <p className={cn("text-sm font-medium", styles.text)}>
                  {highlight.text}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Markdown content */}
      <div
        ref={contentRef}
        className={cn(
          "relative overflow-hidden transition-all duration-300",
          !expanded && needsTruncation && "mask-bottom",
        )}
        style={{
          maxHeight: expanded || !needsTruncation ? "none" : `${max_height}px`,
        }}
      >
        <div
          className={cn(
            "prose prose-slate max-w-none dark:prose-invert",
            typographyClass,
            // Heading styles
            "prose-headings:font-semibold prose-headings:text-slate-900 dark:prose-headings:text-white",
            "prose-h1:text-xl prose-h2:text-lg prose-h3:text-base",
            "prose-h1:mt-6 prose-h1:mb-3 prose-h2:mt-5 prose-h2:mb-2 prose-h3:mt-4 prose-h3:mb-2",
            // Paragraph & list
            "prose-p:text-slate-700 dark:prose-p:text-slate-300",
            "prose-p:mb-3",
            "prose-li:text-slate-700 dark:prose-li:text-slate-300",
            "prose-ul:my-2 prose-ol:my-2",
            // Links
            "prose-a:text-teal-600 prose-a:no-underline hover:prose-a:text-teal-700 hover:prose-a:underline dark:prose-a:text-teal-400",
            // Code
            "prose-code:rounded prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-sm prose-code:text-teal-700 dark:prose-code:bg-slate-800 dark:prose-code:text-teal-400",
            "prose-pre:rounded-lg prose-pre:bg-slate-900 prose-pre:text-sm dark:prose-pre:bg-slate-950",
            // Blockquote
            "prose-blockquote:border-teal-400 prose-blockquote:text-slate-600 dark:prose-blockquote:border-teal-600 dark:prose-blockquote:text-slate-400",
            // Strong
            "prose-strong:text-slate-900 dark:prose-strong:text-white",
            // Table
            "prose-th:text-left prose-th:text-slate-600 dark:prose-th:text-slate-300",
            "prose-td:text-slate-700 dark:prose-td:text-slate-300",
          )}
        >
          <ReactMarkdown>{data.content}</ReactMarkdown>
        </div>

        {/* Fade gradient for truncation */}
        {!expanded && needsTruncation && (
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent dark:from-surface-dark-card" />
        )}
      </div>

      {/* Show more / less toggle */}
      {needsTruncation && (
        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="mt-2 inline-flex items-center gap-1 self-start text-sm font-medium text-teal-600 transition-colors hover:text-teal-700 dark:text-teal-400 dark:hover:text-teal-300"
        >
          {expanded ? (
            <>
              Show less <ChevronUp className="h-4 w-4" />
            </>
          ) : (
            <>
              Show more <ChevronDown className="h-4 w-4" />
            </>
          )}
        </button>
      )}
    </div>
  );
}

export default SummaryText;
