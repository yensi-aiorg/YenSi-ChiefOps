import { useState, useRef, useCallback, useEffect } from "react";
import { SendHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  ChatInput – auto-resizing textarea with send button                */
/* ------------------------------------------------------------------ */

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

const MAX_ROWS = 6;
const LINE_HEIGHT = 20;
const BASE_HEIGHT = 40;

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Ask ChiefOps AI...",
  className,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /** Auto-resize the textarea based on content. */
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;

    el.style.height = "auto";
    const scrollHeight = el.scrollHeight;
    const maxHeight = BASE_HEIGHT + LINE_HEIGHT * (MAX_ROWS - 1);
    el.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
  }, []);

  useEffect(() => {
    resize();
  }, [value, resize]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setValue("");

    // Reset textarea height after send
    requestAnimationFrame(() => {
      const el = textareaRef.current;
      if (el) {
        el.style.height = `${BASE_HEIGHT}px`;
      }
    });
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const isEmpty = value.trim().length === 0;

  return (
    <div className={cn("relative flex items-end gap-2", className)}>
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className={cn(
            "w-full resize-none rounded-xl border border-slate-300 bg-white px-4 py-2.5 pr-12 text-sm text-slate-900 placeholder:text-slate-400",
            "focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "dark:border-slate-600 dark:bg-surface-dark-card dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-teal-400",
            "scrollbar-none",
          )}
          style={{ minHeight: `${BASE_HEIGHT}px` }}
        />
      </div>

      <button
        onClick={handleSend}
        disabled={disabled || isEmpty}
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all duration-200",
          disabled || isEmpty
            ? "cursor-not-allowed bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-600"
            : "bg-teal-600 text-white shadow-sm hover:bg-teal-700 active:scale-95 dark:bg-teal-500 dark:hover:bg-teal-600",
        )}
        aria-label="Send message"
      >
        <SendHorizontal className="h-4.5 w-4.5" />
      </button>
    </div>
  );
}
