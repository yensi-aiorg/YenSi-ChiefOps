import { useEffect, useRef } from "react";
import { X, MessageSquare, FolderKanban } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { useProjectStore } from "@/stores/projectStore";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";
import { StreamingResponse } from "./StreamingResponse";

/* ------------------------------------------------------------------ */
/*  ChatSidebar – right-side expandable conversation panel             */
/* ------------------------------------------------------------------ */

interface ChatSidebarProps {
  open: boolean;
  onClose: () => void;
}

export function ChatSidebar({ open, onClose }: ChatSidebarProps) {
  const {
    messages,
    isStreaming,
    activeProjectId,
    error,
    sendMessage,
    clearError,
  } = useChatStore();

  const { selectedProject, projects } = useProjectStore();

  // Resolve project name from ID
  const activeProjectName = activeProjectId
    ? (selectedProject?.project_id === activeProjectId
        ? selectedProject.name
        : projects.find((p) => p.project_id === activeProjectId)?.name)
      ?? activeProjectId
    : null;

  const scrollRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(messages.length);

  /** Scroll to the bottom when new messages arrive. */
  useEffect(() => {
    if (messages.length > prevMessageCountRef.current || isStreaming) {
      const el = scrollRef.current;
      if (el) {
        requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight;
        });
      }
    }
    prevMessageCountRef.current = messages.length;
  }, [messages.length, isStreaming]);

  const handleSend = (content: string) => {
    clearError();
    sendMessage(content);
  };

  const placeholderText = activeProjectId
    ? "Ask about this project..."
    : "Ask ChiefOps AI anything...";

  /** Find the last assistant message to check if it's still streaming. */
  const lastMessage = messages[messages.length - 1];
  const isLastAssistantStreaming =
    isStreaming &&
    lastMessage &&
    (lastMessage.role === "assistant" || lastMessage.role === ("assistant" as never));

  return (
    <aside
      className={cn(
        "fixed bottom-0 right-0 top-0 z-40 flex w-[400px] flex-col border-l border-slate-200 bg-white shadow-lg transition-transform duration-300 ease-in-out dark:border-slate-700 dark:bg-surface-dark lg:z-20",
        open ? "translate-x-0" : "translate-x-full",
      )}
    >
      {/* Header */}
      <div className="flex h-topbar items-center justify-between border-b border-slate-200 px-4 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-chief-600">
            <MessageSquare className="h-4 w-4 text-white" />
          </div>
          <div>
            <span className="text-sm font-semibold text-slate-900 dark:text-white">
              ChiefOps AI
            </span>
            {isStreaming && (
              <span className="ml-2 text-2xs text-teal-500 dark:text-teal-400">
                Thinking...
              </span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          aria-label="Close chat"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Active project scope indicator */}
      {activeProjectId && (
        <div className="flex items-center gap-2 border-b border-slate-100 bg-teal-50/50 px-4 py-2 dark:border-slate-700/50 dark:bg-teal-900/10">
          <FolderKanban className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
          <span className="text-2xs font-medium text-teal-700 dark:text-teal-300">
            Scoped to project: {activeProjectName}
          </span>
        </div>
      )}

      {/* Message list */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto px-4 py-4"
      >
        {messages.length === 0 && !isStreaming && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-100 to-chief-100 dark:from-teal-900/40 dark:to-chief-900/40">
                <MessageSquare className="h-7 w-7 text-teal-600 dark:text-teal-400" />
              </div>
              <h3 className="mb-1 text-sm font-semibold text-slate-900 dark:text-white">
                AI Assistant Ready
              </h3>
              <p className="mx-auto max-w-[240px] text-xs text-slate-500 dark:text-slate-400">
                Ask questions about your team, projects, or request reports.
                I can analyze your Slack, Jira, and Drive data.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => {
          const key = msg.turn_id ?? `msg-${msg.timestamp}`;
          return <ChatMessage key={key} message={msg} />;
        })}

        {/* Streaming indicator when the last message is still building */}
        {isStreaming && lastMessage && isLastAssistantStreaming && (
          <StreamingResponse
            content={lastMessage.content}
            isStreaming={true}
          />
        )}

        {/* Streaming dots when waiting for first content */}
        {isStreaming && (!lastMessage || !isLastAssistantStreaming) && (
          <div className="flex gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-chief-600">
              <MessageSquare className="h-4 w-4 text-white" />
            </div>
            <div className="rounded-2xl rounded-bl-md bg-slate-100 px-4 py-3 dark:bg-slate-800">
              <StreamingResponse content="" isStreaming={true} />
            </div>
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
          <button
            onClick={clearError}
            className="ml-2 font-medium underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-slate-200 p-4 dark:border-slate-700">
        <ChatInput
          onSend={handleSend}
          disabled={isStreaming}
          placeholder={placeholderText}
        />
      </div>
    </aside>
  );
}
