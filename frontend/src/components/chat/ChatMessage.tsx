import ReactMarkdown from "react-markdown";
import { Bot } from "lucide-react";
import type { ConversationTurn } from "@/types";
import { TurnRole } from "@/types";
import { cn, formatRelativeTime } from "@/lib/utils";
import { SourceBadge } from "./SourceBadge";

/* ------------------------------------------------------------------ */
/*  ChatMessage – single conversation turn bubble                      */
/* ------------------------------------------------------------------ */

interface ChatMessageProps {
  message: ConversationTurn;
  className?: string;
}

export function ChatMessage({ message, className }: ChatMessageProps) {
  const isUser =
    message.role === TurnRole.USER || message.role === ("user" as TurnRole);
  const isAssistant = !isUser;

  const sources = message.sources_used ?? [];
  const hasSources = sources.length > 0;

  return (
    <div
      className={cn(
        "flex w-full gap-2.5",
        isUser ? "justify-end" : "justify-start",
        className,
      )}
    >
      {/* Assistant avatar */}
      {isAssistant && (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-chief-600">
          <Bot className="h-4 w-4 text-white" />
        </div>
      )}

      {/* Message content */}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5",
          isUser
            ? "rounded-br-md bg-teal-600 text-white dark:bg-teal-500"
            : "rounded-bl-md bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100",
        )}
      >
        {/* Markdown body */}
        <div
          className={cn(
            "prose prose-sm max-w-none",
            isUser
              ? "prose-invert prose-p:text-white/95 prose-a:text-teal-200 prose-strong:text-white prose-code:text-teal-100"
              : "dark:prose-invert",
          )}
        >
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
              code: ({ children, className: codeClassName }) => {
                const isInline = !codeClassName;
                if (isInline) {
                  return (
                    <code
                      className={cn(
                        "rounded px-1 py-0.5 text-xs",
                        isUser
                          ? "bg-teal-700/50"
                          : "bg-slate-200 dark:bg-slate-700",
                      )}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <pre
                    className={cn(
                      "overflow-x-auto rounded-lg p-3 text-xs",
                      isUser
                        ? "bg-teal-700/50"
                        : "bg-slate-200 dark:bg-slate-700",
                    )}
                  >
                    <code>{children}</code>
                  </pre>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Source badges */}
        {hasSources && (
          <div className="mt-2 flex flex-wrap gap-1 border-t border-white/10 pt-2 dark:border-slate-700">
            {sources.map((source, idx) => (
              <SourceBadge key={`${source.source_type}-${idx}`} source={source} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={cn(
            "mt-1 text-2xs",
            isUser
              ? "text-teal-200/70"
              : "text-slate-400 dark:text-slate-500",
          )}
        >
          {formatRelativeTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}
